import os
import logging
import hmac
import hashlib
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from models import db, User, Transfer, Deposit, Beneficiary, Transaction, OtpCode
from services.sms_service import send_sms, format_phone as format_sms_phone
from services.otp_service import create_otp, verify_otp, resend_otp as resend_otp_service
from beneficiary_utils import detect_country_from_phone, detect_operator_from_phone, detect_from_phone
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
from services.fees import calculate_fee as calculate_fee_service

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

# --- LOGIN (avec OTP téléphone) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        data = request.get_json()
        phone = data.get('phone', '').strip()
        password = data.get('password', '')

        phone_clean = format_sms_phone(phone)
        user = User.query.filter_by(phone=phone_clean).first()

        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({'success': False, 'message': 'Téléphone ou mot de passe incorrect.'}), 401

        otp_result = create_otp(phone_clean, 'login')
        if not otp_result.get('success'):
            return jsonify({'success': False, 'message': otp_result.get('error', 'Erreur OTP.')}), 429

        code = otp_result['code']
        sms_message = (
            f"TransAfrik\n"
            f"Votre code de verification est :\n"
            f"{code}\n\n"
            f"Ce code expire dans 5 minutes.\n"
            f"Ne le partagez avec personne."
        )
        sms_result = send_sms(phone_clean, sms_message)

        session['pending_login_user_id'] = user.id
        session['pending_phone'] = phone_clean

        app.logger.info(
            f"OTP login créé pour {phone_clean} | "
            f"sms_sent={sms_result.get('success', False)}"
        )

        return jsonify({
            'success': True,
            'message': 'Un code de vérification a été envoyé par SMS.',
            'redirect': url_for('verify_otp_page', purpose='login'),
        })

    return render_template('connexion.html')


# --- REGISTER (OTP avant création du compte) ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        fullname = data.get('fullname', '').strip()
        phone = data.get('phone', '').strip()
        country = data.get('country', '').strip().upper()
        password = data.get('password', '')

        errors = []
        if not fullname or len(fullname) < 2:
            errors.append('Nom complet requis (minimum 2 caractères).')
        if not email or '@' not in email:
            errors.append('Adresse e-mail invalide.')
        if User.query.filter_by(email=email).first():
            errors.append('Cet e-mail est déjà utilisé.')
        if not phone or len(phone.replace(' ', '').replace('+', '').replace('-', '')) < 8:
            errors.append('Numéro de téléphone invalide.')

        phone_clean = format_sms_phone(phone)
        if User.query.filter_by(phone=phone_clean).first():
            errors.append('Ce numéro de téléphone est déjà utilisé.')
        if country not in ['TG','BJ','CM','CI','BF','CG','CD','GA','UG','ZM','SN']:
            errors.append('Pays invalide.')
        if len(password) < 8:
            errors.append('Le mot de passe doit contenir au moins 8 caractères.')

        if errors:
            return jsonify({'success': False, 'message': errors[0], 'errors': errors}), 400

        otp_result = create_otp(phone_clean, 'register')
        if not otp_result.get('success'):
            return jsonify({'success': False, 'message': otp_result.get('error', 'Erreur OTP.')}), 429

        code = otp_result['code']
        sms_message = (
            f"TransAfrik\n"
            f"Votre code de verification est :\n"
            f"{code}\n\n"
            f"Ce code expire dans 5 minutes.\n"
            f"Ne le partagez avec personne."
        )
        send_sms(phone_clean, sms_message)

        session['pending_register'] = {
            'email': email,
            'fullname': fullname,
            'phone': phone_clean,
            'country': country,
            'password': password,
        }

        return jsonify({
            'success': True,
            'message': 'Un code de vérification a été envoyé par SMS.',
            'redirect': url_for('verify_otp_page', purpose='register'),
        })

    return render_template('inscription.html')


