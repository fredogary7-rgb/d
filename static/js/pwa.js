/* ============================================================
   TransAfrik PWA — v2.0.0
   Gère : Installation, iOS, Mise à jour, Push Notifications
   Logs détaillés à chaque étape pour debug facile (F12 → Console)
   ============================================================ */

(function () {
  'use strict';

  const LOG_PREFIX = '[PWA]';
  const TAG = '🔔 PUSH';

  const PUSH_SUB_STORAGE_KEY = 'transafrik_push_sub';
  const PUSH_PENDING_KEY = 'transafrik_push_pending';

  let _pushRegistration = null;
  let _pushSetupDone = false;
  let _pushSyncing = false;  // Verrou pour éviter les synchronisations concurrentes

  /* ==========================================================
     SERVICE WORKER REGISTRATION
     ========================================================== */
  function registerSW() {
    console.log(LOG_PREFIX, '1️⃣  Début enregistrement Service Worker...');

    if (!('serviceWorker' in navigator)) {
      console.warn(LOG_PREFIX, '❌ Service Worker non supporté par ce navigateur.');
      return;
    }

    navigator.serviceWorker.register('/sw.js', { scope: '/' })
      .then(registration => {
        console.log(LOG_PREFIX, '✅ SW enregistré — scope:', registration.scope);
        console.log(LOG_PREFIX, '   SW state:', registration.active ? 'actif' : (registration.installing ? 'installation...' : (registration.waiting ? 'en attente' : 'inconnu')));

        // Vérifier s'il y a une mise à jour en attente
        if (registration.waiting) {
          console.log(LOG_PREFIX, '🔄 SW en attente détecté');
          handleUpdate(registration);
        }

        // Écouter les mises à jour futures
        registration.addEventListener('updatefound', () => {
          console.log(LOG_PREFIX, '🔄 Nouveau SW trouvé (updatefound)');
          const newWorker = registration.installing;
          if (!newWorker) return;
          newWorker.addEventListener('statechange', () => {
            console.log(LOG_PREFIX, '   Nouveau SW state:', newWorker.state);
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              handleUpdate(registration);
            }
          });
        });

        // Écouter les changements de contrôleur (après skipWaiting)
        navigator.serviceWorker.addEventListener('controllerchange', () => {
          console.log(LOG_PREFIX, '🔄 Nouveau contrôleur SW actif — rechargement');
          window.location.reload();
        });

        // Vérifier les mises à jour périodiquement (toutes les 30 min)
        setInterval(() => {
          registration.update().catch(() => {});
        }, 30 * 60 * 1000);

        // Lancer la configuration Push
        setupPushNotifications(registration);
      })
      .catch(err => {
        console.error(LOG_PREFIX, '❌ Échec enregistrement SW:', err.message, err);
      });
  }

  /* ==========================================================
     SW READY CHECK (attendre que registration soit prête)
     ========================================================== */
  function waitForSWReady() {
    return new Promise((resolve, reject) => {
      if (!('serviceWorker' in navigator)) {
        console.warn(LOG_PREFIX, TAG, '❌ SW non supporté');
        return reject(new Error('SW non supporté'));
      }

      navigator.serviceWorker.ready.then(registration => {
        console.log(LOG_PREFIX, TAG, '✅ SW prêt (registration.ready)');
        console.log(LOG_PREFIX, TAG, '   scope:', registration.scope);
        console.log(LOG_PREFIX, TAG, '   pushManager présent:', !!registration.pushManager);
        _pushRegistration = registration;
        resolve(registration);
      }).catch(err => {
        console.error(LOG_PREFIX, TAG, '❌ SW.ready a échoué:', err.message);
        reject(err);
      });
    });
  }

  /* ==========================================================
     MISE À JOUR
     ========================================================== */
  function handleUpdate(registration) {
    if (sessionStorage.getItem('pwa_update_shown')) return;
    sessionStorage.setItem('pwa_update_shown', '1');

    showUpdateBanner(() => {
      if (registration.waiting) {
        registration.waiting.postMessage('SKIP_WAITING');
      }
    });
  }

  function showUpdateBanner(onUpdate) {
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
      onUpdate();
    });
    document.getElementById('pwa-update-close').addEventListener('click', () => banner.remove());
  }

  /* ==========================================================
     INSTALLATION (BANNIÈRE PWA)
     ========================================================== */
  function setupInstallBanner() {
    let deferredPrompt = null;

    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      deferredPrompt = e;
      console.log(LOG_PREFIX, '📱 beforeinstallprompt reçu — PWA installable');

      const wasDismissed = sessionStorage.getItem('pwa_install_dismissed');
      if (wasDismissed) {
        console.log(LOG_PREFIX, '📱 Installation déjà proposée cette session');
        return;
      }

      showInstallBanner(() => {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(result => {
          console.log(LOG_PREFIX, '📱 Choix utilisateur:', result.outcome);
          deferredPrompt = null;
        });
      });
    });

    window.addEventListener('appinstalled', () => {
      console.log(LOG_PREFIX, '✅ PWA installée avec succès');
      deferredPrompt = null;
    });

    // Détection iOS
    const isIOS = /iphone|ipad|ipod/.test(navigator.userAgent.toLowerCase());
    const isStandalone = 'standalone' in navigator && navigator.standalone;
    if (isIOS && !isStandalone) {
      const wasShown = sessionStorage.getItem('pwa_ios_shown');
      if (!wasShown) {
        sessionStorage.setItem('pwa_ios_shown', '1');
        setTimeout(() => showIOSGuide(), 3000);
      }
    }
  }

  function showInstallBanner(onInstall) {
    if (document.getElementById('pwa-install-banner')) return;

    const banner = document.createElement('div');
    banner.id = 'pwa-install-banner';
    banner.innerHTML = `
      <div style="
        position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:99999;
        background:#fff;color:#0F172A;
        padding:20px 28px;border-radius:20px;
        font-family:'Inter',sans-serif;
        box-shadow:0 16px 48px rgba(0,0,0,.15);
        animation:slideUp 0.4s ease;max-width:90vw;
        display:flex;align-items:center;gap:16px;flex-wrap:wrap;justify-content:center;
      ">
        <img src="/static/logo.png" style="width:40px;height:40px;border-radius:10px" alt="">
        <div>
          <div style="font-weight:700;font-size:14px">Installer TransAfrik</div>
          <div style="font-size:11px;color:#64748B">Accès rapide depuis l'écran d'accueil</div>
        </div>
        <button id="pwa-install-btn" style="
          padding:10px 20px;background:#2563EB;color:#fff;
          border:none;border-radius:10px;font-weight:700;font-size:13px;
          cursor:pointer;font-family:'Inter',sans-serif;transition:all 0.2s;
        ">Installer</button>
        <button id="pwa-install-close" style="
          background:none;border:none;color:#94A3B8;
          cursor:pointer;font-size:18px;padding:4px;
        "><i class="fa-solid fa-xmark"></i></button>
      </div>
    `;

    document.body.appendChild(banner);
    document.getElementById('pwa-install-btn').addEventListener('click', () => { banner.remove(); onInstall(); });
    document.getElementById('pwa-install-close').addEventListener('click', () => {
      banner.remove();
      sessionStorage.setItem('pwa_install_dismissed', '1');
    });
  }

  function showIOSGuide() {
    if (document.getElementById('pwa-ios-guide')) return;

    const guide = document.createElement('div');
    guide.id = 'pwa-ios-guide';
    guide.innerHTML = `
      <div style="
        position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:99999;
        background:#fff;color:#0F172A;
        padding:24px;border-radius:20px;
        font-family:'Inter',sans-serif;
        box-shadow:0 16px 48px rgba(0,0,0,.15);
        animation:slideUp 0.4s ease;max-width:90vw;width:340px;
      ">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <div style="font-weight:800;font-size:15px">📱 Installer sur iPhone/iPad</div>
          <button id="pwa-ios-close" style="background:none;border:none;color:#94A3B8;cursor:pointer;font-size:18px"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div style="display:flex;flex-direction:column;gap:14px;font-size:12px;color:#475569">
          <div style="display:flex;align-items:center;gap:12px">
            <div style="width:32px;height:32px;border-radius:8px;background:#2563EB;display:flex;align-items:center;justify-content:center;flex-shrink:0">
              <i class="fa-solid fa-share-from-square" style="color:#fff;font-size:14px"></i>
            </div>
            <div>
              <div style="font-size:13px;font-weight:600">1. Appuyez sur <span style="color:#2563EB">Partager</span></div>
              <div style="font-size:11px;color:#94A3B8;margin-top:2px">dans la barre d'outils Safari</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:12px">
            <div style="width:32px;height:32px;border-radius:8px;background:#10B981;display:flex;align-items:center;justify-content:center;flex-shrink:0">
              <i class="fa-solid fa-plus" style="color:#fff;font-size:14px"></i>
            </div>
            <div>
              <div style="font-size:13px;font-weight:600">2. Sélectionnez <span style="color:#10B981">Sur l'écran d'accueil</span></div>
              <div style="font-size:11px;color:#94A3B8;margin-top:2px">dans le menu qui s'affiche</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:12px">
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
          cursor:pointer;font-family:'Inter',sans-serif;margin-top:16px;
        ">Compris !</button>
      </div>
    `;

    document.body.appendChild(guide);
    function removeGuide() { guide.remove(); }
    document.getElementById('pwa-ios-close').addEventListener('click', removeGuide);
    document.getElementById('pwa-ios-gotit').addEventListener('click', removeGuide);
  }

  /* ==========================================================
     PUSH NOTIFICATIONS — LOGS DÉTAILLÉS
     ========================================================== */

  /**
   * Configure le système Push (appelé après l'enregistrement du SW).
   * Vérifie les permissions, puis tente la subscription.
   */
  function setupPushNotifications(registration) {
    if (_pushSetupDone) {
      console.log(LOG_PREFIX, TAG, '⏩ setupPushNotifications déjà fait — ignoré');
      return;
    }

    console.log(LOG_PREFIX, TAG, '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log(LOG_PREFIX, TAG, '2️⃣  Début configuration Push...');
    console.log(LOG_PREFIX, TAG, '   registration présente:', !!registration);
    console.log(LOG_PREFIX, TAG, '   pushManager:', registration ? !!registration.pushManager : 'N/A');
    console.log(LOG_PREFIX, TAG, '   Notification API supportée:', 'Notification' in window);
    console.log(LOG_PREFIX, TAG, '   PushManager API supportée:', 'PushManager' in window);
    console.log(LOG_PREFIX, TAG, '   Permission actuelle:', Notification.permission);

    _pushRegistration = registration;
    _pushSetupDone = true;

    // Vérifier si les notifications sont supportées
    if (!('Notification' in window) || !('PushManager' in window)) {
      console.warn(LOG_PREFIX, TAG, '❌ Push API non supportée — abandon');
      return;
    }

    // Étape 1 : Si déjà accordée → subscribe immédiatement
    if (Notification.permission === 'granted') {
      console.log(LOG_PREFIX, TAG, '✅ Permission déjà accordée → subscribe immédiat');
      subscribeToPushWithLogs(registration);
      return;
    }

    // Étape 2 : Si refusée → ne rien faire
    if (Notification.permission === 'denied') {
      console.warn(LOG_PREFIX, TAG, '🚫 Permission refusée — abandon');
      return;
    }

    // Étape 3 : Permission "default" → afficher une bannière explicite
    //            (pas de handler click fragile sur le document !)
    console.log(LOG_PREFIX, TAG, '⏳ Permission "default" → bannière visible après 3 secondes...');
    setTimeout(() => showPushPermissionBanner(registration), 3000);
  }

  /**
   * Affiche une bannière/bouton explicite pour demander la permission
   * de notification. S'affiche uniquement sur les pages authentifiées.
   */
  function showPushPermissionBanner(registration) {
    // Ne pas afficher si déjà en cours ou si permission déjà accordée/refusée
    if (sessionStorage.getItem('push_banner_shown')) {
      console.log(LOG_PREFIX, TAG, '⏩ Bannière déjà montrée cette session');
      return;
    }
    if (Notification.permission !== 'default') {
      console.log(LOG_PREFIX, TAG, '⏩ Permission déjà ' + Notification.permission + ' — pas de bannière');
      return;
    }
    // Vérifier qu'on est sur une page authentifiée
    const isAuthPage = document.querySelector('.topbar-profile') !== null
                    || document.querySelector('.sidebar') !== null
                    || document.querySelector('.balance-card') !== null
                    || document.querySelector('.mobile-bottom-nav') !== null;
    if (!isAuthPage) {
      console.log(LOG_PREFIX, TAG, '⏩ Page non authentifiée — bannière différée');
      return;
    }

    console.log(LOG_PREFIX, TAG, '📢 Affichage bannière "Activer les notifications"...');
    sessionStorage.setItem('push_banner_shown', '1');

    const banner = document.createElement('div');
    banner.id = 'push-permission-banner';
    banner.innerHTML = `
      <div style="
        position:fixed;bottom:90px;left:50%;transform:translateX(-50%);z-index:99998;
        background:linear-gradient(135deg,#1E3A8A,#2563EB);color:#fff;
        padding:16px 24px;border-radius:18px;
        font-family:'Inter',sans-serif;font-size:14px;font-weight:600;
        display:flex;align-items:center;gap:14px;
        box-shadow:0 16px 48px rgba(37,99,235,.4);
        animation:pushSlideUp 0.5s ease;max-width:92vw;flex-wrap:wrap;justify-content:center;
      ">
        <span><i class="fa-solid fa-bell" style="margin-right:8px"></i>Activer les notifications</span>
        <span style="font-weight:400;font-size:12px;opacity:.85">Restez informé de vos transferts</span>
        <button id="push-allow-btn" style="
          padding:10px 20px;background:#fff;color:#2563EB;
          border:none;border-radius:10px;font-weight:700;font-size:13px;
          cursor:pointer;font-family:'Inter',sans-serif;transition:all 0.2s;
          white-space:nowrap;
        ">Activer</button>
        <button id="push-dismiss-btn" style="
          background:none;border:none;color:rgba(255,255,255,.7);
          cursor:pointer;font-size:18px;padding:4px;
        "><i class="fa-solid fa-xmark"></i></button>
      </div>
      <style>
        @keyframes pushSlideUp{from{opacity:0;transform:translateX(-50%) translateY(40px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}
      </style>
    `;

    document.body.appendChild(banner);

    document.getElementById('push-allow-btn').addEventListener('click', () => {
      console.log(LOG_PREFIX, TAG, '🖱️  Bouton "Activer" cliqué — demande de permission...');
      banner.remove();

      Notification.requestPermission().then(permission => {
        console.log(LOG_PREFIX, TAG, '📋 Résultat permission:', permission);

        if (permission === 'granted') {
          console.log(LOG_PREFIX, TAG, '✅ Permission accordée — lancement subscribe...');
          subscribeToPushWithLogs(_pushRegistration || registration);
        } else if (permission === 'denied') {
          console.warn(LOG_PREFIX, TAG, '🚫 Permission refusée par l\'utilisateur');
        } else {
          console.log(LOG_PREFIX, TAG, '⏸️  Permission "default" — utilisateur a ignoré (fermé la popup)');
        }
      });
    });

    document.getElementById('push-dismiss-btn').addEventListener('click', () => {
      console.log(LOG_PREFIX, TAG, '❌ Bannière fermée par l\'utilisateur');
      banner.remove();
    });
  }

  /**
   * Flux complet d'abonnement Push avec logs détaillés.
   * Appelé UNIQUEMENT après que Notification.permission === 'granted'.
   */
  async function subscribeToPushWithLogs(registration) {
    console.log(LOG_PREFIX, TAG, '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log(LOG_PREFIX, TAG, '3️⃣  Début subscribeToPushWithLogs...');

    if (!registration) {
      console.error(LOG_PREFIX, TAG, '❌ Aucune registration SW — impossible de subscribe');
      return { success: false, error: 'no_registration' };
    }

    // ============ Étape 3a : Récupérer la clé VAPID publique ============
    console.log(LOG_PREFIX, TAG, '3a. Récupération clé VAPID publique depuis /api/push/vapid-public-key...');
    let vapidPublicKey = null;

    try {
      const keyResp = await fetch('/api/push/vapid-public-key');
      console.log(LOG_PREFIX, TAG, '   Réponse HTTP:', keyResp.status, keyResp.statusText);

      if (keyResp.ok) {
        const keyData = await keyResp.json();
        console.log(LOG_PREFIX, TAG, '   Réponse JSON:', JSON.stringify(keyData));
        vapidPublicKey = keyData.public_key || null;

        if (vapidPublicKey) {
          console.log(LOG_PREFIX, TAG, '✅ Clé VAPID reçue — longueur:', vapidPublicKey.length, 'caractères');
        } else {
          console.warn(LOG_PREFIX, TAG, '⚠️  Clé VAPID vide dans la réponse');
        }
      } else {
        console.error(LOG_PREFIX, TAG, `❌ Erreur HTTP ${keyResp.status} lors de la récupération VAPID`);
        const body = await keyResp.text().catch(() => '');
        console.error(LOG_PREFIX, TAG, '   Corps réponse:', body.substring(0, 200));
      }
    } catch (e) {
      console.error(LOG_PREFIX, TAG, '❌ Exception lors de la récupération VAPID:', e.message);
    }

    // ============ Étape 3b : Convertir la clé VAPID en Uint8Array ============
    console.log(LOG_PREFIX, TAG, '3b. Préparation de applicationServerKey...');
    const subscribeOptions = { userVisibleOnly: true };

    if (vapidPublicKey) {
      try {
        subscribeOptions.applicationServerKey = urlBase64ToUint8Array(vapidPublicKey);
        console.log(LOG_PREFIX, TAG, '✅ applicationServerKey convertie — longueur:', subscribeOptions.applicationServerKey.length, 'octets');
      } catch (e) {
        console.error(LOG_PREFIX, TAG, '❌ Erreur conversion clé VAPID:', e.message);
      }
    } else {
      console.warn(LOG_PREFIX, TAG, '⚠️  Aucune clé VAPID — subscription sans applicationServerKey (peut échouer)');
    }

    // ============ Étape 3c : Subscription pushManager ============
    console.log(LOG_PREFIX, TAG, '3c. Subscription pushManager...');
    let subscription = null;

    try {
      // Vérifier d'abord si une subscription existe déjà
      subscription = await registration.pushManager.getSubscription();
      console.log(LOG_PREFIX, TAG, '   getSubscription():', subscription ? 'trouvée' : 'aucune');

      if (!subscription) {
        console.log(LOG_PREFIX, TAG, '   Appel pushManager.subscribe()...');
        subscription = await registration.pushManager.subscribe(subscribeOptions);
        console.log(LOG_PREFIX, TAG, '✅ Subscription créée avec succès');
      } else {
        console.log(LOG_PREFIX, TAG, '✅ Subscription déjà existante — réutilisée');
      }
    } catch (err) {
      console.error(LOG_PREFIX, TAG, '❌ Échec pushManager.subscribe():', err.message);
      console.error(LOG_PREFIX, TAG, '   Stack:', err.stack);
      return { success: false, error: 'subscribe_failed: ' + err.message };
    }

    // ============ Étape 3d : Valider la subscription ============
    console.log(LOG_PREFIX, TAG, '3d. Validation subscription...');
    const subJson = subscription.toJSON();
    console.log(LOG_PREFIX, TAG, '   endpoint:', subJson.endpoint.substring(0, 80) + '...');
    console.log(LOG_PREFIX, TAG, '   keys.p256dh présent:', !!subJson.keys?.p256dh);
    console.log(LOG_PREFIX, TAG, '   keys.auth présent:', !!subJson.keys?.auth);

    if (!subJson.endpoint || !subJson.keys?.p256dh || !subJson.keys?.auth) {
      console.error(LOG_PREFIX, TAG, '❌ Subscription incomplète — abandon');
      console.error(LOG_PREFIX, TAG, '   Données:', JSON.stringify(subJson));
      return { success: false, error: 'incomplete_subscription' };
    }

    console.log(LOG_PREFIX, TAG, '✅ Subscription valide — sauvegarde locale...');
    localStorage.setItem(PUSH_SUB_STORAGE_KEY, JSON.stringify(subJson));
    console.log(LOG_PREFIX, TAG, '   Sauvegardée dans localStorage:', PUSH_SUB_STORAGE_KEY);

    // ============ Étape 3e : Envoyer au backend ============
    console.log(LOG_PREFIX, TAG, '3e. Envoi subscription au backend POST /api/push/subscribe...');
    return await sendSubscriptionToServer(subJson);
  }

  /**
   * Envoie la subscription au backend /api/push/subscribe.
   * Gère 200, 302 (redirect=login), 401, 403, 400, 500, erreur réseau.
   */
  async function sendSubscriptionToServer(subJson) {
    try {
      console.log(LOG_PREFIX, TAG, '   ➡️  POST /api/push/subscribe');
      console.log(LOG_PREFIX, TAG, '      Body: { subscription: { endpoint: "...", keys: {...} } }');

      const response = await fetch('/api/push/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin', // Envoyer les cookies de session
        body: JSON.stringify({ subscription: subJson }),
      });

      console.log(LOG_PREFIX, TAG, '   ⬅️  Réponse HTTP:', response.status, response.statusText);
      console.log(LOG_PREFIX, TAG, '      Content-Type:', response.headers.get('content-type'));

      // ── Gérer le cas 302 (redirect → page login) ──
      // fetch suit les redirects automatiquement, donc si on a un 200
      // avec une réponse HTML, c'est probablement la page login
      const contentType = response.headers.get('content-type') || '';

      if (response.status === 200 && contentType.includes('text/html')) {
        console.warn(LOG_PREFIX, TAG, '⚠️  Réponse HTML reçue → probablement redirigé vers login');
        console.log(LOG_PREFIX, TAG, '   Utilisateur non authentifié — mise en attente');
        localStorage.setItem(PUSH_PENDING_KEY, '1');
        return { success: false, pending: true, reason: 'redirected_to_login' };
      }

      // ── Gérer 401 / 403 ──
      if (response.status === 401 || response.status === 403) {
        console.warn(LOG_PREFIX, TAG, `⚠️  HTTP ${response.status} — utilisateur non authentifié`);
        localStorage.setItem(PUSH_PENDING_KEY, '1');
        return { success: false, pending: true, reason: 'http_' + response.status };
      }

      // ── Gérer erreurs ──
      if (!response.ok) {
        console.error(LOG_PREFIX, TAG, `❌ HTTP ${response.status} — échec enregistrement`);
        const errorBody = await response.text().catch(() => '');
        console.error(LOG_PREFIX, TAG, '   Corps erreur:', errorBody.substring(0, 300));
        localStorage.setItem(PUSH_PENDING_KEY, '1');
        return { success: false, error: `http_${response.status}: ${errorBody.substring(0, 100)}` };
      }

      // ── Succès ──
      const result = await response.json();
      console.log(LOG_PREFIX, TAG, '   Réponse JSON:', JSON.stringify(result));

      if (result.success) {
        console.log(LOG_PREFIX, TAG, '✅ Abonnement enregistré sur le serveur !');
        console.log(LOG_PREFIX, TAG, '   subscription_id:', result.subscription_id || result.subscription_id || 'N/A');
        console.log(LOG_PREFIX, TAG, '   created:', result.created || false);
        console.log(LOG_PREFIX, TAG, '   updated:', result.updated || false);
        localStorage.removeItem(PUSH_PENDING_KEY);
        console.log(LOG_PREFIX, TAG, '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.log(LOG_PREFIX, TAG, '🎉 SYSTÈME PUSH OPÉRATIONNEL !');
        return { success: true };
      } else {
        console.warn(LOG_PREFIX, TAG, '❌ Serveur a répondu success=false');
        console.warn(LOG_PREFIX, TAG, '   Erreur:', result.error || result.message || 'inconnue');
        localStorage.setItem(PUSH_PENDING_KEY, '1');
        return { success: false, error: result.error || result.message };
      }
    } catch (fetchErr) {
      console.error(LOG_PREFIX, TAG, '❌ Erreur réseau/fetch:', fetchErr.message);
      console.error(LOG_PREFIX, TAG, '   Stack:', fetchErr.stack);
      localStorage.setItem(PUSH_PENDING_KEY, '1');
      return { success: false, error: 'network: ' + fetchErr.message };
    }
  }

  /* ==========================================================
     SYNC — Enregistrer un abonnement en attente dans le backend
     Verrou _pushSyncing pour éviter les appels simultanés.
     ========================================================== */
  async function syncPushSubscription() {
    // ── Verrou : éviter deux synchronisations concurrentes ──
    if (_pushSyncing) {
      console.log(LOG_PREFIX, TAG, '⏩ Sync déjà en cours — ignoré');
      return { success: false, reason: 'already_syncing' };
    }

    const pending = localStorage.getItem(PUSH_PENDING_KEY);
    if (!pending) {
      console.log(LOG_PREFIX, TAG, '⏩ Aucun flag PUSH_PENDING — rien à synchroniser');
      return { success: false, reason: 'no_pending_flag' };
    }

    const subRaw = localStorage.getItem(PUSH_SUB_STORAGE_KEY);
    if (!subRaw) {
      console.log(LOG_PREFIX, TAG, '⚠️  Flag pending présent mais aucune subscription — nettoyage');
      localStorage.removeItem(PUSH_PENDING_KEY);
      return { success: false, reason: 'no_subscription' };
    }

    if (Notification.permission !== 'granted') {
      console.log(LOG_PREFIX, TAG, '🚫 Permission révoquée — nettoyage localStorage');
      localStorage.removeItem(PUSH_SUB_STORAGE_KEY);
      localStorage.removeItem(PUSH_PENDING_KEY);
      return { success: false, reason: 'permission_denied' };
    }

    _pushSyncing = true;
    console.log(LOG_PREFIX, TAG, '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log(LOG_PREFIX, TAG, '🔁 Sync Push démarrée (pending =', pending, ')');

    try {
      let subJson;
      try {
        subJson = JSON.parse(subRaw);
      } catch (e) {
        console.error(LOG_PREFIX, TAG, '❌ Subscription JSON corrompu — suppression');
        localStorage.removeItem(PUSH_SUB_STORAGE_KEY);
        localStorage.removeItem(PUSH_PENDING_KEY);
        _pushSyncing = false;
        return { success: false, reason: 'corrupted_json' };
      }

      console.log(LOG_PREFIX, TAG, '📤 Envoi subscription au serveur...');
      const result = await sendSubscriptionToServer(subJson);

      if (result.success) {
        // Succès : nettoyage complet
        console.log(LOG_PREFIX, TAG, '✅ Sync Push réussie !');
        localStorage.removeItem(PUSH_PENDING_KEY);
        // On conserve la subscription dans localStorage pour les synchros futures
        console.log(LOG_PREFIX, TAG, '   Flag PUSH_PENDING supprimé');
      } else if (result.pending) {
        console.log(LOG_PREFIX, TAG, '⏳ Sync repoussée —', result.reason || 'non authentifié');
      } else {
        console.log(LOG_PREFIX, TAG, '❌ Sync échouée —', result.error || result.reason || 'inconnue');
      }

      _pushSyncing = false;
      return result;
    } catch (err) {
      console.error(LOG_PREFIX, TAG, '❌ Exception syncPushSubscription:', err.message);
      _pushSyncing = false;
      return { success: false, error: 'exception: ' + err.message };
    }
  }

  /**
   * Vérifie si on est sur une page authentifiée.
   */
  function _isAuthPage() {
    return document.querySelector('.topbar-profile') !== null
        || document.querySelector('.sidebar') !== null
        || document.querySelector('.balance-card') !== null
        || document.querySelector('.mobile-bottom-nav') !== null;
  }

  /**
   * Tente une synchronisation push si un abonnement est en attente.
   * Appelée sur chaque chargement de page authentifiée.
   * Si l'utilisateur vient de se connecter (flag sessionStorage),
   * la sync est déclenchée immédiatement avec un délai réduit.
   */
  function autoSyncOnAuthPages() {
    if (!_isAuthPage()) {
      console.log(LOG_PREFIX, TAG, '⏸️  Page non authentifiée — sync différée');
      return;
    }
    if (!localStorage.getItem(PUSH_PENDING_KEY)) {
      console.log(LOG_PREFIX, TAG, '⏩ Aucun abonnement en attente');
      return;
    }

    // ── L'utilisateur vient de se connecter → sync immédiate ──
    const justLoggedIn = sessionStorage.getItem('transafrik_just_logged_in');
    if (justLoggedIn) {
      sessionStorage.removeItem('transafrik_just_logged_in');
      console.log(LOG_PREFIX, TAG, '🔑 Flag just_logged_in détecté → sync immédiate');
      setTimeout(() => {
        syncPushSubscription().catch(err => {
          console.error(LOG_PREFIX, TAG, '❌ autoSyncOnAuthPages (just_logged_in) a échoué:', err.message);
        });
      }, 800);
      return;
    }

    // ── Chargement normal d'une page authentifiée ──
    console.log(LOG_PREFIX, TAG, '✅ Page authentifiée détectée → syncPushSubscription()');
    setTimeout(() => {
      syncPushSubscription().catch(err => {
        console.error(LOG_PREFIX, TAG, '❌ autoSyncOnAuthPages a échoué:', err.message);
      });
    }, 2000);
  }

  /**
   * Écouteur global qui tente une sync push quand l'utilisateur
   * revient sur la page (focus/visibilitychange).
   * Utile après une connexion ou un changement de permission.
   */
  function setupPushSyncListeners() {
    // ── Focus : utilisateur revient sur l'onglet ──
    window.addEventListener('focus', () => {
      if (!localStorage.getItem(PUSH_PENDING_KEY)) return;
      if (!_isAuthPage()) return;
      console.log(LOG_PREFIX, TAG, '👁️  Fenêtre focus → vérification sync push');
      // Délai court pour laisser la session se stabiliser
      setTimeout(() => {
        syncPushSubscription().catch(err => {
          console.error(LOG_PREFIX, TAG, '❌ Sync sur focus a échoué:', err.message);
        });
      }, 1500);
    });

    // ── Visibility change : page redevient visible ──
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) return;
      if (!localStorage.getItem(PUSH_PENDING_KEY)) return;
      if (!_isAuthPage()) return;
      console.log(LOG_PREFIX, TAG, '👁️  Page redevenue visible → vérification sync push');
      setTimeout(() => {
        syncPushSubscription().catch(err => {
          console.error(LOG_PREFIX, TAG, '❌ Sync sur visibilitychange a échoué:', err.message);
        });
      }, 1500);
    });

    console.log(LOG_PREFIX, TAG, '👂 Écouteurs focus/visibilitychange actifs');
  }

  /**
   * Appel explicite après une connexion réussie.
   * Fonction exposée pour être appelée depuis le code de login (par ex. dashboard.html).
   */
  function onLoginSuccess() {
    console.log(LOG_PREFIX, TAG, '🔑 Login détecté → tentative sync immédiate');
    if (!localStorage.getItem(PUSH_PENDING_KEY)) {
      console.log(LOG_PREFIX, TAG, '⏩ Aucun abonnement en attente après login');
      return;
    }
    // Petit délai pour que les cookies de session soient bien en place
    setTimeout(() => {
      syncPushSubscription().catch(err => {
        console.error(LOG_PREFIX, TAG, '❌ onLoginSuccess sync a échoué:', err.message);
      });
    }, 1500);
  }

  /* ==========================================================
     urlBase64ToUint8Array — conversion clé VAPID
     ========================================================== */
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
      console.log(LOG_PREFIX, '🌐 Connexion rétablie');
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
      console.log(LOG_PREFIX, '📴 Hors connexion');
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
        console.log(LOG_PREFIX, '🚪 Déconnexion détectée — nettoyage');
        if (navigator.serviceWorker && navigator.serviceWorker.controller) {
          navigator.serviceWorker.controller.postMessage('CLEAR_ALL_CACHES');
        }
        localStorage.removeItem('transafrik_balance');
        sessionStorage.clear();
        // Ne PAS supprimer push_sub — il sera resynchronisé après reconnexion
      }
    });
  }

  /* ==========================================================
     INIT
     ========================================================== */
  document.addEventListener('DOMContentLoaded', () => {
    console.log(LOG_PREFIX, '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log(LOG_PREFIX, '🚀 INIT PWA v2.0.0 — DOMContentLoaded');
    console.log(LOG_PREFIX, '   URL:', window.location.href);
    console.log(LOG_PREFIX, '   serviceWorker support:', 'serviceWorker' in navigator);
    console.log(LOG_PREFIX, '   Notification support:', 'Notification' in window);
    console.log(LOG_PREFIX, '   PushManager support:', 'PushManager' in window);
    console.log(LOG_PREFIX, '   standalone (PWA installée):', 'standalone' in navigator ? navigator.standalone : 'N/A');

    registerSW();
    setupInstallBanner();
    setupNetworkDetection();
    setupLogoutCleanup();
    setupPushSyncListeners();

    // Tenter de synchroniser un abonnement push en attente
    autoSyncOnAuthPages();

    console.log(LOG_PREFIX, '✅ Module PWA initialisé');
  });

  // ============================================================
  //  API GLOBALE — accessible via window.TransAfrik
  // ============================================================
  window.TransAfrik = window.TransAfrik || {};
  window.TransAfrik.syncPushSubscription = syncPushSubscription;
  window.TransAfrik.subscribeToPush = subscribeToPushWithLogs;
  window.TransAfrik.waitForSWReady = waitForSWReady;
  window.TransAfrik.onLoginSuccess = onLoginSuccess;

  console.log(LOG_PREFIX, '📦 API globale TransAfrik.* exposée');
})();
