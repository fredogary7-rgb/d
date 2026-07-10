import os
import logging
import hmac
import hashlib
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from models import db, User, Transfer, Deposit, Beneficiary, Transaction
from transfer_config import COUNTRIES, get_operators, get_country
from transfer_utils import calculate_fees, calculate_total
from services.service_ids import get_service_id
from services.transfer_service import get_transfer_by_reference
from services.payment_workflow import start_transfer_payment as start_payment
from services.soleaspay import pay_in
from deposit_utils import (
    DEPOSIT_COUNTRIES,
    get_deposit_operators_for_country,
    calculate_deposit_fees,
    generate_deposit_reference,
)
from services.payment_workflow import (
    handle_payment_success,
    handle_withdraw_success,
    handle_withdraw_failed,
    is_payment_success,
    is_payment_failed,
)

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 5,
    'pool_recycle': 300,
    'pool_pre_ping': True,
}

db.init_app(app)

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Create tables
with app.app_context():
    db.create_all()

# ==================== ROUTES ====================

@app.route('/')
def index():
    return render_template('index.html')

# --- LOGIN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({'success': False, 'message': 'Email ou mot de passe incorrect.'}), 401

        login_user(user, remember=data.get('remember', False))
        return jsonify({'success': True, 'message': 'Connexion réussie !', 'redirect': url_for('dashboard')})

    return render_template('connexion.html')