# --- VERIFY OTP ---
@app.route('/verify-otp/<purpose>', methods=['GET', 'POST'])
def verify_otp_page(purpose='login'):
    if purpose not in ('register', 'login', 'reset_password', 'change_phone'):
        flash('Type de vérification invalide.', 'error')
        return redirect(url_for('index'))

    phone = session.get('pending_phone', '')
    if not phone:
        pending = session.get('pending_register', {})
        phone = pending.get('phone', '')
        if not phone:
            flash('Session expirée. Veuillez recommencer.', 'warning')
            return redirect(url_for('login'))

    if request.method == 'POST':
        data = request.get_json()
        code = data.get('code', '').strip()

        if not code or len(code) != 6:
            return jsonify({'success': False, 'message': 'Le code doit contenir 6 chiffres.'}), 400

        result = verify_otp(phone, code, purpose)
        if not result.get('success'):
            return jsonify({'success': False, 'message': result.get('error', 'Code invalide.')}), 400

        if purpose == 'register':
            pending = session.get('pending_register', {})
            if not pending:
                return jsonify({'success': False, 'message': 'Session expirée.'}), 400

            user = User(
                fullname=pending['fullname'],
                email=pending['email'],
                phone=pending['phone'],
                country=pending['country'],
                password_hash=generate_password_hash(pending['password']),
            )
            db.session.add(user)
            db.session.commit()

            session.pop('pending_register', None)
            session.pop('pending_phone', None)
            login_user(user)

            app.logger.info(f"Nouveau compte créé via OTP : {user.email}")
            return jsonify({
                'success': True,
                'message': 'Compte créé avec succès !',
                'redirect': url_for('dashboard'),
            })

        elif purpose == 'login':
            user_id = session.get('pending_login_user_id')
            if not user_id:
                return jsonify({'success': False, 'message': 'Session expirée.'}), 400

            user = db.session.get(User, user_id)
            if not user:
                return jsonify({'success': False, 'message': 'Utilisateur introuvable.'}), 404

            session.pop('pending_login_user_id', None)
            session.pop('pending_phone', None)
            login_user(user)

            app.logger.info(f"Connexion OTP réussie : {user.email}")
            return jsonify({
                'success': True,
                'message': 'Connexion réussie !',
                'redirect': url_for('dashboard'),
            })

        elif purpose == 'reset_password':
            session['otp_verified_for_reset'] = True
            return jsonify({
                'success': True,
                'message': 'Code vérifié. Choisissez un nouveau mot de passe.',
                'redirect': url_for('reset_password'),
            })

    return render_template('verify_otp.html', purpose=purpose, phone=phone)


# --- RESEND OTP ---
@app.route('/api/otp/resend', methods=['POST'])
def api_resend_otp():
    data = request.get_json()
    phone = data.get('phone', '').strip()

    if not phone:
        phone = session.get('pending_phone', '')
        if not phone:
            pending = session.get('pending_register', {})
            phone = pending.get('phone', '')

    if not phone:
        return jsonify({'success': False, 'message': 'Aucun numéro trouvé.'}), 400

    phone_clean = format_sms_phone(phone)
    otp_result = resend_otp_service(phone_clean)

    if not otp_result.get('success'):
        return jsonify({'success': False, 'message': otp_result.get('error', 'Erreur OTP.')}), 429

    code = otp_result['code']
    sms_message = (
        f"TransAfrik\n"
        f"Votre code de verification est :\n"
        f"{code}\n\n"
        f"Ce code expire dans 5 minutes.\n"
        f"Ne le partagez avec personne."
    )
    send_sms(phone_clean, sms_message)
    app.logger.info(f"OTP renvoyé à {phone_clean}")

    return jsonify({'success': True, 'message': 'Nouveau code envoyé par SMS.'})


# --- FORGOT PASSWORD ---
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        data = request.get_json()
        phone = data.get('phone', '').strip()
        if not phone:
            return jsonify({'success': False, 'message': 'Numéro de téléphone requis.'}), 400

        phone_clean = format_sms_phone(phone)
        user = User.query.filter_by(phone=phone_clean).first()
        if not user:
            return jsonify({
                'success': True,
                'message': 'Si ce numéro est associé à un compte, un code vous sera envoyé.',
            })

        otp_result = create_otp(phone_clean, 'reset_password')
        if not otp_result.get('success'):
            return jsonify({'success': False, 'message': otp_result.get('error', 'Erreur OTP.')}), 429

        code = otp_result['code']
        sms_message = (
            f"TransAfrik\n"
            f"Votre code de reinitialisation est :\n"
            f"{code}\n\n"
            f"Ce code expire dans 5 minutes.\n"
            f"Ne le partagez avec personne."
        )
        send_sms(phone_clean, sms_message)

        session['pending_phone'] = phone_clean
        session['pending_reset_user_id'] = user.id

        return jsonify({
            'success': True,
            'message': 'Un code de réinitialisation a été envoyé par SMS.',
            'redirect': url_for('verify_otp_page', purpose='reset_password'),
        })

    return render_template('connexion.html', forgot_password=True)


