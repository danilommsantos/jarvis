"""Sincroniza o progress.json do GitHub com o banco de dados local."""
import json
from datetime import datetime, timezone

from django.conf import settings


def _get_repo():
    from github import Github
    g = Github(settings.GITHUB_TOKEN)
    return g.get_repo(settings.GITHUB_REPO)


def sincronizar(documentos=None):
    """
    Lê progress.json do repositório e atualiza os campos lido/data_leitura.
    Se `documentos` for None, sincroniza todos os documentos.
    Retorna dict com chaves 'atualizados' e 'erros'.
    """
    from github import GithubException
    from biblioteca.models import Documento, SyncLog

    branch = getattr(settings, 'GITHUB_BRANCH', 'main')
    repo = _get_repo()

    try:
        contents = repo.get_contents('progress.json', ref=branch)
        progress = json.loads(contents.decoded_content.decode('utf-8'))
    except GithubException as e:
        msg = 'progress.json não encontrado no repositório.' if e.status == 404 else str(e)
        SyncLog.objects.create(tipo='sincronizar', documentos_afetados=0, erros=msg)
        return {'atualizados': 0, 'erros': msg}
    except json.JSONDecodeError as e:
        msg = f'Erro ao decodificar progress.json: {e}'
        SyncLog.objects.create(tipo='sincronizar', documentos_afetados=0, erros=msg)
        return {'atualizados': 0, 'erros': msg}

    if documentos is None:
        documentos = list(Documento.objects.select_related('categoria').all())

    atualizados = 0
    erros = []

    for doc in documentos:
        path_key = f'{doc.categoria.slug}/{doc.ordem:02d}-{doc.slug}.md'
        if path_key not in progress:
            continue

        info = progress[path_key]
        novo_lido = bool(info.get('lido', False))
        nova_data_str = info.get('data_leitura')

        changed = False

        if doc.lido != novo_lido:
            doc.lido = novo_lido
            changed = True

        if nova_data_str:
            try:
                dt = datetime.fromisoformat(nova_data_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if doc.data_leitura != dt:
                    doc.data_leitura = dt
                    changed = True
            except ValueError:
                erros.append(f'Data inválida para "{doc.titulo}": {nova_data_str}')
        elif novo_lido and not doc.data_leitura:
            # Marcado como lido sem data — usa agora
            doc.data_leitura = datetime.now(tz=timezone.utc)
            changed = True

        if changed:
            doc.save(update_fields=['lido', 'data_leitura'])
            atualizados += 1

    SyncLog.objects.create(
        tipo='sincronizar',
        documentos_afetados=atualizados,
        erros='\n'.join(erros),
        detalhes=f'Sincronizados {atualizados} de {len(documentos)} documento(s).',
    )

    return {'atualizados': atualizados, 'erros': '\n'.join(erros)}