# --- REGISTER ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        data = request.get_json()

        email = data.get('email', '').strip().lower()
        fullname = data.get('fullname', '').strip()
        phone = data.get('phone', '').strip()
        country = data.get('country', '').strip().upper()
        password = data.get('password', '')

        # Validation
        errors = []
        if not fullname or len(fullname) < 2:
            errors.append('Nom complet requis (minimum 2 caractères).')
        if not email or '@' not in email:
            errors.append('Adresse e-mail invalide.')
        if User.query.filter_by(email=email).first():
            errors.append('Cet e-mail est déjà utilisé.')
        if not phone or len(phone.replace(' ', '').replace('+', '').replace('-', '')) < 8:
            errors.append('Numéro de téléphone invalide.')
        if country not in ['TG','BJ','CM','CI','BF','CG','CD','GA','UG','ZM','SN']:
            errors.append('Pays invalide.')
        if len(password) < 8:
            errors.append('Le mot de passe doit contenir au moins 8 caractères.')

        if errors:
            return jsonify({'success': False, 'message': errors[0], 'errors': errors}), 400

        # Create user
        user = User(
            fullname=fullname,
            email=email,
            phone=phone,
            country=country,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return jsonify({'success': True, 'message': 'Compte créé avec succès !', 'redirect': url_for('dashboard')})

    return render_template('inscription.html')

# --- LOGOUT ---
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# --- TRANSFER ---
@app.route('/transfer')
@login_required
def transfer():
    return render_template('transfer.html',
                           countries=COUNTRIES,
                           user=current_user)

# --- TRANSFER CONFIRM ---
@app.route('/transfer/confirm')
@login_required
def transfer_confirm():
    return render_template('transfer_confirm.html', user=current_user)

# --- SEND MONEY (nouveau workflow) ---
@app.route('/send-money', methods=['GET', 'POST'])
@login_required
def send_money():
    if request.method == 'POST':
        data = request.get_json()

        # Extraction des données
        amount = int(data.get('amount', 0))
        sender_country = data.get('sender_country', '').upper()
        sender_operator = data.get('sender_operator', '').lower()
        sender_number = data.get('sender_number', '').strip()
        receiver_country = data.get('receiver_country', '').upper()
        receiver_operator = data.get('receiver_operator', '').lower()
        receiver_number = data.get('receiver_number', '').strip()
        receiver_name = data.get('receiver_name', '').strip()
        currency = data.get('currency', 'XOF')

        # Validation
        errors = []
        if amount < 500:
            errors.append('Le montant minimum est de 500 FCFA.')
        if not sender_country or not sender_operator:
            errors.append('Veuillez sélectionner votre pays et opérateur.')
        if not sender_number:
            errors.append('Votre numéro de téléphone est requis.')
        if not receiver_country or not receiver_operator:
            errors.append('Veuillez sélectionner le pays et opérateur du destinataire.')
        if not receiver_number:
            errors.append('Le numéro du destinataire est requis.')
        if get_service_id(sender_country, sender_operator) is None:
            errors.append(f'Service non disponible pour {sender_country}/{sender_operator}.')
        if get_service_id(receiver_country, receiver_operator) is None:
            errors.append(f'Service non disponible pour {receiver_country}/{receiver_operator}.')

        if errors:
            return jsonify({'success': False, 'message': errors[0], 'errors': errors}), 400

        # Calcul des frais
        fees = calculate_fees(amount)
        total_amount = calculate_total(amount)

        # Nettoyage des numéros (format simple sans + ni espaces)
        def clean_phone(num):
            return num.replace('+', '').replace(' ', '').replace('-', '').strip()

        sender_number = clean_phone(sender_number)
        receiver_number = clean_phone(receiver_number)

        # Création de la transaction en base (status CREATED)
        sender_operator_id = get_service_id(sender_country, sender_operator)
        receiver_operator_id = get_service_id(receiver_country, receiver_operator)

        transfer = Transfer(
            sender_user_id=current_user.id,
            sender_name=current_user.fullname,
            sender_email=current_user.email,
            sender_phone=sender_number,
            sender_country=sender_country,
            sender_operator=sender_operator.upper(),
            sender_operator_id=sender_operator_id,
            receiver_name=receiver_name,
            receiver_phone=receiver_number,
            receiver_country=receiver_country,
            receiver_operator=receiver_operator.upper(),
            receiver_operator_id=receiver_operator_id,
            amount=amount,
            fees=fees,
            total_amount=total_amount,
            currency=currency,
            status='CREATED',
        )
        db.session.add(transfer)
        db.session.commit()

        # ---- LANCEMENT IMMÉDIAT DU PAY-IN SOLEASPAY ----
        pay_result = start_payment(transfer)
        db.session.refresh(transfer)

        return jsonify({
            'success': True,
            'message': 'Transaction créée et paiement lancé.',
            'transfer': transfer.to_dict(),
            'pay_result': pay_result,
            'redirect': url_for('send_money_confirm', ref=transfer.reference),
        })

    # GET : afficher la page
    return render_template('send_money.html',
                           countries=COUNTRIES,
                           user=current_user)

# --- SEND MONEY CONFIRM ---
@app.route('/send-money/confirm')
@login_required
def send_money_confirm():
    ref = request.args.get('ref', '')
    transfer = Transfer.query.filter_by(reference=ref, sender_user_id=current_user.id).first()
    if not transfer:
        flash('Transaction introuvable.', 'error')
        return redirect(url_for('send_money'))
    return render_template('send_money_confirm.html', transfer=transfer, user=current_user)

# --- API: Get operators for a country ---
@app.route('/api/operators/<country_code>')
@login_required
def api_operators(country_code):
    operators = get_operators(country_code.upper())
    return jsonify({'operators': operators})

# --- API: Get country info ---
@app.route('/api/country/<country_code>')
@login_required
def api_country(country_code):
    country = get_country(country_code.upper())
    if country:
        return jsonify({'country': country})
    return jsonify({'error': 'Pays non trouvé'}), 404

# --- DASHBOARD ---
@app.route('/dashboard')
@login_required
def dashboard():
    user = current_user

    # Agrégats
    tx_count = user.tx_count
    beneficiary_count = user.beneficiary_count
    total_sent = user.total_sent
    total_received = user.total_received
    unread_notifications = user.unread_notifications

    # Transactions récentes
    recent_txs = user.recent_transactions(limit=5)

    # Pays / drapeau mapping
    country_flags = {
        'TG': '🇹🇬', 'BJ': '🇧🇯', 'CM': '🇨🇲', 'CI': '🇨🇮', 'BF': '🇧🇫',
        'CG': '🇨🇬', 'CD': '🇨🇩', 'GA': '🇬🇦', 'UG': '🇺🇬', 'ZM': '🇿🇲', 'SN': '🇸🇳',
    }
    country_names = {
        'TG': 'Togo', 'BJ': 'Bénin', 'CM': 'Cameroun', 'CI': 'Côte d\'Ivoire',
        'BF': 'Burkina Faso', 'CG': 'Congo', 'CD': 'RD Congo', 'GA': 'Gabon',
        'UG': 'Ouganda', 'ZM': 'Zambie', 'SN': 'Sénégal',
    }

    return render_template(
        'dashboard.html',
        user=user,
        tx_count=tx_count,
        beneficiary_count=beneficiary_count,
        total_sent=total_sent,
        total_received=total_received,
        unread_notifications=unread_notifications,
        recent_txs=recent_txs,
        country_flags=country_flags,
        country_names=country_names,
    )

# --- API: Calculate fees ---
@app.route('/api/calculate-fees', methods=['POST'])
@login_required
def api_calculate_fees():
    data = request.get_json()
    amount = int(data.get('amount', 0))
    fees = calculate_fees(amount)
    total = calculate_total(amount)
    return jsonify({
        'amount': amount,
        'fees': fees,
        'total': total,
    })

# --- API: Check auth status ---
@app.route('/api/me')
def api_me():
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'fullname': current_user.fullname,
                'email': current_user.email,
                'phone': current_user.phone,
                'country': current_user.country,
            }
        })
    return jsonify({'authenticated': False})

# ==================== LOGGER WEBHOOK ====================

# Crée le dossier logs si nécessaire
os.makedirs('logs', exist_ok=True)

webhook_logger = logging.getLogger('webhook')
webhook_logger.setLevel(logging.INFO)