# --- RESET PASSWORD ---
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if not session.get('otp_verified_for_reset'):
        flash('Veuillez d\'abord vérifier votre identité.', 'warning')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        data = request.get_json()
        new_password = data.get('password', '')
        if len(new_password) < 8:
            return jsonify({
                'success': False,
                'message': 'Le mot de passe doit contenir au moins 8 caractères.',
            }), 400

        user_id = session.get('pending_reset_user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'Session expirée.'}), 400

        user = db.session.get(User, user_id)
        if not user:
            return jsonify({'success': False, 'message': 'Utilisateur introuvable.'}), 404

        user.password_hash = generate_password_hash(new_password)
        db.session.commit()

        session.pop('otp_verified_for_reset', None)
        session.pop('pending_reset_user_id', None)
        session.pop('pending_phone', None)

        app.logger.info(f"Mot de passe réinitialisé pour {user.email}")
        return jsonify({
            'success': True,
            'message': 'Mot de passe mis à jour. Connectez-vous.',
            'redirect': url_for('login'),
        })

    return render_template('reset_password.html')


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

        amount = int(data.get('amount', 0))
        sender_country = data.get('sender_country', '').upper()
        sender_operator = data.get('sender_operator', '').lower()
        sender_number = data.get('sender_number', '').strip()
        receiver_country = data.get('receiver_country', '').upper()
        receiver_operator = data.get('receiver_operator', '').lower()
        receiver_number = data.get('receiver_number', '').strip()
        receiver_name = data.get('receiver_name', '').strip()
        currency = data.get('currency', 'XOF')

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

        fees = calculate_fees(amount)
        total_amount = calculate_total(amount)

        def clean_phone(num):
            return num.replace('+', '').replace(' ', '').replace('-', '').strip()

        sender_number = clean_phone(sender_number)
        receiver_number = clean_phone(receiver_number)

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

        pay_result = start_payment(transfer)
        db.session.refresh(transfer)

        return jsonify({
            'success': True,
            'message': 'Transaction créée et paiement lancé.',
            'transfer': transfer.to_dict(),
            'pay_result': pay_result,
            'redirect': url_for('send_money_confirm', ref=transfer.reference),
        })

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
    tx_count = user.tx_count
    beneficiary_count = user.beneficiary_count
    total_sent = user.total_sent
    total_received = user.total_received
    unread_notifications = user.unread_notifications
    recent_txs = user.recent_transactions(limit=5)

    country_flags = {
        'TG': '\U0001f1f9\U0001f1ec', 'BJ': '\U0001f1e7\U0001f1ef', 'CM': '\U0001f1e8\U0001f1f2',
        'CI': '\U0001f1e8\U0001f1ee', 'BF': '\U0001f1e7\U0001f1eb', 'CG': '\U0001f1e8\U0001f1ec',
        'CD': '\U0001f1e8\U0001f1e9', 'GA': '\U0001f1ec\U0001f1e6', 'UG': '\U0001f1fa\U0001f1ec',
        'ZM': '\U0001f1ff\U0001f1f2', 'SN': '\U0001f1f8\U0001f1f3',
    }
    country_names = {
        'TG': 'Togo', 'BJ': 'B\u00e9nin', 'CM': 'Cameroun', 'CI': 'C\u00f4te d\'Ivoire',
        'BF': 'Burkina Faso', 'CG': 'Congo', 'CD': 'RD Congo', 'GA': 'Gabon',
        'UG': 'Ouganda', 'ZM': 'Zambie', 'SN': 'S\u00e9n\u00e9gal',
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

os.makedirs('logs', exist_ok=True)

webhook_logger = logging.getLogger('webhook')
webhook_logger.setLevel(logging.INFO)
fh = logging.FileHandler('logs/payment.log', encoding='utf-8')
fh.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
webhook_logger.addHandler(fh)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter('[%(asctime)s] WEBHOOK | %(message)s'))
webhook_logger.addHandler(ch)

SOLEAS_WEBHOOK_SECRET = os.getenv('SOLEAS_WEBHOOK_SECRET', '')


def _verify_webhook_signature(payload_body: bytes, signature_header: str) -> bool:
    if not SOLEAS_WEBHOOK_SECRET:
        webhook_logger.warning('SOLEAS_WEBHOOK_SECRET non configuré — signature ignorée')
        return True
    if not signature_header:
        webhook_logger.warning('Signature manquante dans le header')
        return False
    computed = hmac.new(SOLEAS_WEBHOOK_SECRET.encode('utf-8'), payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature_header)


def _log_webhook(webhook_type: str, reference: str, status: str, payload: dict):
    ip = request.remote_addr or 'unknown'
    webhook_logger.info(f"Type={webhook_type} | Reference={reference} | Status={status} | IP={ip} | Payload={payload}")


# ==================== WEBHOOKS SOLEASPAY ====================

@app.route('/webhook/soleaspay/payment', methods=['POST'])
def webhook_payment():
    signature = request.headers.get('X-SoleasPay-Signature', '')
    raw_body = request.get_data()
    if not _verify_webhook_signature(raw_body, signature):
        webhook_logger.warning('Signature invalide — webhook rejeté')
        return jsonify({'success': False, 'message': 'Signature invalide'}), 403

    payload = request.get_json(silent=True) or {}
    if not payload:
        return jsonify({'success': False, 'message': 'Payload invalide'}), 400

    external_ref = payload.get('external_reference') or payload.get('order_id') or ''
    transfer = get_transfer_by_reference(external_ref) if external_ref else None
    _log_webhook('PAYMENT', external_ref, payload.get('status', 'UNKNOWN'), payload)

    if not transfer:
        webhook_logger.warning(f'Transfer introuvable pour external_reference={external_ref}')
        return jsonify({'success': False, 'message': 'Transfer introuvable'}), 404

    if transfer.status not in ('PAYMENT_PROCESSING', 'WAITING_PAYMENT'):
        webhook_logger.info(f'Webhook ignoré (idempotent) : transfert déjà au statut {transfer.status}')
        return jsonify({
            'success': True,
            'message': f'Transfert déjà traité (statut={transfer.status})',
            'reference': transfer.reference,
            'status': transfer.status,
        })

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
        transfer.webhook_payload = payload
        db.session.commit()
        webhook_logger.warning(f'Statut Pay-In inconnu pour {transfer.reference}: {payload.get("status")}')
        return jsonify({
            'success': True,
            'message': 'Statut inconnu, payload enregistré',
            'reference': transfer.reference,
        })


@app.route('/webhook/soleaspay/withdraw', methods=['POST'])
def webhook_withdraw():
    signature = request.headers.get('X-SoleasPay-Signature', '')
    raw_body = request.get_data()
    if not _verify_webhook_signature(raw_body, signature):
        webhook_logger.warning('Signature invalide — webhook rejeté')
        return jsonify({'success': False, 'message': 'Signature invalide'}), 403

    payload = request.get_json(silent=True) or {}
    if not payload:
        return jsonify({'success': False, 'message': 'Payload invalide'}), 400

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

    if transfer.status != 'WITHDRAW_PROCESSING':
        webhook_logger.info(f'Webhook ignoré (idempotent) : transfert déjà au statut {transfer.status}')
        return jsonify({
            'success': True,
            'message': f'Transfert déjà traité (statut={transfer.status})',
            'reference': transfer.reference,
            'status': transfer.status,
        })

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
        handle_withdraw_failed(transfer, reason=payload.get('message', 'Échec du retrait'), webhook_payload=payload)
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
    page = request.args.get('page', 1, type=int)
    per_page = 20
    filter_status = request.args.get('status', 'ALL')
    search = request.args.get('search', '').strip()

    query = Transfer.query.filter_by(sender_user_id=current_user.id)

    if filter_status and filter_status != 'ALL':
        if filter_status == 'PENDING':
            query = query.filter(Transfer.status.in_(['CREATED', 'WAITING_PAYMENT', 'PAYMENT_PROCESSING', 'PAYMENT_SUCCESS', 'WITHDRAW_PROCESSING']))
        elif filter_status == 'COMPLETED':
            query = query.filter_by(status='COMPLETED')
        elif filter_status == 'FAILED':
            query = query.filter_by(status='FAILED')
        elif filter_status == 'CANCELLED':
            query = query.filter_by(status='CANCELLED')
        else:
            query = query.filter_by(status=filter_status)

    if search:
        search_term = f'%{search}%'
        query = query.filter(db.or_(
            Transfer.reference.ilike(search_term),
            Transfer.receiver_phone.ilike(search_term),
            Transfer.receiver_name.ilike(search_term),
            Transfer.sender_phone.ilike(search_term),
        ))

    pagination = query.order_by(Transfer.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    country_names = {
        'TG': 'Togo', 'BJ': 'B\u00e9nin', 'CM': 'Cameroun', 'CI': 'C\u00f4te d\'Ivoire',
        'BF': 'Burkina Faso', 'CG': 'Congo', 'CD': 'RD Congo', 'GA': 'Gabon',
        'UG': 'Ouganda', 'ZM': 'Zambie', 'SN': 'S\u00e9n\u00e9gal',
    }
    country_flags = {
        'TG': '\U0001f1f9\U0001f1ec', 'BJ': '\U0001f1e7\U0001f1ef', 'CM': '\U0001f1e8\U0001f1f2',
        'CI': '\U0001f1e8\U0001f1ee', 'BF': '\U0001f1e7\U0001f1eb', 'CG': '\U0001f1e8\U0001f1ec',
        'CD': '\U0001f1e8\U0001f1e9', 'GA': '\U0001f1ec\U0001f1e6', 'UG': '\U0001f1fa\U0001f1ec',
        'ZM': '\U0001f1ff\U0001f1f2', 'SN': '\U0001f1f8\U0001f1f3',
    }

    transfers_data = []
    for t in pagination.items:
        d = t.to_dict()
        d['receiver_country_name'] = country_names.get(t.receiver_country, t.receiver_country)
        d['receiver_country_flag'] = country_flags.get(t.receiver_country, '\U0001f30d')
        d['sender_country_name'] = country_names.get(t.sender_country, t.sender_country)
        d['sender_country_flag'] = country_flags.get(t.sender_country, '\U0001f30d')
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
    return render_template('deposit.html', user=current_user, countries=DEPOSIT_COUNTRIES)


@app.route('/api/deposit/operators/<country_code>')
@login_required
def api_deposit_operators(country_code):
    operators = get_deposit_operators_for_country(country_code.upper())
    return jsonify({'success': True, 'operators': operators})


@app.route('/api/deposit', methods=['POST'])
@login_required
def api_create_deposit():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Données manquantes'}), 400

    amount = int(data.get('amount', 0))
    phone = data.get('phone', '').strip()
    country = data.get('country', '').strip().upper()
    operator_slug = data.get('operator', '').strip().lower()
    operator_id = data.get('operator_id', 0)

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

    phone_clean = phone.replace('+', '').replace(' ', '').replace('-', '').strip()
    fees_data = calculate_deposit_fees(amount, currency='XOF')
    total_amount = fees_data['total']
    fees = fees_data['fees']

    from config.operators import get_operator_by_id
    op_info = get_operator_by_id(operator_id)
    currency = op_info.get('currency', 'XOF') if op_info else 'XOF'
    operator_name = op_info.get('name', operator_slug.upper()) if op_info else operator_slug.upper()

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
    deposit = Deposit.query.filter_by(reference=reference, user_id=current_user.id).first_or_404()
    return render_template('deposit_status.html', user=current_user, deposit=deposit)


@app.route('/api/deposit/status/<reference>')
@login_required
def api_deposit_status(reference):
    deposit = Deposit.query.filter_by(reference=reference, user_id=current_user.id).first()
    if not deposit:
        return jsonify({'success': False, 'message': 'Dépôt introuvable'}), 404
    return jsonify({'success': True, 'deposit': deposit.to_dict()})


@app.route('/webhook/soleaspay/deposit', methods=['POST'])
def webhook_deposit():
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

    if deposit.status != 'PAYMENT_PROCESSING':
        return jsonify({'success': True, 'message': f'Dépôt déjà traité (statut={deposit.status})'})

    if is_payment_success(payload):
        deposit.webhook_payload = payload
        deposit.status = 'COMPLETED'
        deposit.status_message = 'Dépôt confirmé — portefeuille crédité.'
        deposit.user.balance = (deposit.user.balance or 0) + deposit.amount
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
    country_flags = {
        'TG': '\U0001f1f9\U0001f1ec', 'BJ': '\U0001f1e7\U0001f1ef', 'CM': '\U0001f1e8\U0001f1f2',
        'CI': '\U0001f1e8\U0001f1ee', 'BF': '\U0001f1e7\U0001f1eb', 'CG': '\U0001f1e8\U0001f1ec',
        'CD': '\U0001f1e8\U0001f1e9', 'GA': '\U0001f1ec\U0001f1e6', 'UG': '\U0001f1fa\U0001f1ec',
        'ZM': '\U0001f1ff\U0001f1f2', 'SN': '\U0001f1f8\U0001f1f3',
    }
    country_names = {
        'TG': 'Togo', 'BJ': 'B\u00e9nin', 'CM': 'Cameroun', 'CI': 'C\u00f4te d\'Ivoire',
        'BF': 'Burkina Faso', 'CG': 'Congo', 'CD': 'RD Congo', 'GA': 'Gabon',
        'UG': 'Ouganda', 'ZM': 'Zambie', 'SN': 'S\u00e9n\u00e9gal',
    }
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
    beneficiary = Beneficiary.query.filter_by(id=beneficiary_id, user_id=current_user.id).first_or_404()
    transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'send',
        Transaction.recipient_phone == beneficiary.phone,
    ).order_by(Transaction.created_at.desc()).limit(50).all()

    country_flags = {
        'TG': '\U0001f1f9\U0001f1ec', 'BJ': '\U0001f1e7\U0001f1ef', 'CM': '\U0001f1e8\U0001f1f2',
        'CI': '\U0001f1e8\U0001f1ee', 'BF': '\U0001f1e7\U0001f1eb', 'CG': '\U0001f1e8\U0001f1ec',
        'CD': '\U0001f1e8\U0001f1e9', 'GA': '\U0001f1ec\U0001f1e6', 'UG': '\U0001f1fa\U0001f1ec',
        'ZM': '\U0001f1ff\U0001f1f2', 'SN': '\U0001f1f8\U0001f1f3',
    }
    country_names = {
        'TG': 'Togo', 'BJ': 'B\u00e9nin', 'CM': 'Cameroun', 'CI': 'C\u00f4te d\'Ivoire',
        'BF': 'Burkina Faso', 'CG': 'Congo', 'CD': 'RD Congo', 'GA': 'Gabon',
        'UG': 'Ouganda', 'ZM': 'Zambie', 'SN': 'S\u00e9n\u00e9gal',
    }

    return render_template('beneficiary_detail.html',
                           user=current_user,
                           beneficiary=beneficiary,
                           transactions=transactions,
                           country_flags=country_flags,
                           country_names=country_names)


@app.route('/api/beneficiaries')
@login_required
def api_get_beneficiaries():
    beneficiaries = Beneficiary.query.filter_by(user_id=current_user.id).order_by(
        Beneficiary.is_favorite.desc(), Beneficiary.created_at.desc()
    ).all()
    return jsonify({'success': True, 'beneficiaries': [b.to_dict() for b in beneficiaries], 'total': len(beneficiaries)})


@app.route('/api/beneficiaries', methods=['POST'])
@login_required
def api_create_beneficiary():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Données manquantes'}), 400

    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    country = data.get('country', '').strip().upper()

    if not name or not phone or not country:
        return jsonify({'success': False, 'message': 'Nom, numéro et pays requis'}), 400

    existing = Beneficiary.query.filter_by(user_id=current_user.id, phone=phone, country=country).first()
    if existing:
        return jsonify({'success': False, 'message': 'Ce numéro est déjà enregistré pour ce pays.'}), 400

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
    return jsonify({'success': True, 'message': 'Bénéficiaire ajouté !', 'beneficiary': beneficiary.to_dict()})


@app.route('/api/beneficiaries/<int:beneficiary_id>', methods=['PUT'])
@login_required
def api_update_beneficiary(beneficiary_id):
    beneficiary = Beneficiary.query.filter_by(id=beneficiary_id, user_id=current_user.id).first()
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
    return jsonify({'success': True, 'message': 'Bénéficiaire modifié !', 'beneficiary': beneficiary.to_dict()})


@app.route('/api/beneficiaries/<int:beneficiary_id>', methods=['DELETE'])
@login_required
def api_delete_beneficiary(beneficiary_id):
    beneficiary = Beneficiary.query.filter_by(id=beneficiary_id, user_id=current_user.id).first()
    if not beneficiary:
        return jsonify({'success': False, 'message': 'Bénéficiaire introuvable'}), 404
    db.session.delete(beneficiary)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Bénéficiaire supprimé'})


@app.route('/api/beneficiaries/<int:beneficiary_id>/favorite', methods=['POST'])
@login_required
def api_toggle_favorite(beneficiary_id):
    beneficiary = Beneficiary.query.filter_by(id=beneficiary_id, user_id=current_user.id).first()
    if not beneficiary:
        return jsonify({'success': False, 'message': 'Bénéficiaire introuvable'}), 404
    beneficiary.is_favorite = not beneficiary.is_favorite
    beneficiary.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({
        'success': True,
        'is_favorite': beneficiary.is_favorite,
        'message': 'Ajouté aux favoris' if beneficiary.is_favorite else 'Retiré des favoris',
    })


@app.route('/api/beneficiaries/recent')
@login_required
def api_recent_contacts():
    subq = db.session.query(
        Transaction.recipient_phone,
        Transaction.recipient_country,
        db.func.max(Transaction.created_at).label('max_ts')
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'send',
        Transaction.recipient_phone.isnot(None),
    ).group_by(Transaction.recipient_phone, Transaction.recipient_country).subquery()

    recent = db.session.query(Transaction).join(
        subq,
        db.and_(
            Transaction.recipient_phone == subq.c.recipient_phone,
            Transaction.recipient_country == subq.c.recipient_country,
            Transaction.created_at == subq.c.max_ts,
        )
    ).filter(Transaction.user_id == current_user.id).order_by(subq.c.max_ts.desc()).limit(5).all()

    contacts = []
    for tx in recent:
        already = Beneficiary.query.filter_by(user_id=current_user.id, phone=tx.recipient_phone, country=tx.recipient_country).first()
        contacts.append({
            'name': tx.recipient_name or 'Inconnu',
            'phone': tx.recipient_phone,
            'country': tx.recipient_country,
            'operator': tx.recipient_operator or '',
            'is_saved': already is not None,
        })

    return jsonify({'success': True, 'contacts': contacts, 'total': len(contacts)})


@app.route('/api/contacts/import', methods=['POST'])
@login_required
def api_import_contacts():
    data = request.get_json()
    if not data or not isinstance(data.get('contacts'), list):
        return jsonify({'success': False, 'message': 'Format invalide. Attendu: {"contacts": [...]}'}), 400

    contacts = data['contacts']
    imported = 0
    skipped = 0
    saved = []

    for c in contacts:
        name = (c.get('name') or '').strip()
        phone = (c.get('phone') or c.get('tel') or '').strip()
        if not name or not phone:
            skipped += 1
            continue

        phone = phone.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        country = (c.get('country') or '').strip().upper()
        if not country:
            country = detect_country_from_phone(phone)
        if not country:
            country = current_user.country

        existing = Beneficiary.query.filter_by(user_id=current_user.id, phone=phone, country=country).first()
        if existing:
            skipped += 1
            continue

        operator = (c.get('operator') or '').strip().upper() or None
        beneficiary = Beneficiary(
            user_id=current_user.id,
            name=name,
            phone=phone,
            country=country,
            operator=operator,
            nickname=c.get('nickname') or None,
            photo=c.get('photo') or None,
        )
        db.session.add(beneficiary)
        saved.append(beneficiary)
        imported += 1

    if saved:
        db.session.commit()

    return jsonify({
        'success': True,
        'message': f'{imported} contact(s) importé(s), {skipped} ignoré(s).',
        'imported': imported,
        'skipped': skipped,
        'beneficiaries': [b.to_dict() for b in saved],
    })


@app.route('/api/contacts/detect', methods=['POST'])
@login_required
def api_detect_phone():
    data = request.get_json()
    if not data or not data.get('phone'):
        return jsonify({'success': False, 'message': 'Numéro requis'}), 400
    phone = data['phone'].strip()
    detection = detect_from_phone(phone)
    return jsonify({'success': True, **detection})


@app.route('/api/contacts/sync', methods=['POST'])
@login_required
def api_sync_contacts():
    data = request.get_json()
    if not data or not isinstance(data.get('contacts'), list):
        return jsonify({'success': False, 'message': 'Format invalide'}), 400

    contacts = data['contacts']
    imported = 0
    updated = 0
    skipped = 0
    saved = []

    for c in contacts:
        name = (c.get('name') or '').strip()
        phone = (c.get('phone') or c.get('tel') or '').strip()
        if not name or not phone:
            skipped += 1
            continue

        phone = phone.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        country = (c.get('country') or '').strip().upper()
        if not country:
            country = detect_country_from_phone(phone)
        if not country:
            country = current_user.country

        operator = (c.get('operator') or '').strip().upper() or None
        if not operator:
            op_detection = detect_operator_from_phone(phone, country)
            if op_detection:
                operator = op_detection['name'].upper()

        existing = Beneficiary.query.filter_by(user_id=current_user.id, phone=phone, country=country).first()
        if existing:
            if existing.name != name and name:
                existing.name = name
            if operator and not existing.operator:
                existing.operator = operator
            existing.updated_at = datetime.utcnow()
            updated += 1
        else:
            beneficiary = Beneficiary(
                user_id=current_user.id,
                name=name,
                phone=phone,
                country=country,
                operator=operator,
                nickname=c.get('nickname') or None,
                photo=c.get('photo') or None,
            )
            db.session.add(beneficiary)
            saved.append(beneficiary)
            imported += 1

    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'{imported} nouveau(x), {updated} mis à jour, {skipped} ignoré(s).',
        'imported': imported,
        'updated': updated,
        'skipped': skipped,
        'beneficiaries': [b.to_dict() for b in saved],
    })


