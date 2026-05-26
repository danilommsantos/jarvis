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


def _gerar_github_actions_workflow():
    return """\
name: Deploy MkDocs to Cloudflare Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.x'

      - uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Build MkDocs
        run: |
          pip install mkdocs-material
          mkdocs build

      - name: Install Wrangler
        run: npm install -g wrangler

      - name: Create Pages project (if not exists)
        run: wrangler pages project create biblioteca-pessoal --production-branch main || true
        env:
          CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}

      - name: Deploy to Cloudflare Pages
        run: wrangler pages deploy site --project-name biblioteca-pessoal --commit-dirty=true
        env:
          CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
"""


def _gerar_reader_css():
    return """\
/* Painel de controles de leitura — gerado automaticamente */

/* Fix: inline color/background dos documentos colados no modo escuro do tema */
[data-md-color-scheme="slate"] .md-content__inner *,
[data-md-color-scheme="slate"] .md-content article * {
  color: inherit !important;
  background-color: transparent !important;
}

/* Modo Noturno (fundo preto para máximo contraste) */
body.rdr-nocturno .md-content__inner {
  background-color: #050505 !important;
  color: #e0e0e0 !important;
}
body.rdr-nocturno .md-content__inner * {
  color: inherit !important;
  background-color: transparent !important;
}
body.rdr-nocturno .md-content__inner pre,
body.rdr-nocturno .md-content__inner code {
  background-color: #141414 !important;
}

/* Nav de paginação — fixo na parte inferior central */
#rdr-pag-nav {
  position: fixed;
  bottom: 1.75rem;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9998;
  align-items: center;
  gap: .75rem;
  background: var(--md-default-bg-color, #fff);
  border: 1px solid rgba(0,0,0,.14);
  border-radius: 2rem;
  box-shadow: 0 4px 18px rgba(0,0,0,.18);
  padding: .45rem 1rem;
}
[data-md-color-scheme="slate"] #rdr-pag-nav {
  border-color: rgba(255,255,255,.14);
}

#rdr-wrap {
  position: fixed;
  bottom: 1.75rem;
  right: 1.75rem;
  z-index: 9999;
  font-family: inherit;
}
.rdr-panel {
  background: var(--md-default-bg-color, #fff);
  border: 1px solid rgba(0,0,0,.14);
  border-radius: .5rem;
  box-shadow: 0 4px 18px rgba(0,0,0,.18);
  padding: .9rem 1rem;
  min-width: 205px;
  margin-bottom: .55rem;
}
[data-md-color-scheme="slate"] .rdr-panel {
  border-color: rgba(255,255,255,.14);
}
.rdr-label {
  font-size: .67rem;
  font-weight: 700;
  letter-spacing: .07em;
  text-transform: uppercase;
  color: var(--md-default-fg-color--light, #666);
  margin: 0 0 .4rem;
}
.rdr-label + .rdr-label { margin-top: .75rem; }
.rdr-row { display: flex; align-items: center; gap: .35rem; }
.rdr-btn {
  background: transparent;
  border: 1px solid rgba(0,0,0,.2);
  border-radius: .3rem;
  color: var(--md-default-fg-color, #333);
  cursor: pointer;
  font-size: .8rem;
  padding: .22rem .5rem;
  transition: background .12s;
}
.rdr-btn:hover { background: rgba(0,0,0,.07); }
.rdr-btn:disabled { opacity: .4; cursor: default; }
.rdr-btn.active {
  background: var(--md-primary-fg-color, #1976d2);
  border-color: var(--md-primary-fg-color, #1976d2);
  color: var(--md-primary-bg-color, #fff);
}
[data-md-color-scheme="slate"] .rdr-btn { border-color: rgba(255,255,255,.2); }
.rdr-val {
  font-size: .85rem;
  font-weight: 700;
  min-width: 38px;
  text-align: center;
  color: var(--md-default-fg-color, #333);
}
.rdr-flex { flex: 1; text-align: center; }
.rdr-toggle {
  display: block;
  margin-left: auto;
  background: var(--md-primary-fg-color, #1976d2);
  border: none;
  border-radius: 2rem;
  box-shadow: 0 2px 8px rgba(0,0,0,.25);
  color: var(--md-primary-bg-color, #fff);
  cursor: pointer;
  font-size: .82rem;
  font-weight: 600;
  padding: .5rem 1.1rem;
  transition: opacity .15s;
}
.rdr-toggle:hover { opacity: .88; }
"""