# Handler fichier
fh = logging.FileHandler('logs/payment.log', encoding='utf-8')
fh.setFormatter(logging.Formatter(
    '[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
))
webhook_logger.addHandler(fh)

# Handler console (pour debug en dev)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter('[%(asctime)s] WEBHOOK | %(message)s'))
webhook_logger.addHandler(ch)

# Clé secrète pour la validation de signature SoleasPay
SOLEAS_WEBHOOK_SECRET = os.getenv('SOLEAS_WEBHOOK_SECRET', '')


def _verify_webhook_signature(payload_body: bytes, signature_header: str) -> bool:
    """Vérifie la signature HMAC-SHA256 du webhook SoleasPay.

    Si SOLEAS_WEBHOOK_SECRET n'est pas configuré, la vérification est ignorée
    (mode développement).
    """
    if not SOLEAS_WEBHOOK_SECRET:
        webhook_logger.warning('SOLEAS_WEBHOOK_SECRET non configuré — signature ignorée')
        return True

    if not signature_header:
        webhook_logger.warning('Signature manquante dans le header')
        return False

    computed = hmac.new(
        SOLEAS_WEBHOOK_SECRET.encode('utf-8'),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    # Comparaison sécurisée (timing-safe)
    return hmac.compare_digest(computed, signature_header)


def _log_webhook(webhook_type: str, reference: str, status: str, payload: dict):
    """Enregistre un webhook dans logs/payment.log."""
    ip = request.remote_addr or 'unknown'
    webhook_logger.info(
        f"Type={webhook_type} | Reference={reference} | Status={status} | "
        f"IP={ip} | Payload={payload}"
    )


# ==================== WEBHOOKS SOLEASPAY ====================

# --- Webhook Pay-In ---
@app.route('/webhook/soleaspay/payment', methods=['POST'])
def webhook_payment():
    """Reçoit les notifications de Pay-In de SoleasPay.

    Idempotent : ne traite que si statut = PAYMENT_PROCESSING.
    """
    # Vérification de la signature
    signature = request.headers.get('X-SoleasPay-Signature', '')
    raw_body = request.get_data()
    if not _verify_webhook_signature(raw_body, signature):
        webhook_logger.warning('Signature invalide — webhook rejeté')
        return jsonify({'success': False, 'message': 'Signature invalide'}), 403

    payload = request.get_json(silent=True) or {}
    if not payload:
        return jsonify({'success': False, 'message': 'Payload invalide'}), 400

    # Récupérer le Transfer via external_reference
    external_ref = payload.get('external_reference') or payload.get('order_id') or ''
    transfer = get_transfer_by_reference(external_ref) if external_ref else None

    _log_webhook('PAYMENT', external_ref, payload.get('status', 'UNKNOWN'), payload)

    if not transfer:
        webhook_logger.warning(f'Transfer introuvable pour external_reference={external_ref}')
        return jsonify({'success': False, 'message': 'Transfer introuvable'}), 404

    # ---- IDEMPOTENCE : ne traiter que si PAYMENT_PROCESSING ----
    if transfer.status not in ('PAYMENT_PROCESSING', 'WAITING_PAYMENT'):
        webhook_logger.info(
            f'Webhook ignoré (idempotent) : transfert déjà au statut {transfer.status}'
        )
        return jsonify({
            'success': True,
            'message': f'Transfert déjà traité (statut={transfer.status})',
            'reference': transfer.reference,
            'status': transfer.status,
        })

    # ---- Traitement ----
    if is_payment_success(payload):
        transfer.webhook_payload = payload
        db.session.commit()
        handle_payment_success(transfer, payin_response=payload)
        webhook_logger.info(f'Pay-In SUCCESS → PAYMENT_SUCCESS + Withdraw lancé pour {transfer.reference}')
        return jsonify({
            'success': True,
            'message': 'Paiement confirmé, retrait lancé',
            'reference': transfer.reference,
            'status': transfer.status,
        })

    elif is_payment_failed(payload):
        from services.transfer_service import mark_payment_failed
        transfer.webhook_payload = payload
        mark_payment_failed(transfer, payin_response=payload)
        webhook_logger.info(f'Pay-In FAILED pour {transfer.reference}')
        return jsonify({
            'success': False,
            'message': 'Paiement échoué',
            'reference': transfer.reference,
            'status': transfer.status,
        })

    else:
        # Statut inconnu — on loggue sans modifier
        transfer.webhook_payload = payload
        db.session.commit()
        webhook_logger.warning(f'Statut Pay-In inconnu pour {transfer.reference}: {payload.get("status")}')
        return jsonify({
            'success': True,
            'message': 'Statut inconnu, payload enregistré',
            'reference': transfer.reference,
        })


# --- Webhook Withdraw ---
@app.route('/webhook/soleaspay/withdraw', methods=['POST'])
def webhook_withdraw():
    """Reçoit les notifications de Withdraw de SoleasPay.

    Idempotent : ne traite que si statut = WITHDRAW_PROCESSING.
    """
    # Vérification de la signature
    signature = request.headers.get('X-SoleasPay-Signature', '')
    raw_body = request.get_data()
    if not _verify_webhook_signature(raw_body, signature):
        webhook_logger.warning('Signature invalide — webhook rejeté')
        return jsonify({'success': False, 'message': 'Signature invalide'}), 403

    payload = request.get_json(silent=True) or {}
    if not payload:
        return jsonify({'success': False, 'message': 'Payload invalide'}), 400

    # Récupérer le Transfer via external_reference (contient transfer.reference)
    data = payload.get('data', {})
    if isinstance(data, list) and len(data) > 0:
        ref = data[0].get('external_reference') or data[0].get('reference') or ''
    elif isinstance(data, dict):
        ref = data.get('external_reference') or data.get('reference') or ''
    else:
        ref = ''

    transfer = get_transfer_by_reference(ref) if ref else None

    _log_webhook('WITHDRAW', ref, payload.get('status', 'UNKNOWN'), payload)

    if not transfer:
        webhook_logger.warning(f'Transfer introuvable pour reference={ref}')
        return jsonify({'success': False, 'message': 'Transfer introuvable'}), 404

    # ---- IDEMPOTENCE : ne traiter que si WITHDRAW_PROCESSING ----
    if transfer.status != 'WITHDRAW_PROCESSING':
        webhook_logger.info(
            f'Webhook ignoré (idempotent) : transfert déjà au statut {transfer.status}'
        )
        return jsonify({
            'success': True,
            'message': f'Transfert déjà traité (statut={transfer.status})',
            'reference': transfer.reference,
            'status': transfer.status,
        })

    # ---- Traitement ----
    if is_payment_success(payload):
        handle_withdraw_success(transfer, withdraw_response=payload)
        webhook_logger.info(f'Withdraw SUCCESS → COMPLETED pour {transfer.reference}')
        return jsonify({
            'success': True,
            'message': 'Transfert terminé avec succès',
            'reference': transfer.reference,
            'status': 'COMPLETED',
        })

    elif is_payment_failed(payload):
        handle_withdraw_failed(
            transfer,
            reason=payload.get('message', 'Échec du retrait'),
            webhook_payload=payload,
        )
        webhook_logger.info(f'Withdraw FAILED pour {transfer.reference}')
        return jsonify({
            'success': False,
            'message': 'Retrait échoué',
            'reference': transfer.reference,
            'status': 'FAILED',
        })

    else:
        transfer.webhook_payload = payload
        db.session.commit()
        webhook_logger.warning(f'Statut Withdraw inconnu pour {transfer.reference}: {payload.get("status")}')
        return jsonify({
            'success': True,
            'message': 'Statut inconnu, payload enregistré',
            'reference': transfer.reference,
        })


# ==================== API STATUS ====================

@app.route('/api/transfer/<reference>/status')
def api_transfer_status(reference):
    """Retourne le statut en temps réel d'un transfert.

    GET /api/transfer/TA20260710A83F91/status

    Response:
        {
            "reference": "TA20260710A83F91",
            "status": "WITHDRAW_PROCESSING",
            "amount": 15000,
            "fees": 250,
            "total_amount": 15250,
            "currency": "XOF",
            "sender_operator": "TMoney",
            "receiver_operator": "Orange Money",
            "receiver_name": "Jean Dupont",
            "created_at": "2026-07-10T08:00:00",
            "updated_at": "2026-07-10T08:05:00"
        }
    """
    transfer = get_transfer_by_reference(reference)
    if not transfer:
        return jsonify({'success': False, 'message': 'Transfert introuvable'}), 404

    return jsonify({
        'success': True,
        'reference': transfer.reference,
        'status': transfer.status,
        'amount': transfer.amount,
        'fees': transfer.fees,
        'total_amount': transfer.total_amount,
        'currency': transfer.currency,
        'exchange_rate': transfer.exchange_rate,
        'sender_country': transfer.sender_country,
        'sender_operator': transfer.sender_operator,
        'receiver_country': transfer.receiver_country,
        'receiver_operator': transfer.receiver_operator,
        'receiver_name': transfer.receiver_name,
        'payin_reference': transfer.payin_reference,
        'withdraw_reference': transfer.withdraw_reference,
        'created_at': transfer.created_at.isoformat() if transfer.created_at else None,
        'updated_at': transfer.updated_at.isoformat() if transfer.updated_at else None,
    })


# ==================== HISTORY / HISTORIQUE ====================

@app.route('/history')
@login_required
def history():
    """Page d'historique des transferts."""
    # Compteurs pour les stats cards
    transfers = Transfer.query.filter_by(sender_user_id=current_user.id)
    total_count = transfers.count()
    total_amount = db.session.query(
        db.func.coalesce(db.func.sum(Transfer.total_amount), 0)
    ).filter(Transfer.sender_user_id == current_user.id).scalar()
    completed_count = transfers.filter(Transfer.status == 'COMPLETED').count()
    pending_count = transfers.filter(
        Transfer.status.in_(['CREATED', 'WAITING_PAYMENT', 'PAYMENT_PROCESSING',
                             'PAYMENT_SUCCESS', 'WITHDRAW_PROCESSING'])
    ).count()

    return render_template('history.html',
                           user=current_user,
                           total_count=total_count,
                           total_amount=total_amount,
                           completed_count=completed_count,
                           pending_count=pending_count)


@app.route('/api/history')
@login_required
def api_history():
    """API pour le filtrage dynamique (sans rechargement de page)."""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    filter_status = request.args.get('status', 'ALL')
    search = request.args.get('search', '').strip()

    query = Transfer.query.filter_by(sender_user_id=current_user.id)

    # Filtre par statut
    if filter_status and filter_status != 'ALL':
        if filter_status == 'PENDING':
            query = query.filter(
                Transfer.status.in_(['CREATED', 'WAITING_PAYMENT', 'PAYMENT_PROCESSING',
                                     'PAYMENT_SUCCESS', 'WITHDRAW_PROCESSING'])
            )
        elif filter_status == 'COMPLETED':
            query = query.filter_by(status='COMPLETED')
        elif filter_status == 'FAILED':
            query = query.filter_by(status='FAILED')
        elif filter_status == 'CANCELLED':
            query = query.filter_by(status='CANCELLED')
        else:
            query = query.filter_by(status=filter_status)

    # Recherche
    if search:
        search_term = f'%{search}%'
        query = query.filter(
            db.or_(
                Transfer.reference.ilike(search_term),
                Transfer.receiver_phone.ilike(search_term),
                Transfer.receiver_name.ilike(search_term),
                Transfer.sender_phone.ilike(search_term),
            )
        )

    # Tri + pagination
    pagination = query.order_by(Transfer.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    country_names = {
        'TG': 'Togo', 'BJ': 'Bénin', 'CM': 'Cameroun', 'CI': 'Côte d\'Ivoire',
        'BF': 'Burkina Faso', 'CG': 'Congo', 'CD': 'RD Congo', 'GA': 'Gabon',
        'UG': 'Ouganda', 'ZM': 'Zambie', 'SN': 'Sénégal',
    }
    country_flags = {
        'TG': '🇹🇬', 'BJ': '🇧🇯', 'CM': '🇨🇲', 'CI': '🇨🇮', 'BF': '🇧🇫',
        'CG': '🇨🇬', 'CD': '🇨🇩', 'GA': '🇬🇦', 'UG': '🇺🇬', 'ZM': '🇿🇲', 'SN': '🇸🇳',
    }

    transfers_data = []
    for t in pagination.items:
        d = t.to_dict()
        d['receiver_country_name'] = country_names.get(t.receiver_country, t.receiver_country)
        d['receiver_country_flag'] = country_flags.get(t.receiver_country, '🌍')
        d['sender_country_name'] = country_names.get(t.sender_country, t.sender_country)
        d['sender_country_flag'] = country_flags.get(t.sender_country, '🌍')
        transfers_data.append(d)

    return jsonify({
        'success': True,
        'transfers': transfers_data,
        'page': pagination.page,
        'pages': pagination.pages,
        'total': pagination.total,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
    })


# ==================== HEALTH CHECK ====================

@app.route('/health')
def health():
    try:
        db.session.execute(db.text('SELECT 1'))
        return jsonify({'status': 'ok', 'db': 'connected'})
    except Exception as e:
        return jsonify({'status': 'error', 'db': str(e)}), 500


# ==================== DEPOSIT / DÉPÔT ====================

@app.route('/deposit')
@login_required
def deposit_page():
    """Page principale de dépôt d'argent."""
    return render_template('deposit.html',
                           user=current_user,
                           countries=DEPOSIT_COUNTRIES)


@app.route('/api/deposit/operators/<country_code>')
@login_required
def api_deposit_operators(country_code):
    """Retourne les opérateurs disponibles pour un pays donné (dépôt)."""
    operators = get_deposit_operators_for_country(country_code.upper())
    return jsonify({'success': True, 'operators': operators})


@app.route('/api/deposit', methods=['POST'])
@login_required
def api_create_deposit():
    """Crée un dépôt et lance le Pay-In SoleasPay (operation=2)."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Données manquantes'}), 400

    amount = int(data.get('amount', 0))
    phone = data.get('phone', '').strip()
    country = data.get('country', '').strip().upper()
    operator_slug = data.get('operator', '').strip().lower()
    operator_id = data.get('operator_id', 0)

    # Validation
    errors = []
    if amount < 500:
        errors.append('Le montant minimum est de 500.')
    if not phone or len(phone.replace('+', '').replace(' ', '')) < 8:
        errors.append('Numéro de téléphone invalide.')
    if not country:
        errors.append('Pays requis.')
    if not operator_slug or not operator_id:
        errors.append('Opérateur requis.')

    if errors:
        return jsonify({'success': False, 'message': errors[0], 'errors': errors}), 400

    # Nettoyage du numéro
    phone_clean = phone.replace('+', '').replace(' ', '').replace('-', '').strip()

    # Calcul des frais
    fees_data = calculate_deposit_fees(amount, currency='XOF')
    total_amount = fees_data['total']
    fees = fees_data['fees']

    # Récupérer les infos de l'opérateur
    from config.operators import get_operator_by_id
    op_info = get_operator_by_id(operator_id)
    currency = op_info.get('currency', 'XOF') if op_info else 'XOF'
    operator_name = op_info.get('name', operator_slug.upper()) if op_info else operator_slug.upper()

    # Créer le dépôt en base
    reference = generate_deposit_reference()

    deposit = Deposit(
        reference=reference,
        user_id=current_user.id,
        phone=phone_clean,
        country=country,
        operator=operator_name,
        operator_id=operator_id,
        amount=amount,
        fees=fees,
        total_amount=total_amount,
        currency=currency,
        status='CREATED',
    )
    db.session.add(deposit)
    db.session.commit()

    # ---- LANCEMENT DU PAY-IN SOLEASPAY ----
    try:
        result = pay_in(
            service=operator_id,
            wallet=phone_clean,
            amount=float(total_amount),
            currency=currency,
            order_id=reference,
            description=f'Dépôt TransAfrik - {reference}',
            payer=current_user.fullname,
            payer_email=current_user.email,
        )

        # Mettre à jour le dépôt avec la réponse SoleasPay
        deposit.payin_response = result
        deposit.payin_reference = result.get('reference', '') or result.get('payin_reference', '')
        deposit.external_reference = result.get('external_reference', '') or result.get('order_id', '')

        if result.get('success') or result.get('code') == 0:
            deposit.status = 'PAYMENT_PROCESSING'
            deposit.status_message = 'Paiement en cours...'
        else:
            deposit.status = 'FAILED'
            deposit.status_message = result.get('message', 'Échec du paiement')

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Dépôt créé, paiement en cours.',
            'deposit': deposit.to_dict(),
            'pay_result': result,
            'redirect': url_for('deposit_status', reference=reference),
        })

    except Exception as e:
        deposit.status = 'FAILED'
        deposit.status_message = str(e)[:500]
        db.session.commit()
        return jsonify({
            'success': False,
            'message': f'Erreur lors du paiement : {str(e)}',
            'deposit': deposit.to_dict(),
        }), 500


@app.route('/deposit/<reference>')
@login_required
def deposit_status(reference):
    """Page de statut après création du dépôt."""
    deposit = Deposit.query.filter_by(
        reference=reference, user_id=current_user.id
    ).first_or_404()
    return render_template('deposit_status.html',
                           user=current_user,
                           deposit=deposit)


@app.route('/api/deposit/status/<reference>')
@login_required
def api_deposit_status(reference):
    """API pour vérifier le statut d'un dépôt en temps réel."""
    deposit = Deposit.query.filter_by(
        reference=reference, user_id=current_user.id
    ).first()
    if not deposit:
        return jsonify({'success': False, 'message': 'Dépôt introuvable'}), 404

    return jsonify({
        'success': True,
        'deposit': deposit.to_dict(),
    })


# ==================== WEBHOOK DEPOSIT ====================

@app.route('/webhook/soleaspay/deposit', methods=['POST'])
def webhook_deposit():
    """Webhook pour les dépôts SoleasPay."""
    signature = request.headers.get('X-SoleasPay-Signature', '')
    raw_body = request.get_data()
    if not _verify_webhook_signature(raw_body, signature):
        webhook_logger.warning('Signature invalide — webhook dépôt rejeté')
        return jsonify({'success': False, 'message': 'Signature invalide'}), 403

    payload = request.get_json(silent=True) or {}
    if not payload:
        return jsonify({'success': False, 'message': 'Payload invalide'}), 400

    external_ref = payload.get('external_reference') or payload.get('order_id') or ''
    deposit = Deposit.query.filter_by(reference=external_ref).first()

    _log_webhook('DEPOSIT', external_ref, payload.get('status', 'UNKNOWN'), payload)

    if not deposit:
        webhook_logger.warning(f'Dépôt introuvable pour reference={external_ref}')
        return jsonify({'success': False, 'message': 'Dépôt introuvable'}), 404

    # Idempotence
    if deposit.status != 'PAYMENT_PROCESSING':
        return jsonify({
            'success': True,
            'message': f'Dépôt déjà traité (statut={deposit.status})',
        })

    # Traitement succès
    if is_payment_success(payload):
        deposit.webhook_payload = payload
        deposit.status = 'COMPLETED'
        deposit.status_message = 'Dépôt confirmé — portefeuille crédité.'

        # Créditer le solde de l'utilisateur
        deposit.user.balance = (deposit.user.balance or 0) + deposit.amount

        # Créer une transaction comptable
        tx = Transaction(
            user_id=deposit.user_id,
            type='deposit',
            amount=deposit.amount,
            currency=deposit.currency,
            fee=deposit.fees,
            status='success',
            recipient_name=deposit.user.fullname,
            recipient_phone=deposit.phone,
            recipient_country=deposit.country,
            recipient_operator=deposit.operator,
        )
        db.session.add(tx)
        db.session.commit()

        webhook_logger.info(f'Dépôt COMPLETED: {deposit.reference}, montant={deposit.amount}')
        return jsonify({'success': True, 'message': 'Dépôt confirmé', 'status': 'COMPLETED'})

    # Échec
    elif is_payment_failed(payload):
        deposit.webhook_payload = payload
        deposit.status = 'FAILED'
        deposit.status_message = payload.get('message', 'Échec du dépôt')
        db.session.commit()
        webhook_logger.info(f'Dépôt FAILED: {deposit.reference}')
        return jsonify({'success': False, 'message': 'Dépôt échoué', 'status': 'FAILED'})

    else:
        deposit.webhook_payload = payload
        db.session.commit()
        return jsonify({'success': True, 'message': 'Statut inconnu, payload enregistré'})


# ==================== BENEFICIARIES ====================

@app.route('/beneficiaries')
@login_required
def beneficiaries_page():
    """Page de gestion des bénéficiaires."""
    country_flags = {
        'TG': '🇹🇬', 'BJ': '🇧🇯', 'CM': '🇨🇲', 'CI': '🇨🇮', 'BF': '🇧🇫',
        'CG': '🇨🇬', 'CD': '🇨🇩', 'GA': '🇬🇦', 'UG': '🇺🇬', 'ZM': '🇿🇲', 'SN': '🇸🇳',
    }
    country_names = {
        'TG': 'Togo', 'BJ': 'Bénin', 'CM': 'Cameroun', 'CI': 'Côte d\'Ivoire',
        'BF': 'Burkina Faso', 'CG': 'Congo', 'CD': 'RD Congo', 'GA': 'Gabon',
        'UG': 'Ouganda', 'ZM': 'Zambie', 'SN': 'Sénégal',
    }
    # Liste des pays avec leurs opérateurs depuis transfer_config
    countries_list = [c for c in COUNTRIES]
    operators_list = {}
    for country in countries_list:
        code = country.get('code', '')
        ops = get_operators(code)
        operators_list[code] = ops

    return render_template('beneficiaries.html',
                           user=current_user,
                           country_names=country_names,
                           country_flags=country_flags,
                           countries=countries_list,
                           operators_list=operators_list)


@app.route('/beneficiary/<int:beneficiary_id>')
@login_required
def beneficiary_detail(beneficiary_id):
    """Page de détail/historique d'un bénéficiaire."""
    beneficiary = Beneficiary.query.filter_by(
        id=beneficiary_id, user_id=current_user.id
    ).first_or_404()

    # Transactions liées à ce bénéficiaire (par téléphone)
    transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'send',
        Transaction.recipient_phone == beneficiary.phone,
    ).order_by(Transaction.created_at.desc()).limit(50).all()

    country_flags = {
        'TG': '🇹🇬', 'BJ': '🇧🇯', 'CM': '🇨🇲', 'CI': '🇨🇮', 'BF': '🇧🇫',
        'CG': '🇨🇬', 'CD': '🇨🇩', 'GA': '🇬🇦', 'UG': '🇺🇬', 'ZM': '🇿🇲', 'SN': '🇸🇳',
    }
    country_names = {
        'TG': 'Togo', 'BJ': 'Bénin', 'CM': 'Cameroun', 'CI': 'Côte d\'Ivoire',
        'BF': 'Burkina Faso', 'CG': 'Congo', 'CD': 'RD Congo', 'GA': 'Gabon',
        'UG': 'Ouganda', 'ZM': 'Zambie', 'SN': 'Sénégal',
    }

    return render_template('beneficiary_detail.html',
                           user=current_user,
                           beneficiary=beneficiary,
                           transactions=transactions,
                           country_flags=country_flags,
                           country_names=country_names)


# --- API Bénéficiaires ---

@app.route('/api/beneficiaries')
@login_required
def api_get_beneficiaries():
    """Liste tous les bénéficiaires de l'utilisateur connecté."""
    beneficiaries = Beneficiary.query.filter_by(
        user_id=current_user.id
    ).order_by(Beneficiary.is_favorite.desc(), Beneficiary.created_at.desc()).all()

    return jsonify({
        'success': True,
        'beneficiaries': [b.to_dict() for b in beneficiaries],
        'total': len(beneficiaries),
    })


@app.route('/api/beneficiaries', methods=['POST'])
@login_required
def api_create_beneficiary():
    """Crée un nouveau bénéficiaire."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Données manquantes'}), 400

    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    country = data.get('country', '').strip().upper()

    if not name or not phone or not country:
        return jsonify({'success': False, 'message': 'Nom, numéro et pays requis'}), 400

    # Vérifier doublon (même numéro, même pays)
    existing = Beneficiary.query.filter_by(
        user_id=current_user.id,
        phone=phone,
        country=country,
    ).first()
    if existing:
        return jsonify({
            'success': False,
            'message': 'Ce numéro est déjà enregistré pour ce pays.',
        }), 400

    beneficiary = Beneficiary(
        user_id=current_user.id,
        name=name,
        phone=phone,
        country=country,
        operator=data.get('operator', '').strip().upper() or None,
        email=data.get('email') or None,
        nickname=data.get('nickname') or None,
        photo=data.get('photo') or None,
        is_favorite=data.get('is_favorite', False),
    )
    db.session.add(beneficiary)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Bénéficiaire ajouté !',
        'beneficiary': beneficiary.to_dict(),
    })


@app.route('/api/beneficiaries/<int:beneficiary_id>', methods=['PUT'])
@login_required
def api_update_beneficiary(beneficiary_id):
    """Modifie un bénéficiaire existant."""
    beneficiary = Beneficiary.query.filter_by(
        id=beneficiary_id, user_id=current_user.id
    ).first()

    if not beneficiary:
        return jsonify({'success': False, 'message': 'Bénéficiaire introuvable'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Données manquantes'}), 400

    beneficiary.name = data.get('name', beneficiary.name).strip()
    beneficiary.phone = data.get('phone', beneficiary.phone).strip()
    beneficiary.country = data.get('country', beneficiary.country).strip().upper()
    beneficiary.operator = data.get('operator', '').strip().upper() or None
    beneficiary.email = data.get('email') or None
    beneficiary.nickname = data.get('nickname') or None
    beneficiary.photo = data.get('photo') or None
    beneficiary.is_favorite = data.get('is_favorite', beneficiary.is_favorite)
    beneficiary.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Bénéficiaire modifié !',
        'beneficiary': beneficiary.to_dict(),
    })


@app.route('/api/beneficiaries/<int:beneficiary_id>', methods=['DELETE'])
@login_required
def api_delete_beneficiary(beneficiary_id):
    """Supprime un bénéficiaire."""
    beneficiary = Beneficiary.query.filter_by(
        id=beneficiary_id, user_id=current_user.id
    ).first()

    if not beneficiary:
        return jsonify({'success': False, 'message': 'Bénéficiaire introuvable'}), 404

    db.session.delete(beneficiary)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Bénéficiaire supprimé'})


@app.route('/api/beneficiaries/<int:beneficiary_id>/favorite', methods=['POST'])
@login_required
def api_toggle_favorite(beneficiary_id):
    """Bascule le statut favori d'un bénéficiaire."""
    beneficiary = Beneficiary.query.filter_by(
        id=beneficiary_id, user_id=current_user.id
    ).first()

    if not beneficiary:
        return jsonify({'success': False, 'message': 'Bénéficiaire introuvable'}), 404

    beneficiary.is_favorite = not beneficiary.is_favorite
    beneficiary.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'success': True,
        'is_favorite': beneficiary.is_favorite,
        'message': 'Ajouté aux favoris ⭐' if beneficiary.is_favorite else 'Retiré des favoris',
    })