@app.route('/api/beneficiaries/stats')
@login_required
def api_beneficiary_stats():
    all_benefs = Beneficiary.query.filter_by(user_id=current_user.id)
    total = all_benefs.count()
    favorites = all_benefs.filter(Beneficiary.is_favorite == True).count()
    last_imported = Beneficiary.query.filter_by(user_id=current_user.id).order_by(Beneficiary.created_at.desc()).first()
    last_import_date = last_imported.created_at.isoformat() if last_imported and last_imported.created_at else None
    imported_count = all_benefs.filter(Beneficiary.photo.isnot(None)).count()
    if imported_count == 0:
        imported_count = total
    return jsonify({'success': True, 'total': total, 'favorites': favorites, 'imported': imported_count, 'last_import': last_import_date})


# ==================== FEES CALCULATOR ====================

@app.route('/fees-calculator')
@login_required
def fees_calculator():
    countries_data = {}
    for c in COUNTRIES:
        countries_data[c['code']] = {
            'currency': c.get('currency', 'XOF'),
            'name': c.get('name', ''),
            'flag': c.get('flag', ''),
            'operators': [{'id': op['id'], 'name': op['name']} for op in c.get('operators', [])],
        }

    country_flags = {
        'TG': '\U0001f1f9\U0001f1ec', 'BJ': '\U0001f1e7\U0001f1ef', 'CM': '\U0001f1e8\U0001f1f2',
        'CI': '\U0001f1e8\U0001f1ee', 'BF': '\U0001f1e7\U0001f1eb', 'CG': '\U0001f1e8\U0001f1ec',
        'CD': '\U0001f1e8\U0001f1e9', 'GA': '\U0001f1ec\U0001f1e6', 'UG': '\U0001f1fa\U0001f1ec',
        'ZM': '\U0001f1ff\U0001f1f2', 'SN': '\U0001f1f8\U0001f1f3',
    }
    country_names = {
        'TG': 'Togo', 'BJ': 'B\u00e9nin', 'CM': 'Cameroun', 'CI': 'C\u00f4te d\'Ivoire',
        'BF': 'Burkina Faso', 'CG': 'Congo', 'CD': 'RD Congo', 'GA': 'Gabon',
        'UG': 'Ouganda', 'ZM': 'Zambie', 'SN': 'S\u00e9n\u00e9gal',
    }

    return render_template('fees_calculator.html',
                           user=current_user,
                           countries=COUNTRIES,
                           countries_data=countries_data,
                           country_flags=country_flags,
                           country_names=country_names)


