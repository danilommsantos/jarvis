/**
 * progress.js — Botão "Marcar como lido" para MkDocs + GitHub API
 * Otimizado para e-ink (Boox Note Air4): sem hover effects, botão grande, tap-friendly.
 *
 * Requer docs/js/config.js carregado antes:
 *   window.BIBLIOTECA_REPO = "usuario/repo";
 *   window.BIBLIOTECA_BRANCH = "main";
 */
(function () {
  'use strict';

  var REPO   = (window.BIBLIOTECA_REPO   || '').trim();
  var BRANCH = (window.BIBLIOTECA_BRANCH || 'main').trim();
  var PROGRESS_PATH = 'progress.json';

  // ── Utilitários ──────────────────────────────────────────────────────────

  function getToken() {
    return localStorage.getItem('biblioteca_github_pat') || '';
  }

  function salvarToken(token) {
    localStorage.setItem('biblioteca_github_pat', token.trim());
  }

  function getPageKey() {
    // MkDocs cria URLs como /categoria/01-slug/ → chave: "categoria/01-slug.md"
    var path = window.location.pathname
      .replace(/^\//, '')   // remove barra inicial
      .replace(/\/$/, '');  // remove barra final
    if (!path) return null;
    return path + '.md';
  }

  // ── GitHub API ───────────────────────────────────────────────────────────

  function apiHeaders(token) {
    return {
      'Authorization': 'token ' + token,
      'Accept': 'application/vnd.github.v3+json',
      'Content-Type': 'application/json',
    };
  }

  async function fetchProgress(token) {
    var url = 'https://api.github.com/repos/' + REPO +
              '/contents/' + PROGRESS_PATH + '?ref=' + BRANCH;
    var resp = await fetch(url, { headers: apiHeaders(token) });
    if (resp.status === 401) throw new Error('Token inválido ou expirado.');
    if (resp.status === 404) throw new Error('progress.json não encontrado no repositório.');
    if (!resp.ok) throw new Error('Erro HTTP ' + resp.status);
    var data = await resp.json();
    var decoded = JSON.parse(
      decodeURIComponent(
        escape(atob(data.content.replace(/\n/g, '')))
      )
    );
    return { content: decoded, sha: data.sha };
  }

  async function saveProgress(token, content, sha) {
    var url = 'https://api.github.com/repos/' + REPO + '/contents/' + PROGRESS_PATH;
    var encoded = btoa(
      unescape(encodeURIComponent(JSON.stringify(content, null, 2)))
    );
    var resp = await fetch(url, {
      method: 'PUT',
      headers: apiHeaders(token),
      body: JSON.stringify({
        message: 'progress: marcar leitura via browser',
        content: encoded,
        sha: sha,
        branch: BRANCH,
      }),
    });
    if (resp.status === 401) throw new Error('Token inválido. Apague e reconfigure.');
    if (!resp.ok) {
      var body = await resp.text();
      throw new Error('Erro ao salvar: ' + body);
    }
  }

  // ── UI ───────────────────────────────────────────────────────────────────

  var BTN_BASE = [
    'position:fixed',
    'bottom:24px',
    'right:24px',
    'z-index:9999',
    'padding:18px 28px',
    'font-size:20px',
    'font-weight:bold',
    'font-family:sans-serif',
    'line-height:1.2',
    'border-radius:10px',
    'cursor:pointer',
    'box-shadow:0 4px 14px rgba(0,0,0,0.35)',
    'min-width:160px',
    'text-align:center',
    'user-select:none',
    '-webkit-tap-highlight-color:transparent',
    'border:3px solid #333',
    'transition:none',      /* sem animação — e-ink */
    'outline:none',
  ].join(';');

  function aplicarEstiloLido(btn, lido) {
    if (lido) {
      btn.style.cssText = BTN_BASE + ';background:#2e7d32;color:#fff;border-color:#2e7d32';
      btn.textContent = '✓  Lido';
    } else {
      btn.style.cssText = BTN_BASE + ';background:#fff;color:#222;border-color:#555';
      btn.textContent = 'Marcar como lido';
    }
  }

  function estadoCarregando(btn) {
    btn.disabled = true;
    btn.style.background = '#e0e0e0';
    btn.style.color = '#888';
    btn.textContent = 'Aguarde...';
  }

  function estadoErro(btn) {
    btn.disabled = false;
    btn.style.cssText = BTN_BASE + ';background:#b71c1c;color:#fff;border-color:#b71c1c';
    btn.textContent = '⚠  Tente novamente';
  }

  // ── Inicialização ────────────────────────────────────────────────────────

  async function init() {
    if (!REPO) return;  // config.js não carregado ou REPO vazio

    var pageKey = getPageKey();
    if (!pageKey) return;  // página raiz, sem chave

    var token = getToken();
    var isLido = false;

    // Verificar status inicial (silencioso — não bloqueia a página)
    if (token) {
      try {
        var result = await fetchProgress(token);
        var entry = result.content[pageKey];
        isLido = !!(entry && entry.lido);
      } catch (e) {
        // Sem token ou erro de rede: exibe botão como não lido
      }
    }

    var btn = document.createElement('button');
    aplicarEstiloLido(btn, isLido);
    document.body.appendChild(btn);

    btn.addEventListener('click', async function () {
      if (btn.disabled) return;

      // Pedir token se não tiver
      var tok = getToken();
      if (!tok) {
        tok = (prompt(
          'Cole aqui seu GitHub Personal Access Token.\n' +
          '(Permissões necessárias: Contents — read & write)\n' +
          'O token será salvo apenas no seu navegador (localStorage).'
        ) || '').trim();
        if (!tok) return;
        salvarToken(tok);
      }

      estadoCarregando(btn);

      try {
        var result = await fetchProgress(tok);
        result.content[pageKey] = {
          lido: true,
          data_leitura: new Date().toISOString(),
        };
        await saveProgress(tok, result.content, result.sha);
        aplicarEstiloLido(btn, true);
      } catch (e) {
        estadoErro(btn);
        // Se token inválido, limpar do storage para forçar nova entrada
        if (e.message && e.message.indexOf('Token') !== -1) {
          localStorage.removeItem('biblioteca_github_pat');
        }
        setTimeout(function () { alert('Erro: ' + e.message); }, 50);
      }
    });
  }

  // Aguardar DOM pronto
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
