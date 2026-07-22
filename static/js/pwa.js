/* ============================================================
   TransAfrik PWA — v2.1.0
   Gère : Installation, iOS, Mise à jour, Push Notifications
   TRACAGE EXHAUSTIF — chaque étape loggée, try/catch partout
   ============================================================ */

(function () {
  'use strict';

  const LOG = '[PWA]';
  const PTAG = 'PUSH';

  const PUSH_SUB_KEY = 'transafrik_push_sub';
  const PUSH_PENDING_KEY = 'transafrik_push_pending';

  // ── TRACE INITIALE ──
  console.log(LOG, '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(LOG, 'CHARGEMENT — PWA v2.1.0 — IIFE démarre');
  console.log(LOG, '  URL            :', window.location.href);
  console.log(LOG, '  serviceWorker  :', 'serviceWorker' in navigator);
  console.log(LOG, '  Notification   :', 'Notification' in window);
  console.log(LOG, '  PushManager    :', 'PushManager' in window);
  console.log(LOG, '  standalone     :', 'standalone' in navigator ? navigator.standalone : 'N/A');
  console.log(LOG, '  userAgent      :', navigator.userAgent.substring(0, 100));
  console.log(LOG, '  online         :', navigator.onLine);

  let _swRegistration = null;
  let _pushSetupDone = false;
  let _pushSyncing = false;

  // ══════════════════════════════════════════════════════════
  //  SERVICE WORKER REGISTRATION
  // ══════════════════════════════════════════════════════════
  function registerSW() {
    console.log(LOG, 'SW', '1. registerSW() appelé');

    if (!('serviceWorker' in navigator)) {
      console.warn(LOG, 'SW', 'ABANDON — serviceWorker non supporté');
      return;
    }

    console.log(LOG, 'SW', '  Appel navigator.serviceWorker.register("/sw.js")...');
    try {
      navigator.serviceWorker.register('/sw.js', { scope: '/' })
        .then(reg => {
          console.log(LOG, 'SW', '✅ Service Worker ENREGISTRÉ');
          console.log(LOG, 'SW', '  scope         :', reg.scope);
          console.log(LOG, 'SW', '  active        :', !!reg.active);
          console.log(LOG, 'SW', '  installing    :', !!reg.installing);
          console.log(LOG, 'SW', '  waiting       :', !!reg.waiting);

          _swRegistration = reg;

          // Mise à jour
          if (reg.waiting) {
            console.log(LOG, 'SW', '  → SW en attente détecté');
            handleUpdate(reg);
          }
          reg.addEventListener('updatefound', () => {
            console.log(LOG, 'SW', '  → updatefound');
            const nw = reg.installing;
            if (nw) {
              nw.addEventListener('statechange', () => {
                console.log(LOG, 'SW', '  → nouveau SW state:', nw.state);
                if (nw.state === 'installed' && navigator.serviceWorker.controller) {
                  handleUpdate(reg);
                }
              });
            }
          });

          navigator.serviceWorker.addEventListener('controllerchange', () => {
            console.log(LOG, 'SW', '  → controllerchange — rechargement');
            window.location.reload();
          });

          setInterval(() => { reg.update().catch(() => {}); }, 30 * 60 * 1000);

          // LANCER LA CONFIG PUSH
          console.log(LOG, 'SW', '  → appel setupPushNotifications(reg)...');
          setupPushNotifications(reg);
        })
        .catch(err => {
          console.error(LOG, 'SW', '❌ register() REJETÉE:', err.message);
          console.error(LOG, 'SW', '  Stack:', err.stack);
        });
    } catch (err) {
      console.error(LOG, 'SW', '❌ EXCEPTION dans registerSW():', err.message);
      console.error(LOG, 'SW', '  Stack:', err.stack);
    }
  }

  // ══════════════════════════════════════════════════════════
  //  CONFIGURATION PUSH NOTIFICATIONS
  // ══════════════════════════════════════════════════════════
  function setupPushNotifications(reg) {
    console.log(LOG, PTAG, '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log(LOG, PTAG, '2. setupPushNotifications() appelé');

    if (_pushSetupDone) {
      console.log(LOG, PTAG, '  IGNORÉ — déjà fait');
      return;
    }
    _pushSetupDone = true;

    try {
      console.log(LOG, PTAG, '  reg présent       :', !!reg);
      console.log(LOG, PTAG, '  reg.pushManager   :', reg && !!reg.pushManager);
      console.log(LOG, PTAG, '  Notification API  :', 'Notification' in window);
      console.log(LOG, PTAG, '  PushManager API   :', 'PushManager' in window);
      console.log(LOG, PTAG, '  Notification.permission :', 'Notification' in window ? Notification.permission : 'N/A');
    } catch (err) {
      console.error(LOG, PTAG, '❌ Exception lecture permissions:', err.message);
    }

    // Vérifier les APIs
    if (!('Notification' in window)) {
      console.warn(LOG, PTAG, 'ABANDON — Notification API absente');
      return;
    }
    if (!('PushManager' in window)) {
      console.warn(LOG, PTAG, 'ABANDON — PushManager API absente');
      return;
    }

    // Si déjà accordée → subscribe immédiat
    if (Notification.permission === 'granted') {
      console.log(LOG, PTAG, '✅ Permission déjà GRANTED → subscribe immédiat');
      subscribeToPushWithLogs(reg);
      return;
    }

    // Si refusée → rien
    if (Notification.permission === 'denied') {
      console.log(LOG, PTAG, '🚫 Permission DENIED — abandon');
      return;
    }

    // Permission "default" → bannière après 3s
    console.log(LOG, PTAG, '⏳ Permission DEFAULT → bannière dans 3s');
    setTimeout(() => {
      try {
        showPushPermissionBanner(reg);
      } catch (err) {
        console.error(LOG, PTAG, '❌ Exception showPushPermissionBanner:', err.message);
      }
    }, 3000);
  }

  // ══════════════════════════════════════════════════════════
  //  BANNIÈRE PERMISSION
  // ══════════════════════════════════════════════════════════
  function showPushPermissionBanner(reg) {
    console.log(LOG, PTAG, '3. showPushPermissionBanner()');

    try {
      if (sessionStorage.getItem('push_banner_shown')) {
        console.log(LOG, PTAG, '  IGNORÉ — déjà montrée cette session');
        return;
      }
      if (Notification.permission !== 'default') {
        console.log(LOG, PTAG, '  IGNORÉ — permission =', Notification.permission);
        return;
      }
      const isAuth = document.querySelector('.topbar-profile') !== null
                  || document.querySelector('.sidebar') !== null
                  || document.querySelector('.balance-card') !== null
                  || document.querySelector('.mobile-bottom-nav') !== null;
      if (!isAuth) {
        console.log(LOG, PTAG, '  IGNORÉ — page non authentifiée');
        return;
      }

      console.log(LOG, PTAG, '  → Affichage bannière');
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
            cursor:pointer;font-family:'Inter',sans-serif;white-space:nowrap;
          ">Activer</button>
          <button id="push-dismiss-btn" style="
            background:none;border:none;color:rgba(255,255,255,.7);
            cursor:pointer;font-size:18px;padding:4px;
          "><i class="fa-solid fa-xmark"></i></button>
        </div>
        <style>@keyframes pushSlideUp{from{opacity:0;transform:translateX(-50%) translateY(40px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}</style>
      `;
      document.body.appendChild(banner);

      document.getElementById('push-allow-btn').addEventListener('click', () => {
        console.log(LOG, PTAG, '  → Bouton "Activer" cliqué');
        banner.remove();
        try {
          Notification.requestPermission().then(perm => {
            console.log(LOG, PTAG, '  → Notification.requestPermission() retourne:', perm);
            if (perm === 'granted') {
              console.log(LOG, PTAG, '  → Permission GRANTED → subscribe...');
              subscribeToPushWithLogs(_swRegistration || reg);
            } else if (perm === 'denied') {
              console.warn(LOG, PTAG, '  → Permission DENIED');
            } else {
              console.log(LOG, PTAG, '  → Permission DEFAULT (ignoré)');
            }
          }).catch(err => {
            console.error(LOG, PTAG, '❌ requestPermission() REJETÉE:', err.message);
          });
        } catch (err) {
          console.error(LOG, PTAG, '❌ Exception dans click handler:', err.message);
        }
      });

      document.getElementById('push-dismiss-btn').addEventListener('click', () => {
        console.log(LOG, PTAG, '  → Bannière fermée');
        banner.remove();
      });
    } catch (err) {
      console.error(LOG, PTAG, '❌ Exception showPushPermissionBanner:', err.message);
      console.error(LOG, PTAG, '  Stack:', err.stack);
    }
  }

  // ══════════════════════════════════════════════════════════
  //  SUBSCRIPTION PUSH — ÉTAPE PAR ÉTAPE AVEC TRY/CATCH
  // ══════════════════════════════════════════════════════════
  async function subscribeToPushWithLogs(reg) {
    console.log(LOG, PTAG, '══════════════════════════════════════════');
    console.log(LOG, PTAG, '4. subscribeToPushWithLogs() DÉMARRAGE');

    // ─── Étape 4.0 : Validation registration ───
    try {
      console.log(LOG, PTAG, '4.0 Validation registration...');
      console.log(LOG, PTAG, '  reg argument :', !!reg);
      if (reg) {
        console.log(LOG, PTAG, '  reg.scope    :', reg.scope);
        console.log(LOG, PTAG, '  reg.pushManager :', !!reg.pushManager);
        console.log(LOG, PTAG, '  reg.active   :', !!reg.active);
      }

      if (!reg) {
        console.error(LOG, PTAG, 'ABANDON — reg est null/undefined');
        return { success: false, error: 'no_registration' };
      }

      if (!reg.pushManager) {
        console.error(LOG, PTAG, 'ABANDON — reg.pushManager est null/undefined');
        console.error(LOG, PTAG, '  reg keys:', Object.keys(reg));
        return { success: false, error: 'no_pushManager' };
      }
    } catch (err) {
      console.error(LOG, PTAG, '❌ Exception étape 4.0:', err.message);
      console.error(LOG, PTAG, '  Stack:', err.stack);
      return { success: false, error: 'exception_4.0: ' + err.message };
    }

    // ─── Étape 4.1 : Récupérer clé VAPID ───
    let vapidPublicKey = null;
    try {
      console.log(LOG, PTAG, '4.1 Récupération clé VAPID...');
      console.log(LOG, PTAG, '  GET /api/push/vapid-public-key');
      const keyResp = await fetch('/api/push/vapid-public-key');
      console.log(LOG, PTAG, '  ← HTTP', keyResp.status, keyResp.statusText);

      if (keyResp.ok) {
        const keyData = await keyResp.json();
        console.log(LOG, PTAG, '  Corps JSON:', JSON.stringify(keyData));
        vapidPublicKey = keyData.public_key || null;
        console.log(LOG, PTAG, '  Clé VAPID :', vapidPublicKey ? vapidPublicKey.substring(0, 30) + '...' : 'NULL');
      } else {
        console.error(LOG, PTAG, '  ERREUR HTTP', keyResp.status);
        const body = await keyResp.text().catch(() => '');
        console.error(LOG, PTAG, '  Corps:', body.substring(0, 200));
      }
    } catch (err) {
      console.error(LOG, PTAG, '❌ Exception étape 4.1 (VAPID):', err.message);
      console.error(LOG, PTAG, '  Stack:', err.stack);
      // On continue sans clé VAPID (peut échouer plus tard)
    }

    // ─── Étape 4.2 : Préparer applicationServerKey ───
    const subscribeOptions = { userVisibleOnly: true };
    try {
      console.log(LOG, PTAG, '4.2 Préparation applicationServerKey...');
      if (vapidPublicKey) {
        subscribeOptions.applicationServerKey = urlBase64ToUint8Array(vapidPublicKey);
        console.log(LOG, PTAG, '  applicationServerKey convertie,', subscribeOptions.applicationServerKey.length, 'octets');
      } else {
        console.warn(LOG, PTAG, '  PAS de clé VAPID — risque d\'échec');
      }
    } catch (err) {
      console.error(LOG, PTAG, '❌ Exception étape 4.2 (conversion clé):', err.message);
      console.error(LOG, PTAG, '  Stack:', err.stack);
      // On continue, la conversion a pu échouer
    }

    // ─── Étape 4.3 : Subscription via pushManager ───
    let subscription = null;
    try {
      console.log(LOG, PTAG, '4.3 pushManager.subscribe()...');
      console.log(LOG, PTAG, '  options:', JSON.stringify({ userVisibleOnly: subscribeOptions.userVisibleOnly, applicationServerKey: !!subscribeOptions.applicationServerKey }));

      // Vérifier d'abord une subscription existante
      try {
        subscription = await reg.pushManager.getSubscription();
        console.log(LOG, PTAG, '  getSubscription() →', subscription ? 'TROUVÉE' : 'AUCUNE');
        if (subscription) {
          console.log(LOG, PTAG, '  endpoint:', subscription.endpoint ? subscription.endpoint.substring(0, 80) + '...' : 'NULL');
        }
      } catch (err) {
        console.error(LOG, PTAG, '❌ Exception getSubscription():', err.message);
        console.error(LOG, PTAG, '  Stack:', err.stack);
      }

      if (!subscription) {
        console.log(LOG, PTAG, '  → Appel reg.pushManager.subscribe(options)...');
        subscription = await reg.pushManager.subscribe(subscribeOptions);
        console.log(LOG, PTAG, '✅ subscribe() RÉUSSI');
      } else {
        console.log(LOG, PTAG, '✅ Subscription EXISTANTE réutilisée');
      }
    } catch (err) {
      console.error(LOG, PTAG, '❌ Exception étape 4.3 (subscribe):', err.message);
      console.error(LOG, PTAG, '  name   :', err.name);
      console.error(LOG, PTAG, '  Stack  :', err.stack);
      return { success: false, error: 'subscribe_failed: ' + err.message };
    }

    // ─── Étape 4.4 : Valider la subscription ───
    let subJson;
    try {
      console.log(LOG, PTAG, '4.4 Validation subscription...');
      subJson = subscription.toJSON();
      console.log(LOG, PTAG, '  subscription.toJSON() OK');
      console.log(LOG, PTAG, '  endpoint  :', subJson.endpoint ? subJson.endpoint.substring(0, 80) + '...' : 'NULL');
      console.log(LOG, PTAG, '  keys.p256dh :', !!subJson.keys?.p256dh);
      console.log(LOG, PTAG, '  keys.auth   :', !!subJson.keys?.auth);

      if (!subJson.endpoint || !subJson.keys?.p256dh || !subJson.keys?.auth) {
        console.error(LOG, PTAG, 'ABANDON — Subscription incomplète');
        console.error(LOG, PTAG, '  Données:', JSON.stringify(subJson));
        return { success: false, error: 'incomplete_subscription' };
      }

      console.log(LOG, PTAG, '✅ Subscription VALIDE');
    } catch (err) {
      console.error(LOG, PTAG, '❌ Exception étape 4.4 (validation):', err.message);
      return { success: false, error: 'validation_failed: ' + err.message };
    }

    // ─── Étape 4.5 : Sauvegarde locale ───
    try {
      console.log(LOG, PTAG, '4.5 Sauvegarde dans localStorage...');
      localStorage.setItem(PUSH_SUB_KEY, JSON.stringify(subJson));
      console.log(LOG, PTAG, '  Clé:', PUSH_SUB_KEY);
      console.log(LOG, PTAG, '  Taille:', JSON.stringify(subJson).length, 'caractères');
      console.log(LOG, PTAG, '✅ Sauvegarde locale OK');
    } catch (err) {
      console.error(LOG, PTAG, '❌ Exception étape 4.5 (localStorage):', err.message);
    }

    // ─── Étape 4.6 : Envoi au serveur ───
    console.log(LOG, PTAG, '4.6 Envoi au serveur → sendSubscriptionToServer()');
    try {
      const result = await sendSubscriptionToServer(subJson);
      console.log(LOG, PTAG, '  ← sendSubscriptionToServer retourne:', JSON.stringify(result));
      return result;
    } catch (err) {
      console.error(LOG, PTAG, '❌ Exception étape 4.6 (sendSubscriptionToServer):', err.message);
      console.error(LOG, PTAG, '  Stack:', err.stack);
      return { success: false, error: 'send_failed: ' + err.message };
    }
  }

  // ══════════════════════════════════════════════════════════
  //  ENVOI AU SERVEUR
  // ══════════════════════════════════════════════════════════
  async function sendSubscriptionToServer(subJson) {
    console.log(LOG, PTAG, '5. sendSubscriptionToServer() DÉMARRAGE');
    console.log(LOG, PTAG, '  endpoint:', subJson.endpoint.substring(0, 80) + '...');

    try {
      console.log(LOG, PTAG, '  → POST /api/push/subscribe');
      console.log(LOG, PTAG, '  → credentials: same-origin');

      const response = await fetch('/api/push/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ subscription: subJson }),
      });

      console.log(LOG, PTAG, '  ← HTTP', response.status, response.statusText);
      console.log(LOG, PTAG, '  ← Content-Type:', response.headers.get('content-type'));

      const contentType = response.headers.get('content-type') || '';

      // Redirection HTML → non authentifié
      if (response.status === 200 && contentType.includes('text/html')) {
        console.warn(LOG, PTAG, '  ⚠️  Réponse HTML → redirigé vers login');
        console.log(LOG, PTAG, '  → Flag PUSH_PENDING=1');
        localStorage.setItem(PUSH_PENDING_KEY, '1');
        return { success: false, pending: true, reason: 'redirected_to_login' };
      }

      // 401 / 403 → non authentifié
      if (response.status === 401 || response.status === 403) {
        console.warn(LOG, PTAG, '  ⚠️  HTTP', response.status, '→ non authentifié');
        console.log(LOG, PTAG, '  → Flag PUSH_PENDING=1');
        localStorage.setItem(PUSH_PENDING_KEY, '1');
        return { success: false, pending: true, reason: 'http_' + response.status };
      }

      // Autres erreurs
      if (!response.ok) {
        console.error(LOG, PTAG, '  ❌ HTTP', response.status);
        const errorBody = await response.text().catch(() => '');
        console.error(LOG, PTAG, '  Corps erreur:', errorBody.substring(0, 300));
        localStorage.setItem(PUSH_PENDING_KEY, '1');
        return { success: false, error: 'http_' + response.status + ': ' + errorBody.substring(0, 100) };
      }

      // Succès
      const result = await response.json();
      console.log(LOG, PTAG, '  ← JSON:', JSON.stringify(result));

      if (result.success) {
        console.log(LOG, PTAG, '✅ ABONNEMENT ENREGISTRÉ SUR LE SERVEUR !');
        console.log(LOG, PTAG, '  subscription_id:', result.subscription_id || 'N/A');
        localStorage.removeItem(PUSH_PENDING_KEY);
        console.log(LOG, PTAG, '  Flag PUSH_PENDING supprimé');
        console.log(LOG, PTAG, '══════════════════════════════════════════');
        console.log(LOG, PTAG, '🎉 SYSTÈME PUSH OPÉRATIONNEL !');
        return { success: true };
      } else {
        console.warn(LOG, PTAG, '  Serveur a répondu success=false');
        console.warn(LOG, PTAG, '  Erreur:', result.error || result.message);
        localStorage.setItem(PUSH_PENDING_KEY, '1');
        return { success: false, error: result.error || result.message };
      }
    } catch (fetchErr) {
      console.error(LOG, PTAG, '❌ Exception réseau:', fetchErr.message);
      console.error(LOG, PTAG, '  name:', fetchErr.name);
      console.error(LOG, PTAG, '  Stack:', fetchErr.stack);
      localStorage.setItem(PUSH_PENDING_KEY, '1');
      return { success: false, error: 'network: ' + fetchErr.message };
    }
  }

  // ══════════════════════════════════════════════════════════
  //  SYNC — resoumettre un abonnement en attente
  // ══════════════════════════════════════════════════════════
  async function syncPushSubscription() {
    console.log(LOG, PTAG, 'SYNC. syncPushSubscription() appelé');

    if (_pushSyncing) {
      console.log(LOG, PTAG, 'SYNC. IGNORÉ — déjà en cours');
      return { success: false, reason: 'already_syncing' };
    }

    const pending = localStorage.getItem(PUSH_PENDING_KEY);
    if (!pending) {
      console.log(LOG, PTAG, 'SYNC. IGNORÉ — pas de flag pending');
      return { success: false, reason: 'no_pending_flag' };
    }

    const subRaw = localStorage.getItem(PUSH_SUB_KEY);
    if (!subRaw) {
      console.log(LOG, PTAG, 'SYNC. Flag pending mais pas de sub → nettoyage');
      localStorage.removeItem(PUSH_PENDING_KEY);
      return { success: false, reason: 'no_subscription' };
    }

    if (Notification.permission !== 'granted') {
      console.log(LOG, PTAG, 'SYNC. Permission révoquée → nettoyage');
      localStorage.removeItem(PUSH_SUB_KEY);
      localStorage.removeItem(PUSH_PENDING_KEY);
      return { success: false, reason: 'permission_denied' };
    }

    _pushSyncing = true;
    console.log(LOG, PTAG, 'SYNC. DÉMARRAGE — pending =', pending);

    try {
      let subJson;
      try {
        subJson = JSON.parse(subRaw);
        console.log(LOG, PTAG, 'SYNC. JSON parsé OK');
      } catch (e) {
        console.error(LOG, PTAG, 'SYNC. JSON CORROMPU → nettoyage');
        localStorage.removeItem(PUSH_SUB_KEY);
        localStorage.removeItem(PUSH_PENDING_KEY);
        _pushSyncing = false;
        return { success: false, reason: 'corrupted_json' };
      }

      console.log(LOG, PTAG, 'SYNC. → sendSubscriptionToServer()...');
      const result = await sendSubscriptionToServer(subJson);

      if (result.success) {
        console.log(LOG, PTAG, 'SYNC. ✅ RÉUSSIE — flag supprimé');
        localStorage.removeItem(PUSH_PENDING_KEY);
      } else if (result.pending) {
        console.log(LOG, PTAG, 'SYNC. ⏳ Repoussée —', result.reason);
      } else {
        console.log(LOG, PTAG, 'SYNC. ❌ Échouée —', result.error || result.reason);
      }

      _pushSyncing = false;
      return result;
    } catch (err) {
      console.error(LOG, PTAG, 'SYNC. ❌ Exception:', err.message);
      console.error(LOG, PTAG, '  Stack:', err.stack);
      _pushSyncing = false;
      return { success: false, error: 'exception: ' + err.message };
    }
  }

  // ══════════════════════════════════════════════════════════
  //  HELPERS
  // ══════════════════════════════════════════════════════════

  function urlBase64ToUint8Array(base64String) {
    try {
      const padding = '='.repeat((4 - base64String.length % 4) % 4);
      const base64 = (base64String + padding).replace(/\-/g, '+').replace(/_/g, '/');
      const rawData = window.atob(base64);
      const outputArray = new Uint8Array(rawData.length);
      for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
      }
      return outputArray;
    } catch (err) {
      console.error(LOG, PTAG, '❌ urlBase64ToUint8Array:', err.message);
      throw err;
    }
  }

  function _isAuthPage() {
    try {
      return document.querySelector('.topbar-profile') !== null
          || document.querySelector('.sidebar') !== null
          || document.querySelector('.balance-card') !== null
          || document.querySelector('.mobile-bottom-nav') !== null;
    } catch (err) {
      console.error(LOG, PTAG, '❌ _isAuthPage exception:', err.message);
      return false;
    }
  }

  // ══════════════════════════════════════════════════════════
  //  AUTO-SYNC SUR PAGE AUTHENTIFIÉE
  // ══════════════════════════════════════════════════════════
  function autoSyncOnAuthPages() {
    console.log(LOG, PTAG, 'AUTO-SYNC. autoSyncOnAuthPages()');

    const isAuth = _isAuthPage();
    console.log(LOG, PTAG, 'AUTO-SYNC. _isAuthPage():', isAuth);

    if (!isAuth) {
      console.log(LOG, PTAG, 'AUTO-SYNC. Page non auth → ignoré');
      return;
    }

    const pending = localStorage.getItem(PUSH_PENDING_KEY);
    console.log(LOG, PTAG, 'AUTO-SYNC. PUSH_PENDING_KEY:', pending);

    if (!pending) {
      console.log(LOG, PTAG, 'AUTO-SYNC. Pas de pending → ignoré');
      return;
    }

    const justLoggedIn = sessionStorage.getItem('transafrik_just_logged_in');
    console.log(LOG, PTAG, 'AUTO-SYNC. just_logged_in:', justLoggedIn);

    if (justLoggedIn) {
      sessionStorage.removeItem('transafrik_just_logged_in');
      console.log(LOG, PTAG, 'AUTO-SYNC. → Sync IMMÉDIATE (800ms)');
      setTimeout(() => {
        syncPushSubscription().catch(err => {
          console.error(LOG, PTAG, 'AUTO-SYNC. ❌ just_logged_in sync échouée:', err.message);
        });
      }, 800);
    } else {
      console.log(LOG, PTAG, 'AUTO-SYNC. → Sync normale (2000ms)');
      setTimeout(() => {
        syncPushSubscription().catch(err => {
          console.error(LOG, PTAG, 'AUTO-SYNC. ❌ sync échouée:', err.message);
        });
      }, 2000);
    }
  }

  // ══════════════════════════════════════════════════════════
  //  ÉCOUTEURS FOCUS / VISIBILITY
  // ══════════════════════════════════════════════════════════
  function setupPushSyncListeners() {
    console.log(LOG, PTAG, 'LISTENERS. setupPushSyncListeners()');

    try {
      window.addEventListener('focus', () => {
        if (!localStorage.getItem(PUSH_PENDING_KEY)) return;
        if (!_isAuthPage()) return;
        console.log(LOG, PTAG, 'LISTENERS. focus → sync (1500ms)');
        setTimeout(() => {
          syncPushSubscription().catch(err => {
            console.error(LOG, PTAG, 'LISTENERS. focus sync échouée:', err.message);
          });
        }, 1500);
      });

      document.addEventListener('visibilitychange', () => {
        if (document.hidden) return;
        if (!localStorage.getItem(PUSH_PENDING_KEY)) return;
        if (!_isAuthPage()) return;
        console.log(LOG, PTAG, 'LISTENERS. visibilitychange → sync (1500ms)');
        setTimeout(() => {
          syncPushSubscription().catch(err => {
            console.error(LOG, PTAG, 'LISTENERS. visibilitychange sync échouée:', err.message);
          });
        }, 1500);
      });

      console.log(LOG, PTAG, 'LISTENERS. ✅ focus + visibilitychange actifs');
    } catch (err) {
      console.error(LOG, PTAG, 'LISTENERS. ❌ Exception:', err.message);
    }
  }

  // ══════════════════════════════════════════════════════════
  //  LOGIN SUCCESS (appel explicite)
  // ══════════════════════════════════════════════════════════
  function onLoginSuccess() {
    console.log(LOG, PTAG, 'LOGIN. onLoginSuccess() appelé');
    try {
      if (!localStorage.getItem(PUSH_PENDING_KEY)) {
        console.log(LOG, PTAG, 'LOGIN. Pas de pending → ignoré');
        return;
      }
      console.log(LOG, PTAG, 'LOGIN. → sync (1500ms)');
      setTimeout(() => {
        syncPushSubscription().catch(err => {
          console.error(LOG, PTAG, 'LOGIN. sync échouée:', err.message);
        });
      }, 1500);
    } catch (err) {
      console.error(LOG, PTAG, 'LOGIN. ❌ Exception:', err.message);
    }
  }

  // ══════════════════════════════════════════════════════════
  //  WAIT FOR SW READY
  // ══════════════════════════════════════════════════════════
  function waitForSWReady() {
    console.log(LOG, PTAG, 'WAIT. waitForSWReady()');
    return new Promise((resolve, reject) => {
      try {
        if (!('serviceWorker' in navigator)) {
          console.warn(LOG, PTAG, 'WAIT. serviceWorker non supporté');
          return reject(new Error('SW non supporté'));
        }
        navigator.serviceWorker.ready.then(reg => {
          console.log(LOG, PTAG, 'WAIT. ✅ SW ready');
          console.log(LOG, PTAG, 'WAIT. scope:', reg.scope);
          console.log(LOG, PTAG, 'WAIT. pushManager:', !!reg.pushManager);
          console.log(LOG, PTAG, 'WAIT. active:', !!reg.active);
          _swRegistration = reg;
          resolve(reg);
        }).catch(err => {
          console.error(LOG, PTAG, 'WAIT. ❌ SW.ready rejeté:', err.message);
          reject(err);
        });
      } catch (err) {
        console.error(LOG, PTAG, 'WAIT. ❌ Exception:', err.message);
        reject(err);
      }
    });
  }

  // ══════════════════════════════════════════════════════════
  //  MISE À JOUR SW
  // ══════════════════════════════════════════════════════════
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
        <span><i class="fa-solid fa-rocket" style="margin-right:8px"></i>Nouvelle version disponible</span>
        <button id="pwa-update-btn" style="
          padding:10px 20px;background:#fff;color:#2563EB;
          border:none;border-radius:10px;font-weight:700;font-size:13px;
          cursor:pointer;font-family:'Inter',sans-serif;
        ">Mettre à jour</button>
        <button id="pwa-update-close" style="
          background:none;border:none;color:rgba(255,255,255,.7);
          cursor:pointer;font-size:18px;padding:4px;
        "><i class="fa-solid fa-xmark"></i></button>
      </div>
      <style>@keyframes slideUp{from{opacity:0;transform:translateX(-50%) translateY(30px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}</style>
    `;
    document.body.appendChild(banner);
    document.getElementById('pwa-update-btn').addEventListener('click', () => { banner.remove(); onUpdate(); });
    document.getElementById('pwa-update-close').addEventListener('click', () => banner.remove());
  }

  // ══════════════════════════════════════════════════════════
  //  INSTALL BANNER
  // ══════════════════════════════════════════════════════════
  function setupInstallBanner() {
    let deferredPrompt = null;
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      deferredPrompt = e;
      if (sessionStorage.getItem('pwa_install_dismissed')) return;
      showInstallBanner(() => {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(r => {
          console.log(LOG, 'INSTALL. Choix:', r.outcome);
          deferredPrompt = null;
        });
      });
    });
    window.addEventListener('appinstalled', () => {
      console.log(LOG, 'INSTALL. ✅ PWA installée');
      deferredPrompt = null;
    });
    const isIOS = /iphone|ipad|ipod/.test(navigator.userAgent.toLowerCase());
    const isStandalone = 'standalone' in navigator && navigator.standalone;
    if (isIOS && !isStandalone && !sessionStorage.getItem('pwa_ios_shown')) {
      sessionStorage.setItem('pwa_ios_shown', '1');
      setTimeout(() => showIOSGuide(), 3000);
    }
  }

  function showInstallBanner(onInstall) {
    if (document.getElementById('pwa-install-banner')) return;
    const banner = document.createElement('div');
    banner.id = 'pwa-install-banner';
    banner.innerHTML = `
      <div style="
        position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:99999;
        background:#fff;color:#0F172A;padding:20px 28px;border-radius:20px;
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
          border:none;border-radius:10px;font-weight:700;font-size:13px;cursor:pointer;
        ">Installer</button>
        <button id="pwa-install-close" style="
          background:none;border:none;color:#94A3B8;cursor:pointer;font-size:18px;padding:4px;
        "><i class="fa-solid fa-xmark"></i></button>
      </div>
    `;
    document.body.appendChild(banner);
    document.getElementById('pwa-install-btn').addEventListener('click', () => { banner.remove(); onInstall(); });
    document.getElementById('pwa-install-close').addEventListener('click', () => {
      banner.remove(); sessionStorage.setItem('pwa_install_dismissed', '1');
    });
  }

  function showIOSGuide() {
    if (document.getElementById('pwa-ios-guide')) return;
    const guide = document.createElement('div');
    guide.id = 'pwa-ios-guide';
    guide.innerHTML = `
      <div style="
        position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:99999;
        background:#fff;color:#0F172A;padding:24px;border-radius:20px;
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
            <div><div style="font-size:13px;font-weight:600">1. Appuyez sur <span style="color:#2563EB">Partager</span></div>
            <div style="font-size:11px;color:#94A3B8;margin-top:2px">dans la barre d'outils Safari</div></div>
          </div>
          <div style="display:flex;align-items:center;gap:12px">
            <div style="width:32px;height:32px;border-radius:8px;background:#10B981;display:flex;align-items:center;justify-content:center;flex-shrink:0">
              <i class="fa-solid fa-plus" style="color:#fff;font-size:14px"></i>
            </div>
            <div><div style="font-size:13px;font-weight:600">2. Sélectionnez <span style="color:#10B981">Sur l'écran d'accueil</span></div>
            <div style="font-size:11px;color:#94A3B8;margin-top:2px">dans le menu qui s'affiche</div></div>
          </div>
          <div style="display:flex;align-items:center;gap:12px">
            <div style="width:32px;height:32px;border-radius:8px;background:#F59E0B;display:flex;align-items:center;justify-content:center;flex-shrink:0">
              <i class="fa-solid fa-check" style="color:#fff;font-size:14px"></i>
            </div>
            <div><div style="font-size:13px;font-weight:600">3. Appuyez sur <span style="color:#F59E0B">Ajouter</span></div>
            <div style="font-size:11px;color:#94A3B8;margin-top:2px">pour confirmer l'installation</div></div>
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
    const rm = () => guide.remove();
    document.getElementById('pwa-ios-close').addEventListener('click', rm);
    document.getElementById('pwa-ios-gotit').addEventListener('click', rm);
  }

  // ══════════════════════════════════════════════════════════
  //  NETWORK DETECTION
  // ══════════════════════════════════════════════════════════
  function setupNetworkDetection() {
    window.addEventListener('online', () => {
      const toast = document.createElement('div');
      toast.style.cssText = 'position:fixed;top:88px;right:24px;z-index:99999;background:#10B981;color:#fff;padding:12px 20px;border-radius:12px;font-family:Inter,sans-serif;font-size:13px;font-weight:600;box-shadow:0 8px 24px rgba(16,185,129,.3)';
      toast.innerHTML = '<i class="fa-solid fa-wifi" style="margin-right:8px"></i>Connexion rétablie';
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 3000);
    });
    window.addEventListener('offline', () => {
      const toast = document.createElement('div');
      toast.style.cssText = 'position:fixed;top:88px;right:24px;z-index:99999;background:#F59E0B;color:#fff;padding:12px 20px;border-radius:12px;font-family:Inter,sans-serif;font-size:13px;font-weight:600;box-shadow:0 8px 24px rgba(245,158,11,.3)';
      toast.innerHTML = '<i class="fa-solid fa-triangle-exclamation" style="margin-right:8px"></i>Mode hors connexion';
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 3000);
    });
  }

  // ══════════════════════════════════════════════════════════
  //  LOGOUT CLEANUP
  // ══════════════════════════════════════════════════════════
  function setupLogoutCleanup() {
    document.addEventListener('click', (e) => {
      const link = e.target.closest('a[href*="logout"]');
      if (link) {
        if (navigator.serviceWorker && navigator.serviceWorker.controller) {
          navigator.serviceWorker.controller.postMessage('CLEAR_ALL_CACHES');
        }
        localStorage.removeItem('transafrik_balance');
        sessionStorage.clear();
      }
    });
  }

  // ══════════════════════════════════════════════════════════
  //  INIT — DOMContentLoaded
  // ══════════════════════════════════════════════════════════
  document.addEventListener('DOMContentLoaded', () => {
    console.log(LOG, '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log(LOG, 'DOMContentLoaded — INIT');

    try {
      console.log(LOG, '  → registerSW()');
      registerSW();
    } catch (err) {
      console.error(LOG, '❌ registerSW() exception:', err.message, err.stack);
    }

    try {
      console.log(LOG, '  → setupInstallBanner()');
      setupInstallBanner();
    } catch (err) {
      console.error(LOG, '❌ setupInstallBanner() exception:', err.message);
    }

    try {
      console.log(LOG, '  → setupNetworkDetection()');
      setupNetworkDetection();
    } catch (err) {
      console.error(LOG, '❌ setupNetworkDetection() exception:', err.message);
    }

    try {
      console.log(LOG, '  → setupLogoutCleanup()');
      setupLogoutCleanup();
    } catch (err) {
      console.error(LOG, '❌ setupLogoutCleanup() exception:', err.message);
    }

    try {
      console.log(LOG, '  → setupPushSyncListeners()');
      setupPushSyncListeners();
    } catch (err) {
      console.error(LOG, '❌ setupPushSyncListeners() exception:', err.message);
    }

    try {
      console.log(LOG, '  → autoSyncOnAuthPages()');
      autoSyncOnAuthPages();
    } catch (err) {
      console.error(LOG, '❌ autoSyncOnAuthPages() exception:', err.message);
    }

    // ── ÉCOUTEUR : MESSAGES DU SERVICE WORKER ──
    try {
      if (navigator.serviceWorker) {
        navigator.serviceWorker.addEventListener('message', (event) => {
          console.log(LOG, 'MSG SW → client reçu:', event.data);
          if (event.data && event.data.type === 'NAVIGATE_EXTERNAL') {
            const extUrl = event.data.url;
            console.log(LOG, 'MSG → NAVIGATE_EXTERNAL:', extUrl);
            if (extUrl) {
              window.location.href = extUrl;
            }
          }
        });
        console.log(LOG, '  → SW message listener installé');
      }
    } catch (err) {
      console.error(LOG, '❌ SW message listener exception:', err.message);
    }

    console.log(LOG, '✅ INIT terminé');
  });

  // ══════════════════════════════════════════════════════════
  //  API GLOBALE
  // ══════════════════════════════════════════════════════════
  window.TransAfrik = window.TransAfrik || {};
  window.TransAfrik.syncPushSubscription = syncPushSubscription;
  window.TransAfrik.subscribeToPush = subscribeToPushWithLogs;
  window.TransAfrik.waitForSWReady = waitForSWReady;
  window.TransAfrik.onLoginSuccess = onLoginSuccess;

  console.log(LOG, 'API TransAfrik.* exposée :', Object.keys(window.TransAfrik));
  console.log(LOG, '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
})();