@app.route('/api/fees/calculate', methods=['POST'])
@login_required
def api_calculate_fees_v2():
    data = request.get_json(silent=True) or {}
    amount = int(data.get('amount', 0))
    if amount <= 0:
        return jsonify({'success': True, 'result': {'amount': 0, 'fees': 0, 'receiver_gets': 0, 'total': 0, 'estimated_time': 0, 'promo_message': '', 'tier_discount': 0}})

    result = calculate_fee_service(
        amount=amount,
        sender_country=data.get('sender_country', current_user.country).upper(),
        sender_operator=data.get('sender_operator', '').lower(),
        receiver_country=data.get('receiver_country', '').upper(),
        receiver_operator=data.get('receiver_operator', '').lower(),
        promo_code=data.get('promo_code') or None,
        user_tier=getattr(current_user, 'tier', 'standard'),
        user_id=current_user.id if current_user.is_authenticated else None,
    )
    return jsonify({'success': True, 'result': result})


# ==================== SCANNER QR CODE ====================

@app.route('/scan')
@login_required
def scan_page():
    return render_template('scan_qr.html', user=current_user)


@app.route('/my-qrcode')
@login_required
def my_qrcode_page():
    return render_template('my_qrcode.html', user=current_user)


@app.route('/qr-history')
@login_required
def qr_history_page():
    return render_template('qr_history.html', user=current_user)