def _gerar_reader_js():
    return """\
/* Controles de leitura — gerado automaticamente */
(function () {
  var LS_F  = 'bib_font_size';
  var LS_L  = 'bib_line_height';
  var LS_DK = 'bib_dark';
  var MIN = 12, MAX = 26;
  var fs   = parseFloat(localStorage.getItem(LS_F))  || 16;
  var lh   = parseFloat(localStorage.getItem(LS_L))  || 1;
  var dark = localStorage.getItem(LS_DK) === '1';
  var pagOn = false;
  var curPage = 0;
  var totalPages = 1;

  function contentEl() {
    return document.querySelector('.md-content__inner article') ||
           document.querySelector('article') ||
           document.querySelector('.md-content__inner');
  }

  function dynStyle() {
    var el = document.getElementById('rdr-dyn');
    if (!el) {
      el = document.createElement('style');
      el.id = 'rdr-dyn';
      document.head.appendChild(el);
    }
    return el;
  }

  function apply() {
    var sel = '.md-content__inner';
    dynStyle().textContent =
      sel + ', ' + sel + ' article { font-size: ' + fs + 'pt !important; line-height: ' + lh + ' !important; max-width: 70ch; }\\n' +
      sel + ' * { font-size: inherit !important; line-height: inherit !important; }\\n' +
      sel + ' h1 { font-size: 1.75em !important; }\\n' +
      sel + ' h2 { font-size: 1.4em  !important; }\\n' +
      sel + ' h3 { font-size: 1.15em !important; }\\n' +
      sel + ' pre, ' + sel + ' code { font-size: .875em !important; }';
    var v = document.getElementById('rdr-val');
    if (v) v.textContent = fs + 'pt';
    document.querySelectorAll('.rdr-lh').forEach(function (b) {
      b.classList.toggle('active', parseFloat(b.dataset.lh) === lh);
    });
  }

  function applyDark() {
    document.body.classList.toggle('rdr-nocturno', dark);
    var btn = document.getElementById('rdr-dk');
    if (btn) btn.classList.toggle('active', dark);
  }

  /* ── Paginação ─────────────────────────────────────────── */
  function artH() {
    var el = contentEl();
    return el ? el.clientHeight : window.innerHeight;
  }

  function calcPages() {
    var el = contentEl();
    if (el) totalPages = Math.max(1, Math.ceil(el.scrollHeight / artH()));
  }

  function showPageInfo() {
    var info = document.getElementById('rdr-page-info');
    if (info) info.textContent = (curPage + 1) + ' / ' + totalPages;
    var prev = document.getElementById('rdr-prev');
    var next = document.getElementById('rdr-next');
    if (prev) prev.disabled = curPage === 0;
    if (next) next.disabled = curPage >= totalPages - 1;
  }

  function gotoPage(n) {
    var el = contentEl();
    if (!el) return;
    curPage = Math.max(0, Math.min(n, totalPages - 1));
    el.scrollTop = curPage * artH();
    localStorage.setItem('bib_pos_' + window.location.pathname, curPage);
    showPageInfo();
  }

  function enablePag() {
    var el = contentEl();
    if (!el) return;
    pagOn = true;
    el.style.height = Math.max(300, Math.round(window.innerHeight * 0.68)) + 'px';
    el.style.overflowY = 'scroll';
    el.style.scrollbarWidth = 'none';
    var nav = document.getElementById('rdr-pag-nav');
    if (nav) nav.style.display = 'flex';
    var btn = document.getElementById('rdr-pag-btn');
    if (btn) btn.classList.add('active');
    setTimeout(function () {
      calcPages();
      var saved = parseInt(localStorage.getItem('bib_pos_' + window.location.pathname)) || 0;
      gotoPage(Math.min(saved, totalPages - 1));
    }, 60);
  }

  function disablePag() {
    var el = contentEl();
    if (!el) return;
    pagOn = false;
    el.style.height = '';
    el.style.overflowY = '';
    el.style.scrollbarWidth = '';
    var nav = document.getElementById('rdr-pag-nav');
    if (nav) nav.style.display = 'none';
    var btn = document.getElementById('rdr-pag-btn');
    if (btn) btn.classList.remove('active');
  }

  function inject() {
    if (document.getElementById('rdr-wrap')) { apply(); applyDark(); return; }

    var wrap = document.createElement('div');
    wrap.id = 'rdr-wrap';
    wrap.innerHTML =
      '<div id="rdr-panel" class="rdr-panel" style="display:none">' +
        '<p class="rdr-label">Fonte</p>' +
        '<div class="rdr-row">' +
          '<button id="rdr-dec" class="rdr-btn" title="Diminuir">A−</button>' +
          '<span id="rdr-val" class="rdr-val"></span>' +
          '<button id="rdr-inc" class="rdr-btn" title="Aumentar">A+</button>' +
        '</div>' +
        '<p class="rdr-label">Espaçamento</p>' +
        '<div class="rdr-row">' +
          '<button data-lh="1"   class="rdr-lh rdr-btn rdr-flex">1×</button>' +
          '<button data-lh="1.5" class="rdr-lh rdr-btn rdr-flex">1,5×</button>' +
          '<button data-lh="2"   class="rdr-lh rdr-btn rdr-flex">2×</button>' +
        '</div>' +
        '<p class="rdr-label">Leitura</p>' +
        '<div class="rdr-row">' +
          '<button id="rdr-dk"      class="rdr-btn rdr-flex" title="Fundo preto">☾ Noturno</button>' +
          '<button id="rdr-pag-btn" class="rdr-btn rdr-flex" title="Página a página">⊞ Páginas</button>' +
        '</div>' +
      '</div>' +
      '<button id="rdr-toggle" class="rdr-toggle">Aa Leitura</button>';
    document.body.appendChild(wrap);

    var nav = document.createElement('div');
    nav.id = 'rdr-pag-nav';
    nav.style.display = 'none';
    nav.innerHTML =
      '<button id="rdr-prev" class="rdr-btn">← Anterior</button>' +
      '<span id="rdr-page-info" class="rdr-val" style="min-width:60px;text-align:center;"></span>' +
      '<button id="rdr-next" class="rdr-btn">Próxima →</button>';
    document.body.appendChild(nav);

    document.getElementById('rdr-toggle').onclick = function () {
      var p = document.getElementById('rdr-panel');
      p.style.display = p.style.display === 'none' ? 'block' : 'none';
    };
    document.getElementById('rdr-dec').onclick = function () {
      fs = Math.max(MIN, fs - 1); localStorage.setItem(LS_F, fs); apply();
      if (pagOn) { setTimeout(function () { calcPages(); gotoPage(curPage); }, 60); }
    };
    document.getElementById('rdr-inc').onclick = function () {
      fs = Math.min(MAX, fs + 1); localStorage.setItem(LS_F, fs); apply();
      if (pagOn) { setTimeout(function () { calcPages(); gotoPage(curPage); }, 60); }
    };
    document.querySelectorAll('.rdr-lh').forEach(function (b) {
      b.onclick = function () {
        lh = parseFloat(b.dataset.lh); localStorage.setItem(LS_L, lh); apply();
        if (pagOn) { setTimeout(function () { calcPages(); gotoPage(curPage); }, 60); }
      };
    });
    document.getElementById('rdr-dk').onclick = function () {
      dark = !dark;
      localStorage.setItem(LS_DK, dark ? '1' : '0');
      applyDark();
    };
    document.getElementById('rdr-pag-btn').onclick = function () {
      if (pagOn) disablePag(); else enablePag();
    };
    document.getElementById('rdr-prev').onclick = function () { gotoPage(curPage - 1); };
    document.getElementById('rdr-next').onclick = function () { gotoPage(curPage + 1); };
    document.addEventListener('keydown', function (e) {
      if (!pagOn) return;
      if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === 'ArrowDown') {
        e.preventDefault(); gotoPage(curPage + 1);
      } else if (e.key === 'ArrowLeft' || e.key === 'PageUp' || e.key === 'ArrowUp') {
        e.preventDefault(); gotoPage(curPage - 1);
      }
    });
    apply();
    applyDark();
  }

  /* Injeção inicial e re-aplicação em navegação SPA do Material */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inject);
  } else {
    inject();
  }
  if (typeof document$ !== 'undefined' && document$.subscribe) {
    document$.subscribe(function () {
      if (pagOn) disablePag();
      curPage = 0;
      setTimeout(inject, 80);
    });
  }
})();
"""


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

extra_css:
  - css/reader.css

extra_javascript:
  - js/config.js
  - js/progress.js
  - js/reader.js

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
        ('docs/js/reader.js', _gerar_reader_js(), 'chore: atualiza reader.js'),
        ('docs/css/reader.css', _gerar_reader_css(), 'chore: atualiza reader.css'),
        ('.github/workflows/deploy.yml', _gerar_github_actions_workflow(), 'ci: workflow GitHub Actions'),
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
