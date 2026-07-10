/**
 * TransAfrik — Scanner QR Code (JS)
 * 
 * Fonctionnalités :
 * - Scanner caméra en temps réel (jsQR)
 * - Upload d'image QR
 * - Saisie manuelle de texte QR
 * - Gestion de "Mon QR" (partage, téléchargement, impression, copie)
 * - Affichage historique des scans
 * - Validation côté client (type, champs)
 * - Feedback visuel + vibration + son
 * 
 * Bibliothèque externe : jsQR (https://github.com/cozmo/jsQR)
 * Chargée via CDN dans le template scan.html
 */

(function () {
  'use strict';

  // ══════════════════════════════════════════════════════
  // ÉTAT GLOBAL
  // ══════════════════════════════════════════════════════
  let videoStream = null;
  let scanInterval = null;
  let isScanning = false;
  let currentTab = 'my-qr'; // 'my-qr' | 'scanner' | 'history'
  let lastScanData = null;

  // Éléments DOM (remplis après DOMContentLoaded)
  let elements = {};

  // ══════════════════════════════════════════════════════
  // INITIALISATION
  // ══════════════════════════════════════════════════════
  document.addEventListener('DOMContentLoaded', function () {
    cacheElements();
    bindEvents();
    initTabs();
    checkAutoStart();
    refreshQR();
  });

  function cacheElements() {
    elements = {
      // Tabs
      tabButtons: document.querySelectorAll('.scan-tab'),
      tabPanels: document.querySelectorAll('.scan-tab-panel'),

      // Mon QR
      qrImage: document.getElementById('qrImage'),
      qrImageWrapper: document.getElementById('qrImageWrapper'),
      qrProfileName: document.getElementById('qrProfileName'),
      qrProfilePhone: document.getElementById('qrProfilePhone'),
      qrProfileCountry: document.getElementById('qrProfileCountry'),
      qrIdentifier: document.getElementById('qrIdentifier'),
      qrAvatar: document.getElementById('qrAvatar'),
      qrLoading: document.getElementById('qrLoading'),

      // QR Actions
      btnShare: document.getElementById('btnShareQR'),
      btnDownload: document.getElementById('btnDownloadQR'),
      btnPrint: document.getElementById('btnPrintQR'),
      btnCopyId: document.getElementById('btnCopyId'),

      // Scanner
      scannerViewport: document.getElementById('scannerViewport'),
      scannerVideo: document.getElementById('scannerVideo'),
      scannerPlaceholder: document.getElementById('scannerPlaceholder'),
      btnStartScan: document.getElementById('btnStartScan'),
      btnStopScan: document.getElementById('btnStopScan'),
      btnUploadQR: document.getElementById('btnUploadQR'),
      fileInput: document.getElementById('fileInput'),

      // Texte manuel
      manualText: document.getElementById('manualText'),
      btnManualScan: document.getElementById('btnManualScan'),

      // Feedback
      scanFeedback: document.getElementById('scanFeedback'),
      feedbackIcon: document.getElementById('feedbackIcon'),
      feedbackTitle: document.getElementById('feedbackTitle'),
      feedbackSub: document.getElementById('feedbackSub'),
      feedbackAction: document.getElementById('feedbackAction'),

      // Historique
      historyList: document.getElementById('historyList'),
      scanEmpty: document.getElementById('scanEmpty'),
    };
  }

  function bindEvents() {
    // Tabs
    elements.tabButtons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        switchTab(this.dataset.tab);
      });
    });

    // Mon QR Actions
    if (elements.btnShare) elements.btnShare.addEventListener('click', shareQR);
    if (elements.btnDownload) elements.btnDownload.addEventListener('click', downloadQR);
    if (elements.btnPrint) elements.btnPrint.addEventListener('click', printQR);
    if (elements.btnCopyId) elements.btnCopyId.addEventListener('click', copyQRId);

    // Scanner
    if (elements.btnStartScan) elements.btnStartScan.addEventListener('click', startScanner);
    if (elements.btnStopScan) elements.btnStopScan.addEventListener('click', stopScanner);
    if (elements.btnUploadQR) elements.btnUploadQR.addEventListener('click', function () {
      elements.fileInput.click();
    });
    if (elements.fileInput) elements.fileInput.addEventListener('change', handleFileUpload);
    if (elements.btnManualScan) elements.btnManualScan.addEventListener('click', handleManualText);

    // Feedback action button
    if (elements.feedbackAction) {
      elements.feedbackAction.addEventListener('click', function () {
        if (lastScanData) {
          navigateToTransfer(lastScanData);
        }
      });
    }
  }

  // ══════════════════════════════════════════════════════
  // TABS
  // ══════════════════════════════════════════════════════
  function initTabs() {
    // Activer le premier onglet visible
    var defaultTab = document.querySelector('.scan-tab.active');
    if (defaultTab) {
      switchTab(defaultTab.dataset.tab, true);
    }
  }

  function switchTab(tabName, silent) {
    // Arrêter le scanner si on quitte l'onglet scanner
    if (currentTab === 'scanner' && tabName !== 'scanner') {
      stopScanner();
    }

    currentTab = tabName;

    // Mise à jour des boutons
    elements.tabButtons.forEach(function (btn) {
      btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    // Mise à jour des panneaux
    elements.tabPanels.forEach(function (panel) {
      panel.style.display = panel.dataset.panel === tabName ? '' : 'none';
    });

    // Actions spécifiques
    if (tabName === 'scanner' && !silent) {
      // Ne pas auto-démarrer, l'utilisateur clique sur le bouton
    }
    if (tabName === 'my-qr') {
      refreshQR();
    }
  }

  // ══════════════════════════════════════════════════════
  // MON QR — GESTION
  // ══════════════════════════════════════════════════════
  function refreshQR() {
    var img = elements.qrImage;
    var wrapper = elements.qrImageWrapper;
    var loading = elements.qrLoading;

    if (!img || !wrapper) return;

    // Afficher le loader
    if (loading) loading.style.display = 'flex';
    if (wrapper) wrapper.style.display = 'none';

    // Appel API pour récupérer le QR Code
    fetch('/api/qrcode/my')
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (loading) loading.style.display = 'none';
        if (wrapper) wrapper.style.display = 'flex';

        if (data.success && data.qr_image) {
          img.src = data.qr_image;
          img.style.display = 'block';

          // Mettre à jour les infos profil
          if (elements.qrProfileName) elements.qrProfileName.textContent = data.user.name || '—';
          if (elements.qrProfilePhone) elements.qrProfilePhone.textContent = data.user.phone || '—';
          if (elements.qrProfileCountry) {
            elements.qrProfileCountry.innerHTML = (data.user.flag || '') + ' ' + (data.user.country_name || data.user.country || '—');
          }
          if (elements.qrIdentifier) elements.qrIdentifier.textContent = data.user.qr_id || '—';
          if (elements.qrAvatar) {
            elements.qrAvatar.textContent = getInitials(data.user.name || '');
          }
        } else {
          img.style.display = 'none';
          showToast('Erreur lors du chargement du QR Code', 'error');
        }
      })
      .catch(function (err) {
        if (loading) loading.style.display = 'none';
        if (wrapper) wrapper.style.display = 'flex';
        img.style.display = 'none';
        showToast('Erreur réseau : ' + err.message, 'error');
      });
  }

  function shareQR() {
    if (!navigator.share) {
      // Fallback : copier le lien
      copyQRId();
      showToast('Lien copié ! Partagez-le manuellement.', 'info');
      return;
    }

    var qrId = elements.qrIdentifier ? elements.qrIdentifier.textContent : '';
    navigator.share({
      title: 'Mon QR TransAfrik',
      text: 'Scannez mon QR Code pour m\'envoyer de l\'argent avec TransAfrik ! ID : ' + qrId,
      url: window.location.origin + '/scan',
    }).catch(function () {
      // L'utilisateur a annulé
    });
  }

  function downloadQR() {
    var img = elements.qrImage;
    if (!img || !img.src || img.src === '') {
      showToast('QR Code non disponible', 'error');
      return;
    }

    // Créer un lien de téléchargement
    var a = document.createElement('a');
    a.href = img.src;
    a.download = 'transafrik-qr-' + (elements.qrIdentifier ? elements.qrIdentifier.textContent : 'code') + '.png';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    showToast('QR Code téléchargé !', 'success');
  }

  function printQR() {
    var img = elements.qrImage;
    if (!img || !img.src || img.src === '') {
      showToast('QR Code non disponible', 'error');
      return;
    }

    var name = elements.qrProfileName ? elements.qrProfileName.textContent : 'TransAfrik';
    var id = elements.qrIdentifier ? elements.qrIdentifier.textContent : '';

    var win = window.open('', '_blank', 'width=500,height=700');
    win.document.write(
      '<html><head><title>QR TransAfrik - ' + name + '</title>' +
      '<style>body{font-family:Arial,sans-serif;text-align:center;padding:40px}' +
      'img{width:300px;height:300px;margin:20px 0}' +
      'h2{color:#2361FF;margin:0}' +
      'p{color:#5A6D8A;margin:4px 0}' +
      '.id{font-family:monospace;font-size:18px;font-weight:bold;color:#0B1E3D}' +
      '@media print{body{padding:20px}}</style></head>' +
      '<body>' +
      '<h2>' + escapeHTML(name) + '</h2>' +
      '<p>Scanner pour envoyer de l\'argent</p>' +
      '<img src="' + img.src + '" />' +
      '<div class="id">' + escapeHTML(id) + '</div>' +
      '<p style="margin-top:20px;font-size:12px;color:#999">TransAfrik © 2026</p>' +
      '<script>window.onload=function(){window.print();}<' + '/script>' +
      '</body></html>'
    );
    win.document.close();
  }

  function copyQRId() {
    var id = elements.qrIdentifier ? elements.qrIdentifier.textContent : '';
    if (!id) {
      showToast('Identifiant non disponible', 'error');
      return;
    }

    navigator.clipboard.writeText(id).then(function () {
      var btn = elements.btnCopyId;
      if (btn) {
        var originalHTML = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-check"></i> Copié !';
        setTimeout(function () { btn.innerHTML = originalHTML; }, 2000);
      }
      showToast('Identifiant copié : ' + id, 'success');
    }).catch(function () {
      showToast('Erreur lors de la copie', 'error');
    });
  }

  // ══════════════════════════════════════════════════════
  // SCANNER CAMÉRA
  // ══════════════════════════════════════════════════════
  function checkAutoStart() {
    // Ne pas auto-démarrer, respecter la vie privée
  }

  function startScanner() {
    if (isScanning) return;

    // Vérifier la disponibilité de getUserMedia
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showToast('Votre navigateur ne supporte pas la caméra.', 'error');
      return;
    }

    // Vérifier si jsQR est chargé
    if (typeof jsQR === 'undefined') {
      showToast('Bibliothèque de scan non chargée. Rechargez la page.', 'error');
      return;
    }

    navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment', width: { ideal: 640 }, height: { ideal: 640 } }
    }).then(function (stream) {
      videoStream = stream;
      elements.scannerVideo.srcObject = stream;
      elements.scannerVideo.style.display = 'block';
      elements.scannerPlaceholder.style.display = 'none';
      elements.btnStartScan.style.display = 'none';
      elements.btnStopScan.style.display = '';

      elements.scannerVideo.play();
      isScanning = true;

      // Démarrer la boucle de scan
      scanLoop();
    }).catch(function (err) {
      console.error('Erreur caméra :', err);
      if (err.name === 'NotAllowedError') {
        showToast('Accès à la caméra refusé. Veuillez autoriser l\'accès.', 'error');
      } else if (err.name === 'NotFoundError') {
        showToast('Aucune caméra détectée.', 'error');
      } else {
        showToast('Erreur caméra : ' + err.message, 'error');
      }
    });
  }

  function stopScanner() {
    isScanning = false;

    if (scanInterval) {
      clearInterval(scanInterval);
      scanInterval = null;
    }

    if (videoStream) {
      videoStream.getTracks().forEach(function (track) { track.stop(); });
      videoStream = null;
    }

    if (elements.scannerVideo) {
      elements.scannerVideo.srcObject = null;
      elements.scannerVideo.style.display = 'none';
    }
    if (elements.scannerPlaceholder) {
      elements.scannerPlaceholder.style.display = '';
    }
    if (elements.btnStartScan) elements.btnStartScan.style.display = '';
    if (elements.btnStopScan) elements.btnStopScan.style.display = 'none';
  }

  function scanLoop() {
    if (!isScanning) return;

    scanInterval = setInterval(function () {
      if (!isScanning) {
        clearInterval(scanInterval);
        return;
      }

      var video = elements.scannerVideo;
      if (!video || video.readyState !== video.HAVE_ENOUGH_DATA) return;

      // Créer un canvas temporaire pour capturer l'image
      var canvas = document.createElement('canvas');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      var ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      var imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);

      // Analyser avec jsQR
      var code = jsQR(imageData.data, imageData.width, imageData.height, {
        inversionAttempts: 'dontInvert',
      });

      if (code && code.data) {
        // QR détecté !
        handleScanResult(code.data);
        stopScanner();
      }
    }, 200); // Scan toutes les 200ms
  }

  // ══════════════════════════════════════════════════════
  // UPLOAD IMAGE QR
  // ══════════════════════════════════════════════════════
  function handleFileUpload(event) {
    var file = event.target.files[0];
    if (!file) return;

    if (typeof jsQR === 'undefined') {
      showToast('Bibliothèque de scan non chargée.', 'error');
      return;
    }

    var reader = new FileReader();
    reader.onload = function (e) {
      var img = new Image();
      img.onload = function () {
        var canvas = document.createElement('canvas');
        canvas.width = img.width;
        canvas.height = img.height;
        var ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0);
        var imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);

        var code = jsQR(imageData.data, imageData.width, imageData.height, {
          inversionAttempts: 'dontInvert',
        });

        if (code && code.data) {
          handleScanResult(code.data);
        } else {
          showToast('Aucun QR Code détecté dans cette image.', 'error');
          showScanFeedback(null, false, 'Aucun QR Code détecté');
        }
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);

    // Réinitialiser l'input pour permettre de re-sélectionner le même fichier
    event.target.value = '';
  }

  // ══════════════════════════════════════════════════════
  // TEXTE MANUEL
  // ══════════════════════════════════════════════════════
  function handleManualText() {
    var text = elements.manualText ? elements.manualText.value.trim() : '';
    if (!text) {
      showToast('Veuillez coller le contenu du QR Code.', 'error');
      return;
    }

    handleScanResult(text);
  }

  // ══════════════════════════════════════════════════════
  // TRAITEMENT DU RÉSULTAT DE SCAN
  // ══════════════════════════════════════════════════════
  function handleScanResult(rawData) {
    if (!rawData) return;

    // Sauvegarder pour le bouton d'action
    lastScanData = rawData;

    // Valider côté client (validation rapide)
    var parsed = tryParseJSON(rawData);
    if (!parsed) {
      showToast('QR Code invalide : format non reconnu.', 'error');
      showScanFeedback(null, false, 'Format JSON invalide');
      return;
    }

    var qrType = parsed.type || '';
    if (qrType === 'transafrik_user' || qrType === 'transafrik_merchant' || qrType === 'transafrik_deposit' || qrType === 'transafrik_withdraw' || qrType === 'transafrik_invoice') {
      // QR TransAfrik valide côté client
      handleTransafrikQR(parsed, rawData);
    } else {
      // QR inconnu — on le signale
      showToast('Ce QR Code n\'est pas un QR TransAfrik.', 'info');
      showScanFeedback(parsed, false, 'Type de QR non reconnu : ' + (qrType || 'inconnu'));
    }
  }

  function handleTransafrikQR(parsed, rawData) {
    // Vérifier les champs obligatoires pour un user QR
    if (parsed.type === 'transafrik_user') {
      var required = ['user_id', 'name', 'phone', 'country', 'operator'];
      var missing = required.filter(function (f) { return !parsed[f]; });
      if (missing.length > 0) {
        showToast('QR Code invalide : champs manquants.', 'error');
        showScanFeedback(parsed, false, 'Champs manquants : ' + missing.join(', '));
        return;
      }
    }

    // Succès ! Animation + vibration + son
    playSuccessFeedback();

    // Afficher le feedback visuel
    showScanFeedback(parsed, true, 'Prêt pour le transfert');

    // Afficher un toast
    showToast('QR Code scanné avec succès ! ' + (parsed.name || ''), 'success');

    // Envoyer au serveur pour enregistrement + validation complète
    fetch('/api/qrcode/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data: rawData }),
    }).then(function (res) { return res.json(); })
      .then(function (serverResult) {
        if (serverResult.success && serverResult.valid) {
          // Mettre à jour le bouton d'action avec l'URL
          if (elements.feedbackAction) {
            elements.feedbackAction.setAttribute('data-action-url', serverResult.action_url || '/send-money');
          }
          // Rafraîchir l'historique
          refreshHistory();
        }
      })
      .catch(function () {
        // Erreur silencieuse — le client a déjà le feedback
      });
  }

  function showScanFeedback(parsed, isValid, message) {
    var fb = elements.scanFeedback;
    if (!fb) return;

    fb.classList.remove('success', 'error');
    fb.classList.add('show');

    if (isValid && parsed) {
      fb.classList.add('success');
      if (elements.feedbackIcon) {
        elements.feedbackIcon.className = 'fa-solid fa-circle-check';
      }
      if (elements.feedbackTitle) {
        elements.feedbackTitle.textContent = parsed.name || 'Contact détecté';
      }
      if (elements.feedbackSub) {
        elements.feedbackSub.textContent = (parsed.phone || '') + ' · ' + (parsed.country || '') + ' · ' + (parsed.operator || '');
      }
      if (elements.feedbackAction) {
        elements.feedbackAction.style.display = '';
        elements.feedbackAction.textContent = 'Envoyer de l\'argent →';
      }
    } else {
      fb.classList.add('error');
      if (elements.feedbackIcon) {
        elements.feedbackIcon.className = 'fa-solid fa-circle-xmark';
      }
      if (elements.feedbackTitle) {
        elements.feedbackTitle.textContent = 'QR Code invalide';
      }
      if (elements.feedbackSub) {
        elements.feedbackSub.textContent = message || 'Format non reconnu';
      }
      if (elements.feedbackAction) {
        elements.feedbackAction.style.display = 'none';
      }
    }

    // Auto-cacher après 8 secondes
    clearTimeout(fb._timeout);
    fb._timeout = setTimeout(function () {
      fb.classList.remove('show');
    }, 8000);
  }

  function navigateToTransfer(parsedOrRaw) {
    var data;
    if (typeof parsedOrRaw === 'string') {
      data = tryParseJSON(parsedOrRaw);
    } else {
      data = parsedOrRaw;
    }

    if (!data) return;

    // Construire l'URL avec les paramètres pré-remplis
    var params = new URLSearchParams();
    if (data.name) params.set('name', data.name);
    if (data.phone) params.set('phone', data.phone);
    if (data.country) params.set('country', data.country);
    if (data.operator) params.set('operator', data.operator);
    if (data.qr_id) params.set('qr_id', data.qr_id);

    var url = '/send-money?' + params.toString();
    window.location.href = url;
  }

  // ══════════════════════════════════════════════════════
  // FEEDBACK VISUEL + SON + VIBRATION
  // ══════════════════════════════════════════════════════
  function playSuccessFeedback() {
    // Vibration (mobile)
    if (navigator.vibrate) {
      navigator.vibrate([50, 30, 50]);
    }

    // Son de confirmation (beep court)
    try {
      var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      var osc = audioCtx.createOscillator();
      var gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.frequency.setValueAtTime(880, audioCtx.currentTime); // La₅
      osc.frequency.setValueAtTime(1100, audioCtx.currentTime + 0.08); // Do#₆
      gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.25);
      osc.start(audioCtx.currentTime);
      osc.stop(audioCtx.currentTime + 0.25);
    } catch (e) {
      // Audio non supporté — silencieux
    }
  }

  // ══════════════════════════════════════════════════════
  // TOAST NOTIFICATIONS
  // ══════════════════════════════════════════════════════
  function showToast(message, type) {
    // Supprimer les toasts existants
    var existing = document.querySelectorAll('.scan-result-toast');
    existing.forEach(function (el) { el.remove(); });

    var toast = document.createElement('div');
    toast.className = 'scan-result-toast ' + (type || 'info');
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(function () {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.3s';
      setTimeout(function () { toast.remove(); }, 300);
    }, 3000);
  }

  // ══════════════════════════════════════════════════════
  // HISTORIQUE
  // ══════════════════════════════════════════════════════
  function refreshHistory() {
    fetch('/api/qrcode/history')
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (!data.success || !elements.historyList) return;

        var list = elements.historyList;
        list.innerHTML = '';

        if (!data.history || data.history.length === 0) {
          if (elements.scanEmpty) elements.scanEmpty.style.display = '';
          return;
        }

        if (elements.scanEmpty) elements.scanEmpty.style.display = 'none';

        data.history.forEach(function (item) {
          var el = document.createElement('div');
          el.className = 'scan-history-item';
          el.innerHTML =
            '<div class="scan-history-avatar">' + getInitials(item.name) + '</div>' +
            '<div class="scan-history-info">' +
            '<div class="scan-history-name">' + escapeHTML(item.name) + '</div>' +
            '<div class="scan-history-meta">' +
            '<span>' + escapeHTML(item.phone) + '</span>' +
            '<span>' + escapeHTML(item.country || '') + '</span>' +
            '<span style="color:var(--blue)">' + escapeHTML(item.operator || '') + '</span>' +
            '</div>' +
            '</div>' +
            '<div class="scan-history-date">' +
            '<div>' + (item.date || '') + '</div>' +
            '<div>' + (item.time || '') + '</div>' +
            '</div>' +
            '<div class="scan-history-arrow"><i class="fa-solid fa-chevron-right"></i></div>';

          el.addEventListener('click', function () {
            // Re-remplir et naviguer vers le transfert
            var qrData = {
              type: 'transafrik_user',
              name: item.name,
              phone: item.phone,
              country: item.country,
              operator: item.operator,
            };
            navigateToTransfer(qrData);
          });

          list.appendChild(el);
        });
      })
      .catch(function () {
        // Silencieux
      });
  }

  // ══════════════════════════════════════════════════════
  // HELPERS
  // ══════════════════════════════════════════════════════
  function tryParseJSON(str) {
    if (!str || typeof str !== 'string') return null;
    try {
      return JSON.parse(str.trim());
    } catch (e) {
      return null;
    }
  }

  function getInitials(name) {
    if (!name) return '?';
    var parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return parts[0].substring(0, 2).toUpperCase();
  }

  function escapeHTML(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  // ══════════════════════════════════════════════════════
  // EXPOSER AU GLOBAL (pour le onclick dans le HTML)
  // ══════════════════════════════════════════════════════
  window.TransAfrikScan = {
    refreshQR: refreshQR,
    startScanner: startScanner,
    stopScanner: stopScanner,
    switchTab: switchTab,
    shareQR: shareQR,
    downloadQR: downloadQR,
    printQR: printQR,
    copyQRId: copyQRId,
  };

})();