@app.route('/api/qrcode/my')
@login_required
def api_qrcode_my():
    from services.qrcode_service import generate_user_qrcode, generate_qr_identifier
    from config.operators import get_country_info

    user = current_user
    if not user.qr_identifier:
        user.qr_identifier = generate_qr_identifier()
        db.session.commit()

    try:
        qr_json, qr_image_b64 = generate_user_qrcode(user)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

    country_info = get_country_info(user.country)
    flag = country_info.get('flag', '') if country_info else ''
    country_name = country_info.get('name', user.country) if country_info else user.country

    return jsonify({
        'success': True,
        'qr_image': qr_image_b64,
        'qr_json': qr_json,
        'user': {
            'name': user.fullname,
            'phone': user.phone,
            'country': user.country,
            'flag': flag,
            'country_name': country_name,
            'qr_id': user.qr_identifier,
        }
    })


@app.route('/api/qrcode/validate', methods=['POST'])
@login_required
def api_qrcode_validate():
    from services.qrcode_service import validate_qrcode, get_qr_action, find_user_by_qr_identifier, decode_qrcode
    from config.operators import get_country_info

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Données manquantes'}), 400

    qr_raw = data.get('data') or data.get('qr_identifier') or ''
    if not qr_raw:
        return jsonify({'success': False, 'error': 'Aucune donnée QR fournie'}), 400

    is_valid = False
    parsed = None
    error = None

    parsed_candidate = decode_qrcode(qr_raw)
    if parsed_candidate and parsed_candidate.get('type') in ('transafrik_user', 'transafrik_merchant', 'transafrik_deposit', 'transafrik_withdraw', 'transafrik_invoice'):
        is_valid, parsed, error = validate_qrcode(qr_raw)

    target_user = None
    if not is_valid:
        target_user = find_user_by_qr_identifier(qr_raw)
        if not target_user:
            return jsonify({'success': False, 'error': error or 'Aucun utilisateur trouvé pour cet identifiant QR.'})

        country_info = get_country_info(target_user.country) or {}
        parsed = {
            'type': 'transafrik_user',
            'qr_id': target_user.qr_identifier,
            'user_id': target_user.id,
            'name': target_user.fullname,
            'phone': target_user.phone,
            'country': target_user.country,
            'operator': country_info.get('name', 'Inconnu'),
        }
        is_valid = True

    if parsed and parsed.get('type') == 'transafrik_user':
        phone = parsed.get('phone', '')
        existing = Beneficiary.query.filter_by(user_id=current_user.id, phone=phone).first()
        if existing:
            existing.name = parsed.get('name', existing.name)
            existing.country = parsed.get('country', existing.country)
            existing.operator = parsed.get('operator', existing.operator)
            existing.updated_at = datetime.utcnow()
        else:
            beneficiary = Beneficiary(
                user_id=current_user.id,
                name=parsed.get('name', 'Inconnu'),
                phone=phone,
                country=parsed.get('country', ''),
                operator=parsed.get('operator', ''),
            )
            db.session.add(beneficiary)
        db.session.commit()

    resolved_user = target_user or (find_user_by_qr_identifier(parsed.get('qr_id', '')) if parsed else None)
    country_info = get_country_info(parsed.get('country', '')) if parsed else {}
    flag = country_info.get('flag', '') if country_info else ''
    country_name = country_info.get('name', parsed.get('country', '')) if country_info else parsed.get('country', '')

    return jsonify({
        'success': True,
        'valid': True,
        'qr_type': parsed.get('type') if parsed else '',
        'action_url': get_qr_action(parsed.get('type', '') if parsed else ''),
        'user': {
            'qr_id': resolved_user.qr_identifier if resolved_user else (parsed.get('qr_id') if parsed else ''),
            'name': resolved_user.fullname if resolved_user else (parsed.get('name') if parsed else ''),
            'phone': resolved_user.phone if resolved_user else (parsed.get('phone') if parsed else ''),
            'country': resolved_user.country if resolved_user else (parsed.get('country') if parsed else ''),
            'country_name': country_name,
            'flag': flag,
            'operator': parsed.get('operator') if parsed else '',
        },
        'parsed': parsed,
    })


@app.route('/api/qrcode/history')
@login_required
def api_qrcode_history():
    from services.qrcode_service import get_scan_history_from_db
    history = get_scan_history_from_db(current_user.id)
    return jsonify({'success': True, 'history': history})


# ==================== PAGE 404 ====================

@app.errorhandler(404)
def page_not_found(e):
    return jsonify({'error': 'Page non trouvée'}), 404


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)