@app.route('/api/beneficiaries/recent')
@login_required
def api_recent_contacts():
    """Retourne les 5 derniers destinataires uniques (même non enregistrés)."""
    recent = db.session.query(
        Transaction.recipient_name,
        Transaction.recipient_phone,
        Transaction.recipient_country,
        Transaction.recipient_operator,
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'send',
        Transaction.recipient_phone.isnot(None),
    ).order_by(
        db.func.max(Transaction.created_at).desc()
    ).group_by(
        Transaction.recipient_phone,
        Transaction.recipient_country,
    ).limit(5).all()

    contacts = []
    for r in recent:
        # Vérifier si déjà enregistré comme bénéficiaire
        already = Beneficiary.query.filter_by(
            user_id=current_user.id,
            phone=r.recipient_phone,
            country=r.recipient_country,
        ).first()
        contacts.append({
            'name': r.recipient_name or 'Inconnu',
            'phone': r.recipient_phone,
            'country': r.recipient_country,
            'operator': r.recipient_operator or '',
            'is_saved': already is not None,
        })

    return jsonify({
        'success': True,
        'contacts': contacts,
        'total': len(contacts),
    })


# --- API Contact Import (architecture future) ---
@app.route('/api/contacts/import', methods=['POST'])
@login_required
def api_import_contacts():
    """API d'import de contacts (CSV / JSON).
    Architecture réservée pour intégration Android/iOS ultérieure.
    """
    # Placeholder — à implémenter plus tard
    return jsonify({
        'success': False,
        'message': 'Import de contacts non encore implémenté.',
    }), 501


# ==================== PAGE 404 ====================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
