"""Publica documentos no repositório GitHub e mantém mkdocs.yml + progress.json."""
import json
from datetime import datetime

from django.conf import settings


def _get_repo():
    from github import Github
    g = Github(settings.GITHUB_TOKEN)
    return g.get_repo(settings.GITHUB_REPO)


def _branch():
    return getattr(settings, 'GITHUB_BRANCH', 'main')


def _upsert_file(repo, path, content, message):
    """Cria ou atualiza um arquivo no repositório."""
    from github import GithubException
    branch = _branch()
    if isinstance(content, str):
        content = content.encode('utf-8')
    try:
        existing = repo.get_contents(path, ref=branch)
        if existing.decoded_content == content:
            return  # sem alteração, evita commit vazio
        repo.update_file(path, message, content, existing.sha, branch=branch)
    except GithubException as e:
        if e.status == 404:
            repo.create_file(path, message, content, branch=branch)
        else:
            raise


def _todos_documentos_agrupados():
    from biblioteca.models import Categoria, Documento
    grupos = {}
    for doc in Documento.objects.select_related('categoria').all():
        grupos.setdefault(doc.categoria_id, []).append(doc)
    return grupos


def _gerar_config_js():
    repo = getattr(settings, 'GITHUB_REPO', '')
    branch = _branch()
    return (
        f'/* Gerado automaticamente — não editar */\n'
        f'window.BIBLIOTECA_REPO = "{repo}";\n'
        f'window.BIBLIOTECA_BRANCH = "{branch}";\n'
    )


def _gerar_mkdocs_yml(grupos):
    from biblioteca.models import Categoria
    categorias = Categoria.objects.order_by('nome')

    nav_linhas = ['  - Início: index.md']
    for cat in categorias:
        docs = sorted(grupos.get(cat.pk, []), key=lambda d: d.ordem)
        if not docs:
            continue
        nav_linhas.append(f'  - {cat.nome}:')
        for doc in docs:
            filename = f'{doc.ordem:02d}-{doc.slug}.md'
            nav_linhas.append(f'    - {doc.titulo}: {cat.slug}/{filename}')

    nav_block = '\n'.join(nav_linhas)

    return f"""site_name: Biblioteca de Leitura
docs_dir: docs

theme:
  name: material
  language: pt
  features:
    - navigation.tabs
    - navigation.top
    - toc.integrate
    - content.action.view
  palette:
    - scheme: default
      toggle:
        icon: material/brightness-7
        name: Modo escuro
    - scheme: slate
      toggle:
        icon: material/brightness-4
        name: Modo claro
  font:
    text: Roboto
    code: Roboto Mono

extra_javascript:
  - js/config.js
  - js/progress.js

nav:
{nav_block}
"""


def _gerar_index_md(grupos):
    from biblioteca.models import Categoria, Documento
    total = Documento.objects.count()
    lidos = Documento.objects.filter(lido=True).count()
    pct = (lidos / total * 100) if total else 0
    agora = datetime.now().strftime('%d/%m/%Y %H:%M')

    linhas = [
        '# Biblioteca de Leitura\n',
        f'**Progresso geral:** {lidos}/{total} documentos lidos ({pct:.1f}%)\n\n',
        f'*Atualizado em: {agora}*\n\n',
        '---\n\n',
    ]

    for cat in Categoria.objects.order_by('nome'):
        docs = sorted(grupos.get(cat.pk, []), key=lambda d: d.ordem)
        if not docs:
            continue
        lidos_cat = sum(1 for d in docs if d.lido)
        linhas.append(f'## {cat.nome} ({lidos_cat}/{len(docs)})\n\n')
        if cat.descricao:
            linhas.append(f'{cat.descricao}\n\n')
        for doc in docs:
            icone = '✅' if doc.lido else '⬜'
            filename = f'{doc.ordem:02d}-{doc.slug}.md'
            linhas.append(f'- {icone} [{doc.titulo}]({cat.slug}/{filename})\n')
        linhas.append('\n')

    return ''.join(linhas)


def _gerar_progress_json():
    from biblioteca.models import Documento
    progress = {}
    for doc in Documento.objects.select_related('categoria').all():
        # Chave: caminho relativo sem docs/ (ex: "legislacao/01-lei-xyz.md")
        path_key = f'{doc.categoria.slug}/{doc.ordem:02d}-{doc.slug}.md'
        progress[path_key] = {
            'lido': doc.lido,
            'data_leitura': doc.data_leitura.isoformat() if doc.data_leitura else None,
            'titulo': doc.titulo,
            'slug': doc.slug,
        }
    return json.dumps(progress, ensure_ascii=False, indent=2)


def publicar_documentos(documentos=None):
    """
    Publica documentos no GitHub.
    Se `documentos` for None, publica todos os não publicados.
    Retorna dict com chaves 'publicados' e 'erros'.
    """
    from biblioteca.models import Documento, SyncLog

    repo = _get_repo()
    branch = _branch()

    if documentos is None:
        documentos = list(
            Documento.objects.filter(publicado_github=False).select_related('categoria')
        )

    publicados = 0
    erros = []
    detalhes = []

    for doc in documentos:
        try:
            path = doc.get_github_path()
            if doc.formato == 'md':
                conteudo = f'# {doc.titulo}\n\n{doc.conteudo}'
            else:
                conteudo = doc.conteudo

            _upsert_file(repo, path, conteudo, f'docs: adiciona "{doc.titulo}"')
            doc.publicado_github = True
            doc.github_path = path
            doc.save(update_fields=['publicado_github', 'github_path'])
            publicados += 1
            detalhes.append(f'✓ {path}')
        except Exception as e:
            erros.append(f'"{doc.titulo}": {e}')

    # Arquivos de suporte (sempre regenerados)
    grupos = _todos_documentos_agrupados()
    arquivos_suporte = [
        ('mkdocs.yml', _gerar_mkdocs_yml(grupos), 'chore: atualiza mkdocs.yml'),
        ('docs/index.md', _gerar_index_md(grupos), 'docs: atualiza índice'),
        ('progress.json', _gerar_progress_json(), 'chore: atualiza progress.json'),
        ('docs/js/config.js', _gerar_config_js(), 'chore: atualiza config.js'),
    ]
    for path, conteudo, msg in arquivos_suporte:
        try:
            _upsert_file(repo, path, conteudo, msg)
            detalhes.append(f'✓ {path}')
        except Exception as e:
            erros.append(f'Arquivo de suporte "{path}": {e}')

    SyncLog.objects.create(
        tipo='publicar',
        documentos_afetados=publicados,
        erros='\n'.join(erros),
        detalhes='\n'.join(detalhes),
    )

    return {'publicados': publicados, 'erros': '\n'.join(erros)}
