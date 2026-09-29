/* ============================================================
   TransAfrik — Détection de mise à jour
   Affiche un bandeau « Nouvelle mise à jour disponible » quand
   une nouvelle version est déployée sur le serveur.
   ============================================================ */
(function () {
  'use strict';

  var CURRENT_VERSION = window.__APP_VERSION__ || '1.0.0';
  var DISMISSED_KEY = 'transafrik_update_dismissed';
  var CHECK_INTERVAL = 30000; // 30 secondes

  var css = [
    '#update-banner{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);z-index:99999;',
    'display:flex;align-items:center;gap:14px;background:#0F172A;color:#fff;border-radius:16px;',
    'padding:14px 18px;box-shadow:0 12px 40px rgba(0,0,0,.35);max-width:92vw;width:460px;',
    'font-family:Inter,Arial,sans-serif;animation:ub-slide-up .3s ease;border:1px solid rgba(255,255,255,.08)}',
    '#update-banner .ub-icon{width:42px;height:42px;border-radius:12px;background:linear-gradient(135deg,#2563EB,#10B981);',
    'display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0}',
    '#update-banner .ub-body{flex:1;min-width:0}',
    '#update-banner .ub-title{font-weight:700;font-size:14px;line-height:1.3}',
    '#update-banner .ub-sub{font-size:12px;opacity:.75;margin-top:2px}',
    '#update-banner .ub-btn{padding:10px 18px;border:none;border-radius:10px;background:linear-gradient(135deg,#2563EB,#1D4ED8);',
    'color:#fff;font-weight:700;font-size:13px;cursor:pointer;white-space:nowrap;transition:all .2s}',
    '#update-banner .ub-btn:hover{transform:translateY(-1px);box-shadow:0 6px 18px rgba(37,99,235,.4)}',
    '#update-banner .ub-close{background:transparent;border:none;color:rgba(255,255,255,.6);font-size:20px;cursor:pointer;',
    'padding:4px;line-height:1;flex-shrink:0}',
    '#update-banner .ub-close:hover{color:#fff}',
    '@keyframes ub-slide-up{from{opacity:0;transform:translate(-50%,20px)}to{opacity:1;transform:translate(-50%,0)}}'
  ].join('');

  function injectCss() {
    if (document.getElementById('ub-style')) return;
    var style = document.createElement('style');
    style.id = 'ub-style';
    style.textContent = css;
    document.head.appendChild(style);
  }

  function showBanner(version) {
    if (document.getElementById('update-banner')) return;
    if (localStorage.getItem(DISMISSED_KEY) === version) return;

    injectCss();

    var banner = document.createElement('div');
    banner.id = 'update-banner';
    banner.innerHTML =
      '<div class="ub-icon">🔄</div>' +
      '<div class="ub-body">' +
        '<div class="ub-title">Nouvelle mise à jour disponible</div>' +
        '<div class="ub-sub">Améliorez votre compte en effectuant la mise à jour.</div>' +
      '</div>' +
      '<button class="ub-btn" id="ub-update-btn">Mettre à jour</button>' +
      '<button class="ub-close" title="Fermer">&times;</button>';

    banner.querySelector('#ub-update-btn').addEventListener('click', function () {
      window.location.reload();
    });
    banner.querySelector('.ub-close').addEventListener('click', function () {
      localStorage.setItem(DISMISSED_KEY, version);
      banner.remove();
    });

    document.body.appendChild(banner);
  }

  function check() {
    fetch('/api/version', { cache: 'no-store', headers: { 'Accept': 'application/json' } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var latest = d && d.version;
        if (latest && latest !== CURRENT_VERSION) {
          showBanner(latest);
        }
      })
      .catch(function () { /* silencieux */ });
  }

  // Première vérification rapide, puis périodique
  setTimeout(check, 3000);
  setInterval(check, CHECK_INTERVAL);
})();
