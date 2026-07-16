/* ============================================================
   TransAfrik PWA — v1.0.0
   Gère : Installation, iOS, Mise à jour, Push Notifications
   ============================================================ */

(function () {
  'use strict';

  /* ==========================================================
     SERVICE WORKER REGISTRATION
     ========================================================== */
  function registerSW() {
    if (!('serviceWorker' in navigator)) {
      console.warn('[PWA] Service Worker non supporté.');
      return;
    }

    const swPath = '/sw.js';

    navigator.serviceWorker.register(swPath, { scope: '/' })
      .then(registration => {
        console.log('[PWA] SW enregistré — scope:', registration.scope);

        // Vérifier s'il y a une mise à jour en attente
        if (registration.waiting) {
          handleUpdate(registration);
        }

        // Écouter les mises à jour futures
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          if (!newWorker) return;
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              handleUpdate(registration);
            }
          });
        });

        // Écouter les changements de contrôleur (après skipWaiting)
        navigator.serviceWorker.addEventListener('controllerchange', () => {
          console.log('[PWA] Nouveau SW actif — rechargement');
          window.location.reload();
        });

        // Vérifier les mises à jour périodiquement (toutes les 30 min)
        setInterval(() => {
          registration.update().catch(() => {});
        }, 30 * 60 * 1000);

        // Demander les permissions de notification
        setupPushNotifications(registration);
      })
      .catch(err => {
        console.error('[PWA] Échec enregistrement SW:', err);
      });
  }

  /* ==========================================================
     MISE À JOUR
     ========================================================== */
  function handleUpdate(registration) {
    // Ne pas spammer — une seule bannière par session
    if (sessionStorage.getItem('pwa_update_shown')) return;
    sessionStorage.setItem('pwa_update_shown', '1');

    showUpdateBanner(() => {
      if (registration.waiting) {
        registration.waiting.postMessage('SKIP_WAITING');
      }
    });
  }

  function showUpdateBanner(onUpdate) {
    // Éviter les doublons
    if (document.getElementById('pwa-update-banner')) return;

    const banner = document.createElement('div');
    banner.id = 'pwa-update-banner';
    banner.innerHTML = `
      <div style="
        position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:99999;
        background:linear-gradient(135deg,#1E3A8A,#2563EB);color:#fff;
        padding:16px 24px;border-radius:18px;
        font-family:'Inter',sans-serif;font-size:14px;font-weight:600;
        display:flex;align-items:center;gap:16px;
        box-shadow:0 16px 48px rgba(37,99,235,.4);
        animation:slideUp 0.4s ease;max-width:90vw;flex-wrap:wrap;justify-content:center;
      ">
        <span><i class="fa-solid fa-rocket" style="margin-right:8px"></i>Une nouvelle version est disponible</span>
        <button id="pwa-update-btn" style="
          padding:10px 20px;background:#fff;color:#2563EB;
          border:none;border-radius:10px;font-weight:700;font-size:13px;
          cursor:pointer;font-family:'Inter',sans-serif;transition:all 0.2s;
        ">Mettre à jour</button>
        <button id="pwa-update-close" style="
          background:none;border:none;color:rgba(255,255,255,.7);
          cursor:pointer;font-size:18px;padding:4px;
        "><i class="fa-solid fa-xmark"></i></button>
      </div>
      <style>
        @keyframes slideUp{from{opacity:0;transform:translateX(-50%) translateY(30px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}
      </style>
    `;

    document.body.appendChild(banner);

    document.getElementById('pwa-update-btn').addEventListener('click', () => {
      banner.remove();
      if (onUpdate) onUpdate();
    });

    document.getElementById('pwa-update-close').addEventListener('click', () => {
      banner.remove();
    });
  }

  /* ==========================================================
     INSTALLATION BANNIÈRE PREMIUM
     ========================================================== */

  let deferredPrompt = null;
  const INSTALL_STORAGE_KEY = 'pwa_install_rejected_at';

  function setupInstallBanner() {
    // Écouter le prompt d'installation natif
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      deferredPrompt = e;
      maybeShowInstallBanner();
    });

    // Détecter si l'app est déjà installée
    window.addEventListener('appinstalled', () => {
      console.log('[PWA] Application installée');
      deferredPrompt = null;
      localStorage.removeItem(INSTALL_STORAGE_KEY);
      const banner = document.getElementById('pwa-install-banner');
      if (banner) banner.remove();
    });

    // Si déjà en standalone, ne rien afficher
    if (isStandalone()) return;

    // Pour iOS : détection spéciale
    if (isIOS() && !isStandalone()) {
      setTimeout(showIOSInstallGuide, 5000);
    }
  }

  function maybeShowInstallBanner() {
    // Ne pas afficher si déjà montré cette semaine
    const rejectedAt = localStorage.getItem(INSTALL_STORAGE_KEY);
    if (rejectedAt) {
      const rejectedDate = new Date(parseInt(rejectedAt));
      const now = new Date();
      const diffDays = (now - rejectedDate) / (1000 * 60 * 60 * 24);
      if (diffDays < 7) return;
    }

    // Ne pas afficher si déjà en standalone
    if (isStandalone()) return;

    // Ne pas afficher sur iOS (géré séparément)
    if (isIOS()) return;

    // Afficher après 3 secondes
    setTimeout(showInstallBanner, 3000);
  }

  function showInstallBanner() {
    if (document.getElementById('pwa-install-banner')) return;

    const banner = document.createElement('div');
    banner.id = 'pwa-install-banner';
    banner.innerHTML = `
      <div style="
        position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:99998;
        background:linear-gradient(135deg,#0B1120,#111827);color:#F1F5F9;
        padding:20px 28px;border-radius:20px;
        font-family:'Inter',sans-serif;
        display:flex;align-items:center;gap:20px;
        box-shadow:0 20px 60px rgba(0,0,0,.5),0 0 0 1px rgba(37,99,235,.2);
        animation:slideUp 0.5s ease;max-width:95vw;flex-wrap:wrap;justify-content:center;
        border:1px solid rgba(37,99,235,.3);backdrop-filter:blur(20px);
      ">
        <div style="display:flex;align-items:center;gap:12px">
          <img src="/static/logo.png" alt="TransAfrik" style="width:44px;height:44px;border-radius:12px" onerror="this.style.display='none'">
          <div>
            <div style="font-weight:800;font-size:15px;font-family:'Outfit',sans-serif">Installer TransAfrik</div>
            <div style="font-size:12px;color:#94A3B8;margin-top:2px">Accès rapide, notifications, hors-ligne</div>
          </div>
        </div>
        <div style="display:flex;gap:8px">
          <button id="pwa-install-btn" style="
            padding:10px 22px;background:linear-gradient(135deg,#2563EB,#1D4ED8);
            color:#fff;border:none;border-radius:12px;font-weight:700;font-size:13px;
            cursor:pointer;font-family:'Inter',sans-serif;white-space:nowrap;
            box-shadow:0 4px 16px rgba(37,99,235,.3);transition:all 0.2s;
          "><i class="fa-solid fa-download" style="margin-right:6px"></i>Installer</button>
          <button id="pwa-install-later" style="
            padding:10px 18px;background:rgba(255,255,255,.05);
            color:#CBD5E1;border:1px solid rgba(255,255,255,.1);border-radius:12px;
            font-weight:600;font-size:12px;cursor:pointer;font-family:'Inter',sans-serif;white-space:nowrap;transition:all 0.2s;
          ">Plus tard</button>
          <button id="pwa-install-close" style="
            background:none;border:none;color:#64748B;
            cursor:pointer;font-size:16px;padding:4px;
          "><i class="fa-solid fa-xmark"></i></button>
        </div>
      </div>
      <style>
        @keyframes slideUp{from{opacity:0;transform:translateX(-50%) translateY(30px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}
      </style>
    `;

    document.body.appendChild(banner);

    document.getElementById('pwa-install-btn').addEventListener('click', async () => {
      banner.remove();
      if (deferredPrompt) {
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        console.log('[PWA] Choix installation:', outcome);
        deferredPrompt = null;
      }
    });

    document.getElementById('pwa-install-later').addEventListener('click', () => {
      banner.remove();
      localStorage.setItem(INSTALL_STORAGE_KEY, Date.now().toString());
    });

    document.getElementById('pwa-install-close').addEventListener('click', () => {
      banner.remove();
      localStorage.setItem(INSTALL_STORAGE_KEY, Date.now().toString());
    });
  }

  /* ==========================================================
     iOS INSTALL GUIDE
     ========================================================== */
  function isIOS() {
    return /iphone|ipad|ipod/.test(navigator.userAgent.toLowerCase());
  }

  function isStandalone() {
    return window.matchMedia('(display-mode: standalone)').matches ||
           navigator.standalone ||
           document.referrer.includes('android-app://');
  }

  function showIOSInstallGuide() {
    if (document.getElementById('pwa-ios-guide')) return;
    if (sessionStorage.getItem('pwa_ios_guide_shown')) return;
    sessionStorage.setItem('pwa_ios_guide_shown', '1');

    const guide = document.createElement('div');
    guide.id = 'pwa-ios-guide';
    guide.innerHTML = `
      <div style="
        position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:99997;
        background:linear-gradient(135deg,#0B1120,#111827);color:#F1F5F9;
        padding:24px;border-radius:20px;
        font-family:'Inter',sans-serif;
        box-shadow:0 20px 60px rgba(0,0,0,.5),0 0 0 1px rgba(37,99,235,.2);
        animation:slideUp 0.5s ease;max-width:380px;width:90vw;
        border:1px solid rgba(37,99,235,.3);backdrop-filter:blur(20px);
      ">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
          <div style="display:flex;align-items:center;gap:10px">
            <img src="/static/logo.png" alt="TransAfrik" style="width:36px;height:36px;border-radius:10px" onerror="this.style.display='none'">
            <div>
              <div style="font-weight:800;font-size:14px;font-family:'Outfit',sans-serif">Installer TransAfrik</div>
              <div style="font-size:11px;color:#94A3B8">Sur iPhone / iPad</div>
            </div>
          </div>
          <button id="pwa-ios-close" style="background:none;border:none;color:#64748B;cursor:pointer;font-size:18px"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div style="display:flex;flex-direction:column;gap:14px;margin-bottom:16px">
          <div style="display:flex;align-items:center;gap:14px">
            <div style="width:32px;height:32px;border-radius:8px;background:#2563EB;display:flex;align-items:center;justify-content:center;flex-shrink:0">
              <i class="fa-solid fa-arrow-up-from-bracket" style="color:#fff;font-size:14px"></i>
            </div>
            <div>
              <div style="font-size:13px;font-weight:600">1. Appuyez sur <span style="color:#2563EB">Partager</span></div>
              <div style="font-size:11px;color:#94A3B8;margin-top:2px">dans la barre Safari en bas de l'écran</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:14px">
            <div style="width:32px;height:32px;border-radius:8px;background:#10B981;display:flex;align-items:center;justify-content:center;flex-shrink:0">
              <i class="fa-solid fa-square-plus" style="color:#fff;font-size:14px"></i>
            </div>
            <div>
              <div style="font-size:13px;font-weight:600">2. <span style="color:#10B981">Ajouter à l'écran d'accueil</span></div>
              <div style="font-size:11px;color:#94A3B8;margin-top:2px">faites défiler le menu si nécessaire</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:14px">
            <div style="width:32px;height:32px;border-radius:8px;background:#F59E0B;display:flex;align-items:center;justify-content:center;flex-shrink:0">
              <i class="fa-solid fa-check" style="color:#fff;font-size:14px"></i>
            </div>
            <div>
              <div style="font-size:13px;font-weight:600">3. Appuyez sur <span style="color:#F59E0B">Ajouter</span></div>
              <div style="font-size:11px;color:#94A3B8;margin-top:2px">pour confirmer l'installation</div>
            </div>
          </div>
        </div>
        <button id="pwa-ios-gotit" style="
          width:100%;padding:12px;background:linear-gradient(135deg,#2563EB,#1D4ED8);
          color:#fff;border:none;border-radius:12px;font-weight:700;font-size:13px;
          cursor:pointer;font-family:'Inter',sans-serif;
        ">Compris !</button>
      </div>
      <style>
        @keyframes slideUp{from{opacity:0;transform:translateX(-50%) translateY(30px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}
      </style>
    `;

    document.body.appendChild(guide);

    function removeGuide() { guide.remove(); }
    document.getElementById('pwa-ios-close').addEventListener('click', removeGuide);
    document.getElementById('pwa-ios-gotit').addEventListener('click', removeGuide);
  }

  /* ==========================================================
     PUSH NOTIFICATIONS
     ========================================================== */
  function setupPushNotifications(registration) {
    // Vérifier si les notifications sont supportées
    if (!('Notification' in window) || !('PushManager' in window)) {
      return;
    }

    // Ne pas redemander si déjà accordées
    if (Notification.permission === 'granted') {
      subscribeToPush(registration);
      return;
    }

    // Ne pas demander tout de suite — attendre une interaction utilisateur
    document.addEventListener('click', function askOnce() {
      if (Notification.permission === 'default') {
        Notification.requestPermission().then(permission => {
          if (permission === 'granted') {
            subscribeToPush(registration);
          }
        });
      }
      document.removeEventListener('click', askOnce);
    }, { once: true });
  }

  async function subscribeToPush(registration) {
    try {
      // Récupérer la clé publique VAPID depuis le backend
      let vapidPublicKey = null;
      try {
        const keyResp = await fetch('/api/push/vapid-public-key');
        const keyData = await keyResp.json();
        vapidPublicKey = keyData.public_key || null;
        if (vapidPublicKey) {
          console.log('[PWA] Clé VAPID récupérée depuis le serveur');
        }
      } catch (e) {
        console.warn('[PWA] Impossible de récupérer la clé VAPID:', e);
      }

      const subscribeOptions = {
        userVisibleOnly: true,
      };
      if (vapidPublicKey) {
        subscribeOptions.applicationServerKey = urlBase64ToUint8Array(vapidPublicKey);
      }

      let subscription = await registration.pushManager.getSubscription();
      if (!subscription) {
        subscription = await registration.pushManager.subscribe(subscribeOptions);
        console.log('[PWA] Abonnement push réussi');
      } else {
        console.log('[PWA] Abonnement push déjà actif');
      }

      // Envoyer l'abonnement au backend pour le stocker
      try {
        const response = await fetch('/api/push/subscribe', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            subscription: subscription.toJSON(),
          }),
        });
        const result = await response.json();
        if (result.success) {
          console.log('[PWA] Abonnement enregistré sur le serveur');
        } else {
          console.warn('[PWA] Échec enregistrement serveur:', result.error);
        }
      } catch (fetchErr) {
        console.warn('[PWA] Erreur réseau lors de l\'enregistrement push:', fetchErr);
      }

      // Stocker l'abonnement localement (pour désabonnement)
      localStorage.setItem('push_subscription', JSON.stringify(subscription.toJSON()));
    } catch (err) {
      console.warn('[PWA] Échec abonnement push:', err);
    }
  }

  function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/\-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  /* ==========================================================
     NETWORK STATUS DETECTION
     ========================================================== */
  function setupNetworkDetection() {
    window.addEventListener('online', () => {
      console.log('[PWA] Connexion rétablie');
      const toast = document.createElement('div');
      toast.style.cssText = `
        position:fixed;top:88px;right:24px;z-index:99999;
        background:#10B981;color:#fff;padding:12px 20px;
        border-radius:12px;font-family:'Inter',sans-serif;font-size:13px;font-weight:600;
        box-shadow:0 8px 24px rgba(16,185,129,.3);
        animation:slideInRight 0.4s ease;
      `;
      toast.innerHTML = '<i class="fa-solid fa-wifi" style="margin-right:8px"></i>Connexion rétablie';
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 3000);
    });

    window.addEventListener('offline', () => {
      console.log('[PWA] Hors connexion');
      const toast = document.createElement('div');
      toast.style.cssText = `
        position:fixed;top:88px;right:24px;z-index:99999;
        background:#F59E0B;color:#fff;padding:12px 20px;
        border-radius:12px;font-family:'Inter',sans-serif;font-size:13px;font-weight:600;
        box-shadow:0 8px 24px rgba(245,158,11,.3);
        animation:slideInRight 0.4s ease;
      `;
      toast.innerHTML = '<i class="fa-solid fa-triangle-exclamation" style="margin-right:8px"></i>Mode hors connexion';
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 3000);
    });

    // Injecter le style d'animation
    const style = document.createElement('style');
    style.textContent = '@keyframes slideInRight{from{opacity:0;transform:translateX(30px)}to{opacity:1;transform:translateX(0)}}';
    document.head.appendChild(style);
  }

  /* ==========================================================
     VIDER LE CACHE APRÈS DÉCONNEXION
     ========================================================== */
  function setupLogoutCleanup() {
    document.addEventListener('click', (e) => {
      const link = e.target.closest('a[href*="logout"]');
      if (link) {
        // Envoyer un message au SW pour vider les caches
        if (navigator.serviceWorker && navigator.serviceWorker.controller) {
          navigator.serviceWorker.controller.postMessage('CLEAR_ALL_CACHES');
        }
        // Vider le localStorage des données sensibles
        localStorage.removeItem('transafrik_balance');
        sessionStorage.clear();
      }
    });
  }

  /* ==========================================================
     INIT
     ========================================================== */
  document.addEventListener('DOMContentLoaded', () => {
    registerSW();
    setupInstallBanner();
    setupNetworkDetection();
    setupLogoutCleanup();
  });

  console.log('[PWA] Module TransAfrik initialisé');
})();