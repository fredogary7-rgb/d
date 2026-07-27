import os
import logging
import hmac
import hashlib
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from models import db, User, Transfer, Deposit, Beneficiary, Transaction, OtpCode, KycRequest, SupportTicket, SupportMessage, PushSubscription, Withdrawal, PaymentRequest, TransactionReceive, Notification
from services.receive_service import (
    create_payment_request, cancel_payment_request, get_payment_request_by_code,
    get_user_payment_requests, get_recent_received_payments,
    generate_pay_qrcode, search_user_for_payment, search_users_for_payment,
    expire_old_requests, process_receive_payment, process_free_payment,
    generate_receive_reference, process_free_payment as process_wallet_to_wallet,
)
from services.push_service import send_push_to_user
from services.email_service import send_otp_email
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
from services.withdraw_service import (
    submit_withdraw,
    get_withdrawal_history,
    get_available_countries,
    get_operators_by_country,
    status_label as withdraw_status_label,
    process_withdrawal_webhook,
)
from admin import admin_bp
from admin.models import AdminUser, AdminLog, SystemConfig
from services.seo_service import (
    get_seo_context, generate_sitemap_xml, ROBOTS_TXT,
    SITE_NAME, SITE_DOMAIN, SITE_LOGO, SITE_THEME_COLOR, SITE_BG_COLOR
)

load_dotenv()

# ==================== GLOBAL CONSTANTS ====================
COUNTRY_FLAGS = {
    'TG': '\U0001f1f9\U0001f1ec', 'BJ': '\U0001f1e7\U0001f1ef', 'CM': '\U0001f1e8\U0001f1f2',
    'CI': '\U0001f1e8\U0001f1ee', 'BF': '\U0001f1e7\U0001f1eb', 'CG': '\U0001f1e8\U0001f1ec',
    'CD': '\U0001f1e8\U0001f1e9', 'GA': '\U0001f1ec\U0001f1e6', 'UG': '\U0001f1fa\U0001f1ec',
    'ZM': '\U0001f1ff\U0001f1f2', 'SN': '\U0001f1f8\U0001f1f3',
}
COUNTRY_NAMES = {
    'TG': 'Togo', 'BJ': 'B\u00e9nin', 'CM': 'Cameroun', 'CI': 'C\u00f4te d\'Ivoire',
    'BF': 'Burkina Faso', 'CG': 'Congo', 'CD': 'RD Congo', 'GA': 'Gabon',
    'UG': 'Ouganda', 'ZM': 'Zambie', 'SN': 'S\u00e9n\u00e9gal',
}

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

@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()

# Register admin blueprint
app.register_blueprint(admin_bp)

# Context processors
@app.context_processor
def inject_now():
    return {"now": datetime.utcnow()}

@app.context_processor
def inject_config():
    return {"config_value": lambda key, default=None: SystemConfig.get(key, default)}

@app.context_processor
def inject_seo():
    """Injecte les variables SEO dans tous les templates."""
    seo = get_seo_context()
    # Ajouter des variables utiles pour les templates
    seo["site_name"] = SITE_NAME
    seo["site_domain"] = SITE_DOMAIN
    seo["site_logo"] = SITE_LOGO
    return seo

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except Exception:
        return None

# Create tables
with app.app_context():
    db.create_all()

# ==================== ROUTES ====================

# --- PWA Routes ---
@app.route('/offline')
def offline():
    return render_template('offline.html')

@app.route('/sw.js')
def service_worker():
    """Sert le Service Worker à la racine du site (obligatoire pour le scope '/'.)"""
    from flask import send_from_directory, make_response
    response = make_response(send_from_directory('static', 'sw.js'))
    response.cache_control.no_cache = True
    return response

@app.route('/')
def index():
    """Page d'accueil avec avis clients validés."""
    from models import Review

    approved_reviews = Review.query.filter_by(approved=True).order_by(Review.created_at.desc()).limit(10).all()
    total_reviews = Review.query.filter_by(approved=True).count()
    avg_rating = db.session.query(db.func.coalesce(db.func.avg(Review.rating), 0)).filter(
        Review.approved == True
    ).scalar()
    avg_rating = round(float(avg_rating), 1)

    user_has_review = False
    if current_user.is_authenticated:
        user_has_review = Review.query.filter_by(user_id=current_user.id).first() is not None

    # JSON-LD Structured Data pour les avis (AggregateRating)
    reviews_structured_data = None
    if total_reviews > 0 and avg_rating > 0:
        reviews_structured_data = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "TransAfrik",
            "url": "https://transafrik.org",
            "aggregateRating": {
                "@type": "AggregateRating",
                "ratingValue": avg_rating,
                "bestRating": "5",
                "reviewCount": total_reviews,
            }
        }

    return render_template(
        'index.html',
        approved_reviews=approved_reviews,
        total_reviews=total_reviews,
        avg_rating=avg_rating,
        user_has_review=user_has_review,
        reviews_structured_data=reviews_structured_data,
    )


# ==================== AVIS CLIENTS ====================
@app.route('/api/reviews', methods=['GET'])
def api_get_reviews():
    """Récupère les avis validés (pagination)."""
    from models import Review
    page = request.args.get('page', 1, type=int)
    per_page = 10
    query = Review.query.filter_by(approved=True).order_by(Review.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'success': True,
        'reviews': [r.to_dict() for r in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
        'has_next': pagination.has_next,
    })


@app.route('/api/reviews', methods=['POST'])
@login_required
def api_submit_review():
    """Soumet ou modifie un avis client."""
    from models import Review, Transfer, Deposit, Withdrawal
    import re
    import html

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Données requises.'}), 400

    rating = data.get('rating')
    title = (data.get('title') or '').strip()
    comment = (data.get('comment') or '').strip()

    # Validation
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({'success': False, 'message': 'La note doit être entre 1 et 5.'}), 400
    if len(comment) < 20 or len(comment) > 1000:
        return jsonify({'success': False, 'message': 'Le commentaire doit faire entre 20 et 1000 caractères.'}), 400

    # Nettoyage anti-XSS
    title = html.escape(title)
    comment = html.escape(comment)
    # Supprimer les URLs
    comment = re.sub(r'https?://\S+', '[lien supprimé]', comment)
    title = re.sub(r'https?://\S+', '[lien supprimé]', title)

    # Vérification client vérifié (au moins 1 transfert, dépôt ou retrait)
    has_transfer = Transfer.query.filter_by(sender_user_id=current_user.id, status='COMPLETED').first()
    has_deposit = Deposit.query.filter_by(user_id=current_user.id, status='COMPLETED').first()
    has_withdrawal = Withdrawal.query.filter_by(user_id=current_user.id, status='COMPLETED').first()
    verified = bool(has_transfer or has_deposit or has_withdrawal)

    # Un seul avis par utilisateur (modifiable)
    existing = Review.query.filter_by(user_id=current_user.id).first()
    if existing:
        existing.rating = rating
        existing.title = title if title else None
        existing.comment = comment
        existing.country = current_user.country
        existing.verified = verified
        existing.approved = False  # à re-valider par admin
        existing.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Votre avis a été mis à jour et sera révisé par notre équipe.',
            'review': existing.to_dict(),
            'is_update': True,
        })

    review = Review(
        user_id=current_user.id,
        rating=rating,
        title=title if title else None,
        comment=comment,
        country=current_user.country,
        verified=verified,
        approved=False,
    )
    db.session.add(review)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Merci ! Votre avis sera publié après validation.',
        'review': review.to_dict(),
        'is_update': False,
    })


@app.route('/api/reviews/my', methods=['GET'])
@login_required
def api_get_my_review():
    """Récupère l'avis de l'utilisateur connecté."""
    from models import Review
    review = Review.query.filter_by(user_id=current_user.id).first()
    if not review:
        return jsonify({'success': True, 'review': None})
    return jsonify({'success': True, 'review': review.to_dict()})

# --- Pages statiques publiques ---
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/security')
def security():
    return render_template('security.html')

@app.route('/features')
def features():
    return render_template('features.html')

@app.route('/services')
def services():
    return render_template('services.html')

# --- LOGIN (connexion directe email + password) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        remember = data.get('remember', False)

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({'success': False, 'message': 'Email ou mot de passe incorrect.'}), 401

        login_user(user, remember=remember)
        app.logger.info(f"Connexion réussie pour {email}")

        return jsonify({
            'success': True,
            'message': 'Connexion réussie !',
            'redirect': url_for('dashboard'),
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

        phone_clean = phone.replace(' ', '').replace('+', '').replace('-', '').strip()
        if User.query.filter_by(phone=phone_clean).first():
            errors.append('Ce numéro de téléphone est déjà utilisé.')
        if country not in ['TG','BJ','CM','CI','BF','CG','CD','GA','UG','ZM','SN']:
            errors.append('Pays invalide.')
        if len(password) < 8:
            errors.append('Le mot de passe doit contenir au moins 8 caractères.')

        if errors:
            return jsonify({'success': False, 'message': errors[0], 'errors': errors}), 400

        otp_result = create_otp(email, 'register')
        if not otp_result.get('success'):
            return jsonify({'success': False, 'message': otp_result.get('error', 'Erreur OTP.')}), 429

        code = otp_result['code']
        send_otp_email(email, code, 'register')

        session['pending_register'] = {
            'email': email,
            'fullname': fullname,
            'phone': phone_clean,
            'country': country,
            'password': password,
        }

        return jsonify({
            'success': True,
            'message': 'Un code de vérification a été envoyé par email.',
            'redirect': url_for('verify_otp_page', purpose='register'),
        })

    return render_template('inscription.html')


# --- VERIFY OTP ---
@app.route('/verify-otp/<purpose>', methods=['GET', 'POST'])
def verify_otp_page(purpose='login'):
    if purpose not in ('register', 'login', 'reset_password', 'change_phone'):
        flash('Type de vérification invalide.', 'error')
        return redirect(url_for('index'))

    email_display = session.get('pending_email', '')
    if not email_display:
        pending = session.get('pending_register', {})
        email_display = pending.get('email', '')
        if not email_display:
            flash('Session expirée. Veuillez recommencer.', 'warning')
            return redirect(url_for('login'))

    if request.method == 'POST':
        data = request.get_json()
        code = data.get('code', '').strip()

        if not code or len(code) != 6:
            return jsonify({'success': False, 'message': 'Le code doit contenir 6 chiffres.'}), 400

        result = verify_otp(email_display, code, purpose)
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
            session.pop('pending_email', None)
            login_user(user)

            app.logger.info(f"Nouveau compte créé via OTP : {user.email}")

            # Notification push de bienvenue
            try:
                send_push_to_user(
                    user_id=user.id,
                    title="Bienvenue sur TransAfrik ! 🎉",
                    body=f"Bonjour {user.fullname}, votre compte a été créé avec succès. Commencez à envoyer de l'argent dès maintenant.",
                    url="/dashboard",
                    tag="welcome",
                    data={"type": "welcome", "user_id": user.id},
                )
                # Notification in-app
                notif = Notification(
                    user_id=user.id,
                    title="Bienvenue sur TransAfrik ! 🎉",
                    message="Votre compte a été créé avec succès. Découvrez nos services de transfert d'argent.",
                    type="account_created",
                    data={"user_id": user.id},
                )
                db.session.add(notif)
                db.session.commit()
                app.logger.info(f"PUSH | Notification bienvenue envoyée | user={user.id}")
            except Exception as push_err:
                app.logger.warning(f"[PUSH] Échec notification bienvenue: {push_err}")

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
            session.pop('pending_email', None)
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

    return render_template('verify_otp.html', purpose=purpose, phone=email_display)


# --- RESEND OTP ---
@app.route('/api/otp/resend', methods=['POST'])
def api_resend_otp():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    if not email:
        # Rétrocompatibilité : chercher phone
        phone = data.get('phone', '').strip()
        if phone:
            user = User.query.filter_by(phone=phone).first()
            if user:
                email = user.email
            else:
                email = phone
    if not email:
        # Fallback depuis la session
        pending = session.get('pending_register', {})
        email = pending.get('email', '')

    if not email:
        return jsonify({'success': False, 'message': 'Aucun email trouvé.'}), 400

    email_lower = email.strip().lower()
    otp_result = resend_otp_service(email_lower)

    if not otp_result.get('success'):
        return jsonify({'success': False, 'message': otp_result.get('error', 'Erreur OTP.')}), 429

    code = otp_result['code']
    purpose = session.get('pending_register', {}).get('purpose', 'login')
    send_otp_email(email_lower, code, purpose)
    app.logger.info(f"EMAIL | OTP renvoyé à {email_lower}")

    return jsonify({'success': True, 'message': 'Nouveau code envoyé par email.'})


# --- FORGOT PASSWORD ---
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        phone = data.get('phone', '').strip()

        if not email and not phone:
            return jsonify({'success': False, 'message': 'Email ou numéro de téléphone requis.'}), 400

        user = None
        if email:
            user = User.query.filter_by(email=email).first()
        if not user and phone:
            phone_clean = phone.replace(' ', '').replace('+', '').replace('-', '').strip()
            user = User.query.filter_by(phone=phone_clean).first()

        if not user:
            return jsonify({
                'success': True,
                'message': 'Si cet email/numéro est associé à un compte, un code vous sera envoyé.',
            })

        otp_result = create_otp(user.email, 'reset_password')
        if not otp_result.get('success'):
            return jsonify({'success': False, 'message': otp_result.get('error', 'Erreur OTP.')}), 429

        code = otp_result['code']
        send_otp_email(user.email, code, 'reset_password')

        session['pending_email'] = user.email
        session['pending_reset_user_id'] = user.id

        return jsonify({
            'success': True,
            'message': 'Un code de réinitialisation a été envoyé par email.',
            'redirect': url_for('verify_otp_page', purpose='reset_password'),
        })

    return render_template('forgot_password.html')


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

        fees = calculate_fees(
            amount,
            sender_country=sender_country,
            receiver_country=receiver_country,
            sender_operator=sender_operator,
            receiver_operator=receiver_operator,
            user_tier=getattr(current_user, 'tier', 'standard'),
            user_id=current_user.id,
        )
        total_amount = calculate_total(
            amount,
            sender_country=sender_country,
            receiver_country=receiver_country,
            sender_operator=sender_operator,
            receiver_operator=receiver_operator,
            user_tier=getattr(current_user, 'tier', 'standard'),
            user_id=current_user.id,
        )

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

# ==================== WITHDRAW / RETRAIT ====================

@app.route('/withdraw')
@login_required
def withdraw_page():
    """Page de retrait — envoyer de l'argent vers un wallet Mobile Money."""
    countries = get_available_countries()
    return render_template('withdraw.html',
                           user=current_user,
                           countries=countries,
                           country_flags=COUNTRY_FLAGS,
                           country_names=COUNTRY_NAMES)


@app.route('/api/withdraw/operators/<country_code>')
@login_required
def api_withdraw_operators(country_code):
    """Retourne les opérateurs disponibles pour un pays donné."""
    ops = get_operators_by_country(country_code.upper())
    return jsonify({'success': True, 'operators': ops})


@app.route('/api/withdraw/fees', methods=['POST'])
@login_required
def api_withdraw_fees():
    """Calcule les frais pour un retrait."""
    from services.withdraw_service import _calculate_withdrawal_fee
    from services.soleaspay import convert_currency

    data = request.get_json(silent=True) or {}
    amount_display = float(data.get('amount', 0))
    currency = data.get('currency', 'XOF').upper()
    operator_id = int(data.get('operator_id', 0))

    from config.operators import get_operator_by_id

    op_info = get_operator_by_id(operator_id)

    if not op_info:
        return jsonify({'success': False, 'message': 'Opérateur invalide.'}), 400

    op_currency = op_info.get('currency', 'XOF')

    # Conversion si nécessaire
    exchange_rate = 1.0
    amount_converted = amount_display
    if currency != op_currency:
        try:
            conv = convert_currency(amount_display, currency, op_currency)
            if not conv.get('success', True):
                return jsonify({'success': False, 'message': f'Conversion {currency} → {op_currency} impossible.'}), 400
            amount_converted = float(conv.get('result', amount_display))
            exchange_rate = amount_converted / amount_display if amount_display > 0 else 1.0
        except Exception:
            return jsonify({'success': False, 'message': 'Erreur de conversion.'}), 400

    fee_result = _calculate_withdrawal_fee(
        amount=int(amount_converted),
        sender_country=current_user.country,
        receiver_country=op_info['country'],
        receiver_operator=op_info['slug'],
    )
    fees = fee_result['fees']
    total_debited = int(amount_converted) + fees

    return jsonify({
        'success': True,
        'amount': amount_display,
        'converted_amount': amount_converted,
        'fees': fees,
        'total_debited': total_debited,
        'receiver_gets': amount_converted,
        'currency': currency,
        'op_currency': op_currency,
        'exchange_rate': exchange_rate,
    })


@app.route('/withdraw/create', methods=['POST'])
@login_required
def withdraw_create():
    """Crée un retrait (POST)."""
    data = request.get_json(silent=True) or {}

    result = submit_withdraw(current_user, data)
    if not result.get('success'):
        return jsonify(result), 400

    withdrawal = result['withdrawal']
    return jsonify({
        'success': True,
        'message': result.get('message', 'Retrait créé.'),
        'withdrawal': withdrawal.to_dict(),
        'redirect': url_for('withdraw_page'),
    })


@app.route('/api/withdraw/history')
@login_required
def api_withdraw_history():
    """Retourne l'historique des retraits de l'utilisateur."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    result = get_withdrawal_history(current_user.id, page=page, per_page=per_page)
    # Ajouter le label de statut
    for w in result['withdrawals']:
        w['status_label'] = withdraw_status_label(w['status'])
    return jsonify({'success': True, **result})


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

    return render_template(
        'dashboard.html',
        user=user,
        tx_count=tx_count,
        beneficiary_count=beneficiary_count,
        total_sent=total_sent,
        total_received=total_received,
        unread_notifications=unread_notifications,
        recent_txs=recent_txs,
        country_flags=COUNTRY_FLAGS,
        country_names=COUNTRY_NAMES,
    )

# --- PROFILE ---
@app.route('/profile')
@login_required
def profile():
    from datetime import date
    user = current_user
    tx_count = user.tx_count
    beneficiary_count = user.beneficiary_count
    total_sent = user.total_sent
    total_received = user.total_received
    unread_notifications = user.unread_notifications

    # KYC progress
    kyc = KycRequest.query.filter_by(user_id=user.id).first()
    kyc_progress = kyc.progress_percent if kyc else 0

    # QR count (placeholder — count user's transactions or specific QR records)
    qr_count = Transaction.query.filter_by(user_id=user.id, type='receive').count()

    # Ticket count
    ticket_count = SupportTicket.query.filter_by(user_id=user.id).count()

    # Referral count
    referral_count = User.query.filter_by(referred_by=user.id).count()

    return render_template(
        'profile.html',
        user=user,
        tx_count=tx_count,
        beneficiary_count=beneficiary_count,
        total_sent=total_sent,
        total_received=total_received,
        unread_notifications=unread_notifications,
        kyc_progress=kyc_progress,
        qr_count=qr_count,
        ticket_count=ticket_count,
        referral_count=referral_count,
        country_flags=COUNTRY_FLAGS,
        country_names=COUNTRY_NAMES,
    )

@app.route('/profile/update', methods=['POST'])
@login_required
def profile_update():
    user = current_user
    firstname = request.form.get('firstname', '').strip()
    lastname = request.form.get('lastname', '').strip()
    if firstname and lastname:
        user.fullname = f"{firstname} {lastname}"
    elif firstname:
        user.fullname = firstname
    elif lastname:
        user.fullname = lastname

    birth_date_str = request.form.get('birth_date', '').strip()
    if birth_date_str:
        try:
            user.birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Date de naissance invalide.', 'error')
            return redirect(url_for('profile'))
    else:
        user.birth_date = None

    gender = request.form.get('gender', '').strip()
    user.gender = gender if gender in ('male', 'female', 'other') else None

    profession = request.form.get('profession', '').strip()
    user.profession = profession or None

    address = request.form.get('address', '').strip()
    user.address = address or None

    city = request.form.get('city', '').strip()
    user.city = city or None

    postal_code = request.form.get('postal_code', '').strip()
    user.postal_code = postal_code or None

    country = request.form.get('country', '').strip()
    if country and country in COUNTRY_NAMES:
        user.country = country

    user.updated_at = datetime.utcnow()
    db.session.commit()
    flash('Profil mis à jour avec succès.', 'success')
    return redirect(url_for('profile'))

@app.route('/profile/upload-avatar', methods=['POST', 'DELETE'])
@login_required
def profile_upload_avatar():
    user = current_user
    if request.method == 'DELETE':
        user.profile_picture = None
        user.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True})
    # POST - upload
    if 'avatar' not in request.files:
        return jsonify({'success': False, 'message': 'Aucun fichier envoyé.'})
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Fichier vide.'})
    if file and allowed_file(file.filename):
        import uuid as uuid_mod
        filename = f"avatar_{user.id}_{uuid_mod.uuid4().hex[:8]}.{file.filename.rsplit('.',1)[1].lower()}"
        upload_dir = os.path.join(app.static_folder, 'uploads', 'avatars')
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        user.profile_picture = f"/static/uploads/avatars/{filename}"
        user.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'url': user.profile_picture})
    return jsonify({'success': False, 'message': 'Format non autorisé (JPG, PNG, JPEG uniquement).'})

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ('jpg', 'jpeg', 'png')

@app.route('/profile/change-password', methods=['POST'])
@login_required
def profile_change_password():
    user = current_user
    current_pw = request.form.get('current_password', '')
    new_pw = request.form.get('new_password', '')
    confirm_pw = request.form.get('confirm_password', '')

    if not check_password_hash(user.password_hash, current_pw):
        flash('Mot de passe actuel incorrect.', 'error')
        return redirect(url_for('profile'))
    if len(new_pw) < 8:
        flash('Le nouveau mot de passe doit contenir au moins 8 caractères.', 'error')
        return redirect(url_for('profile'))
    if new_pw != confirm_pw:
        flash('Les nouveaux mots de passe ne correspondent pas.', 'error')
        return redirect(url_for('profile'))

    user.password_hash = generate_password_hash(new_pw)
    user.updated_at = datetime.utcnow()
    db.session.commit()
    flash('Mot de passe modifié avec succès.', 'success')
    return redirect(url_for('profile'))

@app.route('/profile/change-pin', methods=['POST'])
@login_required
def profile_change_pin():
    user = current_user
    current_pw = request.form.get('current_password', '')
    pin = request.form.get('pin', '')
    confirm_pin = request.form.get('confirm_pin', '')

    if not check_password_hash(user.password_hash, current_pw):
        flash('Mot de passe incorrect.', 'error')
        return redirect(url_for('profile'))
    if not pin.isdigit() or len(pin) != 4:
        flash('Le PIN doit être composé de 4 chiffres.', 'error')
        return redirect(url_for('profile'))
    if pin != confirm_pin:
        flash('Les PIN ne correspondent pas.', 'error')
        return redirect(url_for('profile'))

    user.pin_hash = generate_password_hash(pin)
    user.updated_at = datetime.utcnow()
    db.session.commit()
    flash('PIN mis à jour avec succès.', 'success')
    return redirect(url_for('profile'))

@app.route('/profile/two-factor', methods=['POST'])
@login_required
def profile_two_factor():
    user = current_user
    enabled = request.form.get('two_factor_enabled') == 'on'
    method = request.form.get('two_factor_method', 'sms').strip()

    user.two_factor_enabled = enabled
    user.two_factor_method = method if enabled else None
    user.updated_at = datetime.utcnow()
    db.session.commit()
    status = 'activée' if enabled else 'désactivée'
    flash(f'Authentification à deux facteurs {status}.', 'success')
    return redirect(url_for('profile'))

@app.route('/profile/preferences', methods=['POST'])
@login_required
def profile_preferences():
    user = current_user
    user.language = request.form.get('language', user.language)
    user.currency = request.form.get('currency', user.currency)
    country = request.form.get('country')
    if country and country in COUNTRY_NAMES:
        user.country = country
    theme = request.form.get('theme')
    if theme in ('light', 'dark'):
        user.theme = theme
    user.notification_email = request.form.get('notification_email') == '1'
    user.notification_sms = request.form.get('notification_sms') == '1'
    user.notification_push = request.form.get('notification_push') == '1'
    user.vibrations = request.form.get('vibrations') == '1'
    user.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True, 'theme': user.theme})

@app.route('/profile/delete-account', methods=['POST'])
@login_required
def profile_delete_account():
    user = current_user
    password = request.form.get('password', '')
    confirm_text = request.form.get('confirm_text', '')

    if not check_password_hash(user.password_hash, password):
        flash('Mot de passe incorrect.', 'error')
        return redirect(url_for('profile'))
    if confirm_text != 'SUPPRIMER':
        flash('Veuillez taper SUPPRIMER pour confirmer.', 'error')
        return redirect(url_for('profile'))

    # Soft delete: mark as deleted and deactivate
    user.is_deleted = True
    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.session.commit()
    logout_user()
    flash('Votre compte a été supprimé. Nous sommes tristes de vous voir partir.', 'info')
    return redirect(url_for('index'))

# --- API: Calculate fees ---
@app.route('/api/calculate-fees', methods=['POST'])
@login_required
def api_calculate_fees():
    data = request.get_json()
    amount = int(data.get('amount', 0))
    fees = calculate_fees(
        amount,
        sender_country=data.get('sender_country', ''),
        receiver_country=data.get('receiver_country', ''),
        sender_operator=data.get('sender_operator', ''),
        receiver_operator=data.get('receiver_operator', ''),
        promo_code=data.get('promo_code'),
        user_tier=getattr(current_user, 'tier', 'standard'),
        user_id=current_user.id,
    )
    total = calculate_total(
        amount,
        sender_country=data.get('sender_country', ''),
        receiver_country=data.get('receiver_country', ''),
        sender_operator=data.get('sender_operator', ''),
        receiver_operator=data.get('receiver_operator', ''),
        promo_code=data.get('promo_code'),
        user_tier=getattr(current_user, 'tier', 'standard'),
        user_id=current_user.id,
    )
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

SOLEAS_WEBHOOK_SECRET = os.getenv('SOLEAS_WEBHOOK_SECRET', '')  # Clé privée SoleasPay (envoyée dans x-private-key)


def _verify_webhook_signature(payload_body: bytes, private_key_header: str) -> bool:
    """Vérifie que le header x-private-key correspond à une clé autorisée.

    SoleasPay envoie la clé privée dans le header x-private-key.
    Plusieurs clés sont acceptées (SoleasPay utilise des clés différentes selon l'environnement).
    """
    keys = [SOLEAS_WEBHOOK_SECRET] if SOLEAS_WEBHOOK_SECRET else []
    extra = os.getenv('SOLEAS_EXTRA_KEYS', '')
    if extra:
        keys.extend(k.strip() for k in extra.split(',') if k.strip())

    if not keys:
        webhook_logger.warning('Aucune clé privée configurée — webhook accepté sans vérification')
        return True
    if not private_key_header:
        webhook_logger.warning('Header x-private-key manquant — webhook rejeté')
        return False

    for key in keys:
        if hmac.compare_digest(key.encode('utf-8'), private_key_header.encode('utf-8')):
            webhook_logger.info(f'Signature webhook validée (clé {key[:8]}...)')
            return True

    webhook_logger.warning(f'Signature invalide : header={private_key_header[:16]}... ne correspond à aucune clé autorisée')
    return False


def _log_webhook(webhook_type: str, reference: str, status: str, payload: dict):
    ip = request.remote_addr or 'unknown'
    webhook_logger.info(f"Type={webhook_type} | Reference={reference} | Status={status} | IP={ip} | Payload={payload}")


# ==================== WEBHOOKS SOLEASPAY ====================

def _handle_payment_webhook(payload: dict):
    """Logique de traitement d'un webhook PURCHASE (Pay-In / Dépôt).

    Format réel SoleasPay :
      payload.data.external_reference = "DEP-20260720-9855A8" ou "E-123"
      payload.data.reference          = "MLS6a5e50b94b63eB" (interne SoleasPay)
    """
    data_block = payload.get('data')
    data = data_block if isinstance(data_block, dict) else {}
    format_type = 'A (data wrapper)' if data else 'B (plat)'
    webhook_logger.info(f'WEBHOOK PURCHASE format={format_type} payload_keys={list(payload.keys())[:10]}')
    external_ref = (
        data.get('external_reference')
        or payload.get('externalRef')
        or payload.get('external_reference')
        or payload.get('order_id')
        or ''
    )
    internal_ref = data.get('reference') or payload.get('internalRef') or ''
    transfer = get_transfer_by_reference(external_ref) if external_ref else None

    # ---- Fallback : chercher un Deposit par external_reference ----
    deposit = None
    if not transfer and external_ref:
        deposit = Deposit.query.filter_by(reference=external_ref).first()

    _log_webhook('PURCHASE', external_ref, payload.get('status', 'UNKNOWN'), payload)

    webhook_logger.info(
        f"WEBHOOK RECEIVED\n"
        f"Operation : PURCHASE\n"
        f"Status : {payload.get('status', 'UNKNOWN')}\n"
        f"Reference : {external_ref}"
    )

    # ---- Traiter un Deposit si trouvé ----
    if deposit and not transfer:
        webhook_logger.info(f'Deposit trouvé: id={deposit.id} ref={deposit.reference} status={deposit.status} user={deposit.user_id}')
        if deposit.status != 'PAYMENT_PROCESSING':
            webhook_logger.info(f'Deposit ignoré (idempotent) : statut={deposit.status} (attendu PAYMENT_PROCESSING)')
            return jsonify({'success': True, 'message': f'Dépôt déjà traité (statut={deposit.status})'})

        webhook_logger.info(f'Deposit en PAYMENT_PROCESSING — traitement du statut {payload.get("status")}')
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
            webhook_logger.info(f'Dépôt COMPLETED via webhook unifié: {deposit.reference}, montant={deposit.amount}')

            # ---- Notification push à l'utilisateur ----
            try:
                send_push_to_user(
                    user_id=deposit.user_id,
                    title="💰 Dépôt confirmé",
                    body=f"Votre dépôt de {deposit.amount:,} {deposit.currency} a été crédité avec succès sur votre compte TransAfrik.",
                    url="/wallet",
                    tag=f"deposit-{deposit.reference}",
                    data={"reference": deposit.reference, "amount": deposit.amount, "currency": deposit.currency},
                )
                app.logger.info(f"PUSH | ENVOYÉE | Dépôt confirmé | user={deposit.user_id} | amount={deposit.amount}")
                # Notification in-app
                notif = Notification(
                    user_id=deposit.user_id,
                    title="Dépôt confirmé",
                    message=f"Votre dépôt de {deposit.amount:,} {deposit.currency} a été crédité avec succès.",
                    type="deposit_success",
                    data={"reference": deposit.reference},
                )
                db.session.add(notif)
                db.session.commit()
            except Exception as push_err:
                app.logger.warning(f"[PUSH] Échec notification dépôt: {push_err}")

            # ---- Email de confirmation ----
            try:
                from services.email_service import send_deposit_email
                send_deposit_email(
                    email=deposit.user.email,
                    fullname=deposit.user.fullname,
                    amount=deposit.amount,
                    currency=deposit.currency,
                    reference=deposit.reference,
                )
                app.logger.info(f"EMAIL | EMAIL envoyé avec succès | dépôt {deposit.reference}")
            except Exception as email_err:
                app.logger.warning(f"[EMAIL] Échec envoi email dépôt: {email_err}")

            return jsonify({'success': True, 'message': 'Dépôt confirmé', 'status': 'COMPLETED'})
        elif is_payment_failed(payload):
            deposit.webhook_payload = payload
            deposit.status = 'FAILED'
            deposit.status_message = payload.get('message', 'Échec du dépôt')
            db.session.commit()
            webhook_logger.info(f'Dépôt FAILED via webhook unifié: {deposit.reference}')

            # ---- Notification push échec ----
            try:
                send_push_to_user(
                    user_id=deposit.user_id,
                    title="❌ Dépôt échoué",
                    body=f"Votre dépôt de {deposit.amount:,} {deposit.currency} a échoué : {deposit.status_message}",
                    url="/wallet",
                    tag=f"deposit-{deposit.reference}",
                    data={"reference": deposit.reference, "amount": deposit.amount, "currency": deposit.currency},
                )
                notif = Notification(
                    user_id=deposit.user_id,
                    title="Dépôt échoué",
                    message=f"Votre dépôt de {deposit.amount:,} {deposit.currency} a échoué.",
                    type="deposit_failed",
                    data={"reference": deposit.reference},
                )
                db.session.add(notif)
                db.session.commit()
            except Exception as push_err:
                app.logger.warning(f"[PUSH] Échec notification échec dépôt: {push_err}")

            return jsonify({'success': False, 'message': 'Dépôt échoué', 'status': 'FAILED'})
        else:
            deposit.webhook_payload = payload
            db.session.commit()
            return jsonify({'success': True, 'message': 'Statut inconnu, payload enregistré'})

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
        webhook_logger.info(
            f"WEBHOOK RECEIVED\n"
            f"Operation : PURCHASE\n"
            f"Status : SUCCESS\n"
            f"Reference : {transfer.reference}\n"
            f"User : {transfer.sender_user_id}\n"
            f"Result : COMPLETED"
        )
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
        webhook_logger.info(
            f"WEBHOOK RECEIVED\n"
            f"Operation : PURCHASE\n"
            f"Status : FAILED\n"
            f"Reference : {transfer.reference}\n"
            f"User : {transfer.sender_user_id}\n"
            f"Result : FAILED"
        )
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


def _handle_withdraw_webhook(payload: dict):
    """Logique de traitement d'un webhook WITHDRAW.

    SoleasPay envoie deux formats :
      A) Avec "data" wrapper : data.reference / data.external_reference
      B) Format plat         : internalRef / externalRef

    On cherche d'abord un Withdrawal, puis un Transfer (ancien flux).
    """
    data_block = payload.get('data')
    data = data_block if isinstance(data_block, dict) else {}
    format_type = 'A (data wrapper)' if data else 'B (plat)'
    webhook_logger.info(f'WEBHOOK WITHDRAW format={format_type} payload_keys={list(payload.keys())[:10]}')
    data = payload.get('data', {})
    if isinstance(data, list) and len(data) > 0:
        soleas_ref = data[0].get('reference') or ''
        external_ref = data[0].get('external_reference') or ''
    elif isinstance(data, dict):
        soleas_ref = data.get('reference') or ''
        external_ref = data.get('external_reference') or ''
    else:
        soleas_ref = ''
        external_ref = ''

    # ---- Format B : plat (internalRef/externalRef en top-level) ----
    if not soleas_ref:
        soleas_ref = payload.get('internalRef') or payload.get('reference') or ''
    if not external_ref:
        external_ref = payload.get('externalRef') or payload.get('external_reference') or ''

    display_ref = soleas_ref or external_ref
    _log_webhook('WITHDRAW', display_ref, payload.get('status', 'UNKNOWN'), payload)

    webhook_logger.info(
        f"WEBHOOK RECEIVED\n"
        f"Operation : WITHDRAW\n"
        f"Status : {payload.get('status', 'UNKNOWN')}\n"
        f"SoleasRef : {soleas_ref}\n"
        f"ExternalRef : {external_ref}"
    )

    # ---- 1. Chercher un Withdrawal par withdraw_reference ou withdraw_external_reference ----
    withdrawal = None
    if soleas_ref:
        withdrawal = Withdrawal.query.filter(
            (Withdrawal.withdraw_reference == soleas_ref) |
            (Withdrawal.external_reference == soleas_ref)
        ).first()

    # ---- 2. Fallback : chercher par external_reference ----
    if not withdrawal and external_ref:
        withdrawal = Withdrawal.query.filter(
            (Withdrawal.withdraw_reference == external_ref) |
            (Withdrawal.external_reference == external_ref)
        ).first()

    if withdrawal:
        webhook_logger.info(f"Withdrawal trouvé: id={withdrawal.id} withdraw_ref={withdrawal.withdraw_reference} status={withdrawal.status}")
        if withdrawal.status not in ('WITHDRAW_PROCESSING', 'WAITING_WITHDRAW'):
            webhook_logger.info(f'Webhook ignoré (idempotent) : withdrawal déjà au statut {withdrawal.status}')
            return jsonify({
                'success': True,
                'message': f'Withdrawal déjà traité (statut={withdrawal.status})',
                'external_reference': withdrawal.external_reference,
                'status': withdrawal.status,
            })

        success = process_withdrawal_webhook(withdrawal, payload)
        webhook_logger.info(
            f"WEBHOOK RESULT\n"
            f"Operation : WITHDRAW\n"
            f"Status : {'SUCCESS' if success else 'FAILED'}\n"
            f"WithdrawRef : {withdrawal.withdraw_reference}\n"
            f"User : {withdrawal.user_id}"
        )
        return jsonify({
            'success': success,
            'message': 'Retrait traité avec succès' if success else 'Retrait échoué',
            'withdraw_reference': withdrawal.withdraw_reference,
            'status': withdrawal.status,
        })

    # ---- 3. Fallback : chercher un Transfer (ancien flux) ----
    transfer = None
    if display_ref:
        transfer = Transfer.query.filter(
            (Transfer.reference == display_ref) |
            (Transfer.withdraw_reference == display_ref) |
            (Transfer.withdraw_external_reference == display_ref)
        ).first()
    if not transfer and soleas_ref:
        transfer = Transfer.query.filter(
            (Transfer.reference == soleas_ref) |
            (Transfer.withdraw_reference == soleas_ref) |
            (Transfer.withdraw_external_reference == soleas_ref)
        ).first()
    if not transfer and external_ref:
        transfer = Transfer.query.filter(
            (Transfer.reference == external_ref) |
            (Transfer.withdraw_reference == external_ref) |
            (Transfer.withdraw_external_reference == external_ref)
        ).first()
    if not transfer:
        webhook_logger.warning(f'Aucun Withdrawal ni Transfer trouvé pour reference={display_ref}')
        return jsonify({'success': False, 'message': 'Aucune entité trouvée pour cette référence.'}), 404

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
        webhook_logger.info(
            f"WEBHOOK RECEIVED\n"
            f"Operation : WITHDRAW\n"
            f"Status : SUCCESS\n"
            f"Reference : {transfer.reference}\n"
            f"User : {transfer.sender_user_id}\n"
            f"Result : COMPLETED"
        )
        return jsonify({
            'success': True,
            'message': 'Transfert terminé avec succès',
            'reference': transfer.reference,
            'status': 'COMPLETED',
        })
    elif is_payment_failed(payload):
        handle_withdraw_failed(transfer, reason=payload.get('message', 'Échec du retrait'), webhook_payload=payload)
        webhook_logger.info(
            f"WEBHOOK RECEIVED\n"
            f"Operation : WITHDRAW\n"
            f"Status : FAILED\n"
            f"Reference : {transfer.reference}\n"
            f"User : {transfer.sender_user_id}\n"
            f"Result : FAILED"
        )
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


@app.route('/webhook/soleaspay', methods=['POST'])
def webhook_soleaspay():
    """Webhook unifié SoleasPay — route unique pour PURCHASE et WITHDRAW."""
    # Diagnostic : afficher tous les headers reçus
    print(dict(request.headers))
    signature = request.headers.get('x-private-key', '')
    raw_body = request.get_data()
    if not _verify_webhook_signature(raw_body, signature):
        webhook_logger.warning('Signature invalide — webhook rejeté')
        return jsonify({'success': False, 'message': 'Signature invalide'}), 403

    payload = request.get_json(silent=True) or {}
    if not payload:
        return jsonify({'success': False, 'message': 'Payload invalide'}), 400

    # Logger intégralement les headers et le payload
    webhook_logger.info(f"WEBHOOK RECEIVED | Headers: {dict(request.headers)} | Payload: {payload}")

    # Détecter automatiquement le type d'opération
    data = payload.get('data', {})
    if isinstance(data, dict):
        operation = data.get('operation') or payload.get('operation') or ''
    else:
        operation = payload.get('operation') or ''

    operation = operation.upper().strip()

    # Router selon le type d'opération
    if operation == 'PURCHASE':
        return _handle_payment_webhook(payload)
    elif operation in ('WITHDRAW', 'WITHDRAWAL'):
        return _handle_withdraw_webhook(payload)
    else:
        webhook_logger.warning(f'Type d\'opération inconnu: {operation}')
        return jsonify({'success': False, 'message': f'Type d\'opération inconnu: {operation}'}), 400


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
    pay_sent = TransactionReceive.query.filter_by(sender_id=current_user.id)
    pay_recv = TransactionReceive.query.filter_by(receiver_id=current_user.id)
    deposits = Deposit.query.filter_by(user_id=current_user.id)
    withdrawals = Withdrawal.query.filter_by(user_id=current_user.id)

    total_count = transfers.count() + pay_sent.count() + deposits.count() + withdrawals.count()
    total_amount = db.session.query(
        db.func.coalesce(db.func.sum(Transfer.total_amount), 0)
    ).filter(Transfer.sender_user_id == current_user.id).scalar()
    total_paid = db.session.query(
        db.func.coalesce(db.func.sum(TransactionReceive.amount), 0)
    ).filter(TransactionReceive.sender_id == current_user.id).scalar()
    total_amount = (total_amount or 0) + (total_paid or 0)
    completed_count = (
        transfers.filter(Transfer.status == 'COMPLETED').count()
        + pay_sent.filter_by(status='completed').count()
        + pay_recv.filter_by(status='completed').count()
        + deposits.filter_by(status='COMPLETED').count()
        + withdrawals.filter_by(status='COMPLETED').count()
    )
    pending_count = (
        transfers.filter(
            Transfer.status.in_(['CREATED', 'WAITING_PAYMENT', 'PAYMENT_PROCESSING',
                                 'PAYMENT_SUCCESS', 'WITHDRAW_PROCESSING'])
        ).count()
        + pay_sent.filter_by(status='pending').count()
        + deposits.filter_by(status='PAYMENT_PROCESSING').count()
        + withdrawals.filter_by(status='WITHDRAW_PROCESSING').count()
    )

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

    # 1) Transferts classiques (envoi vers numéro)
    t_query = Transfer.query.filter(Transfer.sender_user_id == current_user.id)

    if filter_status and filter_status != 'ALL':
        if filter_status == 'PENDING':
            t_query = t_query.filter(Transfer.status.in_(['CREATED', 'WAITING_PAYMENT', 'PAYMENT_PROCESSING', 'PAYMENT_SUCCESS', 'WITHDRAW_PROCESSING']))
        elif filter_status == 'COMPLETED':
            t_query = t_query.filter_by(status='COMPLETED')
        elif filter_status == 'FAILED':
            t_query = t_query.filter_by(status='FAILED')
        elif filter_status == 'CANCELLED':
            t_query = t_query.filter_by(status='CANCELLED')
        else:
            t_query = t_query.filter_by(status=filter_status)

    if search:
        search_term = f'%{search}%'
        t_query = t_query.filter(db.or_(
            Transfer.reference.ilike(search_term),
            Transfer.receiver_phone.ilike(search_term),
            Transfer.receiver_name.ilike(search_term),
            Transfer.sender_phone.ilike(search_term),
        ))

    t_list = t_query.order_by(Transfer.created_at.desc()).all()

    # 2) Paiements libre (via pay link) — émis ou reçus
    p_query_sent = TransactionReceive.query.filter(TransactionReceive.sender_id == current_user.id)
    p_query_recv = TransactionReceive.query.filter(TransactionReceive.receiver_id == current_user.id)

    if filter_status and filter_status != 'ALL':
        if filter_status == 'COMPLETED':
            p_query_sent = p_query_sent.filter(TransactionReceive.status == 'completed')
            p_query_recv = p_query_recv.filter(TransactionReceive.status == 'completed')
        elif filter_status in ('FAILED', 'CANCELLED', 'PENDING'):
            p_query_sent = p_query_sent.filter(TransactionReceive.status == filter_status.lower())
            p_query_recv = p_query_recv.filter(TransactionReceive.status == filter_status.lower())

    if search:
        search_term = f'%{search}%'
        p_query_sent = p_query_sent.filter(TransactionReceive.reference.ilike(search_term))
        p_query_recv = p_query_recv.filter(TransactionReceive.reference.ilike(search_term))

    p_list = p_query_sent.order_by(TransactionReceive.created_at.desc()).all()
    p_recv_list = p_query_recv.order_by(TransactionReceive.created_at.desc()).all()

    # 3) Dépôts (Deposit)
    d_query = Deposit.query.filter_by(user_id=current_user.id)

    if filter_status and filter_status != 'ALL':
        d_status_map = {'COMPLETED': 'COMPLETED', 'FAILED': 'FAILED', 'PENDING': 'PAYMENT_PROCESSING'}
        mapped = d_status_map.get(filter_status)
        if mapped:
            d_query = d_query.filter_by(status=mapped)
        elif filter_status == 'CANCELLED':
            d_query = d_query.filter_by(status='CANCELLED')

    if search:
        search_term = f'%{search}%'
        d_query = d_query.filter(Deposit.reference.ilike(search_term))

    d_list = d_query.order_by(Deposit.created_at.desc()).all()

    # 4) Retraits (Withdrawal)
    w_query = Withdrawal.query.filter_by(user_id=current_user.id)

    if filter_status and filter_status != 'ALL':
        w_status_map = {'COMPLETED': 'COMPLETED', 'FAILED': 'FAILED', 'PENDING': 'WITHDRAW_PROCESSING'}
        mapped = w_status_map.get(filter_status)
        if mapped:
            w_query = w_query.filter_by(status=mapped)
        elif filter_status == 'CANCELLED':
            w_query = w_query.filter_by(status='CANCELLED')

    if search:
        search_term = f'%{search}%'
        w_query = w_query.filter(Withdrawal.reference.ilike(search_term))

    w_list = w_query.order_by(Withdrawal.created_at.desc()).all()

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

    from models import User

    entries = []

    # ---- Transferts ----
    for t in t_list:
        d = t.to_dict()
        d['type'] = 'transfer'
        d['receiver_country_name'] = country_names.get(t.receiver_country, t.receiver_country)
        d['receiver_country_flag'] = country_flags.get(t.receiver_country, '\U0001f30d')
        d['sender_country_name'] = country_names.get(t.sender_country, t.sender_country)
        d['sender_country_flag'] = country_flags.get(t.sender_country, '\U0001f30d')
        d['receiver_operator'] = t.receiver_operator
        d['fees'] = t.fees or 0
        d['total_amount'] = t.total_amount or 0
        entries.append(d)

    # ---- Paiements émis (type=payment_sent) ----
    for p in p_list:
        receiver = User.query.get(p.receiver_id) if p.receiver_id else None
        d = {
            'type': 'payment_sent',
            'reference': p.reference or f'PAY-{p.id}',
            'created_at': p.created_at.isoformat() if p.created_at else None,
            'receiver_name': receiver.fullname if receiver else 'Utilisateur',
            'receiver_phone': getattr(receiver, 'phone', '') or '',
            'receiver_country': '',
            'receiver_country_name': '',
            'receiver_country_flag': '\U0001f30d',
            'receiver_operator': 'TransAfrik',
            'amount': p.amount,
            'currency': p.currency or 'XOF',
            'fees': 0,
            'total_amount': p.amount,
            'status': p.status.upper() if p.status else 'COMPLETED',
        }
        entries.append(d)

    # ---- Paiements reçus (type=payment_received) ----
    for p in p_recv_list:
        sender = User.query.get(p.sender_id) if p.sender_id else None
        d = {
            'type': 'payment_received',
            'reference': p.reference or f'PAY-{p.id}',
            'created_at': p.created_at.isoformat() if p.created_at else None,
            'receiver_name': current_user.fullname,
            'receiver_phone': current_user.phone or '',
            'receiver_country': '',
            'receiver_country_name': '',
            'receiver_country_flag': '\U0001f30d',
            'receiver_operator': 'TransAfrik',
            'sender_name': sender.fullname if sender else 'Utilisateur',
            'sender_phone': getattr(sender, 'phone', '') or '',
            'amount': p.amount,
            'currency': p.currency or 'XOF',
            'fees': 0,
            'total_amount': p.amount,
            'status': p.status.upper() if p.status else 'COMPLETED',
        }
        entries.append(d)

    # ---- Dépôts ----
    for dep in d_list:
        dep_status = dep.status or 'UNKNOWN'
        if dep_status == 'PAYMENT_PROCESSING':
            dep_status = 'PENDING'
        entries.append({
            'type': 'deposit',
            'reference': dep.reference,
            'created_at': dep.created_at.isoformat() if dep.created_at else None,
            'receiver_name': current_user.fullname,
            'receiver_phone': current_user.phone or '',
            'receiver_country': dep.country or '',
            'receiver_country_name': country_names.get(dep.country, dep.country or ''),
            'receiver_country_flag': country_flags.get(dep.country, '\U0001f30d'),
            'receiver_operator': dep.operator or 'Mobile Money',
            'amount': dep.amount,
            'currency': dep.currency or 'XOF',
            'fees': dep.fees or 0,
            'total_amount': dep.total_amount or dep.amount,
            'status': dep_status,
        })

    # ---- Retraits ----
    for w in w_list:
        w_status = w.status or 'UNKNOWN'
        if w_status == 'WITHDRAW_PROCESSING':
            w_status = 'PENDING'
        entries.append({
            'type': 'withdraw',
            'reference': w.reference,
            'created_at': w.created_at.isoformat() if w.created_at else None,
            'receiver_name': w.recipient_name or 'Destinataire',
            'receiver_phone': w.recipient_phone or '',
            'receiver_country': w.recipient_country or '',
            'receiver_country_name': country_names.get(w.recipient_country, w.recipient_country or ''),
            'receiver_country_flag': country_flags.get(w.recipient_country, '\U0001f30d'),
            'receiver_operator': w.recipient_operator or 'Mobile Money',
            'amount': w.amount,
            'currency': w.currency or 'XOF',
            'fees': w.fees or 0,
            'total_amount': w.total_debited or w.amount,
            'status': w_status,
        })

    # Trier par date décroissante
    entries.sort(key=lambda x: x['created_at'] or '', reverse=True)

    # Pagination manuelle
    total = len(entries)
    pages = max(1, (total + per_page - 1) // per_page) if total > 0 else 1
    page = max(1, min(page, pages))
    start = (page - 1) * per_page
    end = start + per_page
    chunk = entries[start:end]

    return jsonify({
        'success': True,
        'transfers': chunk,
        'page': page,
        'pages': pages,
        'total': total,
        'has_next': page < pages,
        'has_prev': page > 1,
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
    # Diagnostic : afficher tous les headers reçus
    print(dict(request.headers))
    signature = request.headers.get('x-private-key', '')
    raw_body = request.get_data()
    if not _verify_webhook_signature(raw_body, signature):
        webhook_logger.warning('Signature invalide — webhook dépôt rejeté')
        return jsonify({'success': False, 'message': 'Signature invalide'}), 403

    payload = request.get_json(silent=True) or {}
    if not payload:
        return jsonify({'success': False, 'message': 'Payload invalide'}), 400

    data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
    external_ref = data.get('external_reference') or payload.get('external_reference') or payload.get('order_id') or ''
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

        # ---- Notification push à l'utilisateur ----
        try:
            send_push_to_user(
                user_id=deposit.user_id,
                title="💰 Dépôt confirmé",
                body=f"Votre dépôt de {deposit.amount:,} {deposit.currency} a été crédité avec succès sur votre compte TransAfrik.",
                url="/wallet",
                tag=f"deposit-{deposit.reference}",
                data={"reference": deposit.reference, "amount": deposit.amount, "currency": deposit.currency},
            )
            app.logger.info(f"PUSH | ENVOYÉE | Dépôt confirmé | user={deposit.user_id} | amount={deposit.amount}")
            # Notification in-app
            notif = Notification(
                user_id=deposit.user_id,
                title="Dépôt confirmé",
                message=f"Votre dépôt de {deposit.amount:,} {deposit.currency} a été crédité avec succès.",
                type="deposit_success",
                data={"reference": deposit.reference},
            )
            db.session.add(notif)
            db.session.commit()
        except Exception as push_err:
            app.logger.warning(f"[PUSH] Échec notification dépôt: {push_err}")

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
            'id': resolved_user.id if resolved_user else (parsed.get('user_id') if parsed else None),
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


# ==================== SETTINGS / PARAMÈTRES ====================

@app.route('/settings')
@login_required
def settings_page():
    """Page paramètres du compte."""
    return render_template('settings.html', user=current_user)


# ==================== CONVERTISSEUR DE DEVISES ====================

@app.route('/converter')
@login_required
def converter_page():
    """Page convertisseur de devises."""
    return render_template('converter.html')


@app.route('/api/converter')
@login_required
def api_converter():
    """Endpoint API : conversion de devise via SoleasPay.
    Format attendu de SoleasPay : {"success": true, "data": {"USD": "1.741196"}}
    Format renvoyé au frontend : {"success": true, "amount": 1000, "from": "XOF", "to": "USD", "result": 1.74, "rate": 0.00174}
    """
    import time as time_mod
    t0 = time_mod.time()

    raw_amount = request.args.get('amount', '1')
    from_currency = request.args.get('from', 'USD')
    to_currency = request.args.get('to', 'XOF')

    # Validation du montant
    try:
        amount = float(raw_amount)
        if amount <= 0:
            app.logger.warning(f'[CONVERTER] Montant invalide: {raw_amount}')
            return jsonify({'success': False, 'message': 'Montant invalide.'}), 400
    except (ValueError, TypeError):
        app.logger.warning(f'[CONVERTER] Montant non numérique: {raw_amount}')
        return jsonify({'success': False, 'message': 'Montant invalide.'}), 400

    from_currency = from_currency.upper().strip()
    to_currency = to_currency.upper().strip()

    if not from_currency or not to_currency:
        return jsonify({'success': False, 'message': 'Devises requises.'}), 400

    # Cas même devise : pas d'appel API
    if from_currency == to_currency:
        app.logger.info(f'[CONVERTER] Même devise {from_currency} — taux 1:1')
        return jsonify({
            'success': True,
            'amount': amount,
            'from': from_currency,
            'to': to_currency,
            'result': amount,
            'rate': 1.0,
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'passthrough',
        })

    app.logger.info('=' * 45)
    app.logger.info(f'[CONVERTER] Amount : {amount}')
    app.logger.info(f'[CONVERTER] From   : {from_currency}')
    app.logger.info(f'[CONVERTER] To     : {to_currency}')

    from services.soleaspay import convert_currency
    raw = convert_currency(amount=amount, from_currency=from_currency, to_currency=to_currency)

    elapsed = round((time_mod.time() - t0) * 1000)
    app.logger.info(f'[CONVERTER] Temps SoleasPay : {elapsed} ms')
    app.logger.info(f'[CONVERTER] Réponse brute    : {raw}')

    # Erreur réseau / timeout
    if not raw.get('success'):
        app.logger.error(f'[CONVERTER] ÉCHEC — {raw.get("message")}')
        return jsonify({
            'success': False,
            'message': 'Impossible de récupérer le taux de change.',
        }), 502

    # Parser la structure SoleasPay : {"success": true, "data": {"USD": "1.741196"}}
    data_block = raw.get('data', {})
    if not isinstance(data_block, dict) or not data_block:
        app.logger.error(f'[CONVERTER] Bloc data absent ou invalide: {raw}')
        return jsonify({
            'success': False,
            'message': 'Impossible de récupérer le taux de change.',
        }), 502

    # La clé dans data est le code de la devise cible (ex: "USD")
    converted_value = data_block.get(to_currency)
    if converted_value is None:
        app.logger.error(f'[CONVERTER] Clé {to_currency} absente de data: {data_block}')
        return jsonify({
            'success': False,
            'message': 'Impossible de récupérer le taux de change.',
        }), 502

    try:
        converted_value = float(converted_value)
    except (ValueError, TypeError):
        app.logger.error(f'[CONVERTER] Valeur non numérique: {converted_value}')
        return jsonify({
            'success': False,
            'message': 'Impossible de récupérer le taux de change.',
        }), 502

    rate = converted_value / amount

    result = {
        'success': True,
        'amount': amount,
        'from': from_currency,
        'to': to_currency,
        'result': converted_value,
        'rate': rate,
        'timestamp': datetime.utcnow().isoformat(),
        'response_time_ms': elapsed,
        'source': 'soleaspay',
    }

    app.logger.info(f'[CONVERTER] Résultat : {amount} {from_currency} = {converted_value} {to_currency} (taux: {rate})')
    app.logger.info('=' * 45)
    return jsonify(result)


# ==================== API PARAMÈTRES / SETTINGS ====================

@app.route('/api/settings/update-profile', methods=['POST'])
@login_required
def api_update_profile():
    """Mettre à jour le nom et le pays."""
    data = request.get_json()
    fullname = data.get('fullname', '').strip()
    country = data.get('country', '').strip()

    if not fullname or len(fullname) < 2:
        return jsonify({'success': False, 'message': 'Le nom doit contenir au moins 2 caractères.'}), 400
    if not country:
        return jsonify({'success': False, 'message': 'Veuillez sélectionner un pays.'}), 400

    current_user.fullname = fullname
    current_user.country = country.upper()
    db.session.commit()
    app.logger.info(f'[SETTINGS] Profil mis à jour : {fullname}, {country}')
    return jsonify({
        'success': True,
        'message': 'Profil mis à jour avec succès.',
        'fullname': fullname,
        'country': country.upper(),
    })


@app.route('/api/settings/change-password', methods=['POST'])
@login_required
def api_change_password():
    """Changer le mot de passe."""
    data = request.get_json()
    current_pw = data.get('current_password', '')
    new_pw = data.get('new_password', '')
    confirm_pw = data.get('confirm_password', '')

    if not current_pw or not new_pw or not confirm_pw:
        return jsonify({'success': False, 'message': 'Tous les champs sont obligatoires.'}), 400
    if not check_password_hash(current_user.password_hash, current_pw):
        return jsonify({'success': False, 'message': 'Mot de passe actuel incorrect.'}), 400
    if len(new_pw) < 8:
        return jsonify({'success': False, 'message': 'Le nouveau mot de passe doit contenir au moins 8 caractères.'}), 400
    if new_pw != confirm_pw:
        return jsonify({'success': False, 'message': 'Les mots de passe ne correspondent pas.'}), 400

    current_user.password_hash = generate_password_hash(new_pw)
    db.session.commit()
    app.logger.info(f'[SETTINGS] Mot de passe changé pour {current_user.email}')
    return jsonify({'success': True, 'message': 'Mot de passe mis à jour avec succès.'})


@app.route('/api/settings/change-phone', methods=['POST'])
@login_required
def api_change_phone():
    """Changer le numéro de téléphone."""
    data = request.get_json()
    new_phone = data.get('phone', '').strip()

    if not new_phone or len(new_phone) < 7:
        return jsonify({'success': False, 'message': 'Numéro de téléphone invalide.'}), 400

    # Vérifier si le numéro est déjà utilisé
    existing = User.query.filter_by(phone=new_phone).first()
    if existing and existing.id != current_user.id:
        return jsonify({'success': False, 'message': 'Ce numéro est déjà utilisé.'}), 400

    current_user.phone = new_phone
    db.session.commit()
    app.logger.info(f'[SETTINGS] Téléphone changé pour {current_user.email}: {new_phone}')
    return jsonify({'success': True, 'message': 'Numéro mis à jour avec succès.', 'phone': new_phone})


@app.route('/api/settings/change-email', methods=['POST'])
@login_required
def api_change_email():
    """Changer l'adresse email."""
    data = request.get_json()
    new_email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not new_email or '@' not in new_email:
        return jsonify({'success': False, 'message': 'Adresse email invalide.'}), 400
    if not check_password_hash(current_user.password_hash, password):
        return jsonify({'success': False, 'message': 'Mot de passe incorrect.'}), 400

    existing = User.query.filter_by(email=new_email).first()
    if existing and existing.id != current_user.id:
        return jsonify({'success': False, 'message': 'Cet email est déjà utilisé.'}), 400

    current_user.email = new_email
    db.session.commit()
    app.logger.info(f'[SETTINGS] Email changé : {current_user.email}')
    return jsonify({'success': True, 'message': 'Email mis à jour avec succès.', 'email': new_email})


@app.route('/api/settings/change-pin', methods=['POST'])
@login_required
def api_change_pin():
    """Changer le code PIN de transaction (4-6 chiffres)."""
    data = request.get_json()
    password = data.get('password', '')
    new_pin = data.get('pin', '')
    confirm_pin = data.get('confirm_pin', '')

    if not password or not new_pin:
        return jsonify({'success': False, 'message': 'Tous les champs sont obligatoires.'}), 400
    if not check_password_hash(current_user.password_hash, password):
        return jsonify({'success': False, 'message': 'Mot de passe incorrect.'}), 400
    if not new_pin.isdigit() or len(new_pin) < 4 or len(new_pin) > 6:
        return jsonify({'success': False, 'message': 'Le PIN doit contenir 4 à 6 chiffres.'}), 400
    if new_pin != confirm_pin:
        return jsonify({'success': False, 'message': 'Les PIN ne correspondent pas.'}), 400

    current_user.pin_hash = generate_password_hash(new_pin)
    db.session.commit()
    app.logger.info(f'[SETTINGS] PIN changé pour {current_user.email}')
    return jsonify({'success': True, 'message': 'PIN de transaction mis à jour avec succès.'})


@app.route('/api/settings/update-preferences', methods=['POST'])
@login_required
def api_update_preferences():
    """Mettre à jour la langue et la devise."""
    data = request.get_json()
    lang = data.get('language', 'fr')
    currency = data.get('currency', 'XOF')

    if lang not in ('fr', 'en'):
        return jsonify({'success': False, 'message': 'Langue invalide.'}), 400

    current_user.language = lang
    current_user.currency = currency
    db.session.commit()
    app.logger.info(f'[SETTINGS] Préférences mises à jour : lang={lang}, currency={currency}')
    return jsonify({
        'success': True,
        'message': 'Préférences mises à jour.',
        'language': lang,
        'currency': currency,
    })


@app.route('/api/settings/export-data')
@login_required
def api_export_data():
    """Exporter toutes les données de l'utilisateur au format JSON."""
    user_data = {
        'fullname': current_user.fullname,
        'email': current_user.email,
        'phone': current_user.phone,
        'country': current_user.country,
        'currency': current_user.currency,
        'balance': current_user.balance,
        'pending_balance': current_user.pending_balance,
        'kyc_status': current_user.kyc_status,
        'language': current_user.language,
        'created_at': current_user.created_at.isoformat() if current_user.created_at else None,
        'last_login': current_user.last_login.isoformat() if current_user.last_login else None,
        'transactions_count': current_user.tx_count,
        'beneficiaries_count': current_user.beneficiary_count,
        'total_sent': current_user.total_sent,
        'total_received': current_user.total_received,
    }
    app.logger.info(f'[SETTINGS] Export données pour {current_user.email}')
    return jsonify({'success': True, 'data': user_data})


@app.route('/api/settings/report-problem', methods=['POST'])
@login_required
def api_report_problem():
    """Signaler un problème."""
    data = request.get_json()
    subject = data.get('subject', '').strip()
    description = data.get('description', '').strip()

    if not subject or not description:
        return jsonify({'success': False, 'message': 'Veuillez remplir tous les champs.'}), 400

    # En production, on enverrait un email ou créerait un ticket
    app.logger.warning(f'[REPORT] {current_user.email}: {subject} — {description}')
    return jsonify({'success': True, 'message': 'Merci ! Votre signalement a été enregistré. Notre équipe vous contactera dans les plus brefs délais.'})


@app.route('/api/settings/delete-account', methods=['POST'])
@login_required
def api_delete_account():
    """Supprimer le compte (soft delete)."""
    data = request.get_json()
    password = data.get('password', '')

    if not check_password_hash(current_user.password_hash, password):
        return jsonify({'success': False, 'message': 'Mot de passe incorrect.'}), 400

    current_user.is_deleted = True
    current_user.is_active = False
    db.session.commit()
    logout_user()
    app.logger.warning(f'[SETTINGS] Compte supprimé (soft) : {current_user.email}')
    return jsonify({'success': True, 'message': 'Compte supprimé avec succès.', 'redirect': url_for('index')})


@app.route('/api/settings/session-info')
@login_required
def api_session_info():
    """Infos sur la session actuelle."""
    user_agent = request.headers.get('User-Agent', 'Inconnu')
    ip = request.remote_addr
    return jsonify({
        'success': True,
        'ip': ip,
        'user_agent': user_agent,
        'last_login': current_user.last_login.isoformat() if current_user.last_login else None,
        'created_at': current_user.created_at.isoformat() if current_user.created_at else None,
    })


# ==================== KYC ====================
@app.route('/kyc')
@login_required
def kyc_page():
    kyc = KycRequest.query.filter_by(user_id=current_user.id).first()

    return render_template(
        "kyc.html",
        user=current_user,
        kyc=kyc  )
@app.route('/api/kyc/save-step1', methods=['POST'])
@login_required
def api_kyc_save_step1():
    """Sauvegarde automatique étape 1 — Informations personnelles."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Données requises.'}), 400

    kyc = KycRequest.query.filter_by(user_id=current_user.id).first()
    if not kyc:
        kyc = KycRequest(user_id=current_user.id)
        db.session.add(kyc)

    kyc.first_name = data.get('first_name', '').strip() or kyc.first_name
    kyc.last_name = data.get('last_name', '').strip() or kyc.last_name
    try:
        bd = data.get('birth_date')
        if bd:
            kyc.birth_date = datetime.strptime(bd, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        pass
    kyc.gender = data.get('gender') or kyc.gender
    kyc.nationality = data.get('nationality', '').strip().upper() or kyc.nationality
    kyc.profession = data.get('profession', '').strip() or kyc.profession
    kyc.address = data.get('address', '').strip() or kyc.address
    kyc.city = data.get('city', '').strip() or kyc.city
    kyc.postal_code = data.get('postal_code', '').strip() or kyc.postal_code
    kyc.country = data.get('country', '').strip().upper() or kyc.country
    kyc.phone = data.get('phone', '').strip() or kyc.phone or current_user.phone
    kyc.email = data.get('email', '').strip().lower() or kyc.email or current_user.email

    if kyc.status == 'NOT_STARTED':
        kyc.status = 'DRAFT'

    kyc.updated_at = datetime.utcnow()
    kyc.ip_address = request.remote_addr
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Informations sauvegardées.',
        'kyc': kyc.to_dict(),
    })


@app.route('/api/kyc/save-step2', methods=['POST'])
@login_required
def api_kyc_save_step2():
    """Sauvegarde étape 2 — Type de document."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Données requises.'}), 400

    kyc = KycRequest.query.filter_by(user_id=current_user.id).first()
    if not kyc:
        kyc = KycRequest(user_id=current_user.id)
        db.session.add(kyc)

    doc_type = data.get('document_type', '').strip()
    if doc_type not in KycRequest.DOCUMENT_TYPES:
        return jsonify({'success': False, 'message': 'Type de document invalide.'}), 400

    kyc.document_type = doc_type
    if kyc.status == 'NOT_STARTED':
        kyc.status = 'DRAFT'
    kyc.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Type de document sauvegardé.',
        'kyc': kyc.to_dict(),
    })


def _allowed_kyc_file(filename):
    """Vérifie l'extension du fichier uploadé."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ('jpg', 'jpeg', 'png', 'pdf')


def _sanitize_kyc_filename(filename, prefix='kyc'):
    """Génère un nom de fichier sécurisé."""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
    ts = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
    return f'{prefix}_{ts}.{ext}'


@app.route('/api/kyc/upload', methods=['POST'])
@login_required
def api_kyc_upload():
    """Upload de fichier pour document recto, verso ou selfie."""
    file_type = request.form.get('type', 'front')  # front | back | selfie

    if file_type not in ('front', 'back', 'selfie'):
        return jsonify({'success': False, 'message': 'Type de fichier invalide.'}), 400

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Aucun fichier.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Fichier vide.'}), 400

    if not _allowed_kyc_file(file.filename):
        return jsonify({'success': False, 'message': 'Format non autorisé. Utilisez JPG, JPEG, PNG ou PDF.'}), 400

    # Vérifier taille max 10 Mo
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > 10 * 1024 * 1024:
        return jsonify({'success': False, 'message': 'Fichier trop volumineux (max 10 Mo).'}), 400

    kyc = KycRequest.query.filter_by(user_id=current_user.id).first()
    if not kyc:
        kyc = KycRequest(user_id=current_user.id)
        db.session.add(kyc)
        db.session.flush()

    kyc_dir = os.path.join(app.root_path, 'uploads', 'kyc')
    os.makedirs(kyc_dir, exist_ok=True)

    filename = _sanitize_kyc_filename(file.filename, prefix=f'kyc_{current_user.id}_{file_type}')
    filepath = os.path.join(kyc_dir, filename)
    file.save(filepath)

    # Supprimer l'ancien fichier si existe
    old_file = getattr(kyc, f'document_{file_type}' if file_type != 'selfie' else 'selfie', None)
    if old_file:
        old_path = os.path.join(kyc_dir, old_file)
        if os.path.exists(old_path):
            os.remove(old_path)

    if file_type == 'front':
        kyc.document_front = filename
    elif file_type == 'back':
        kyc.document_back = filename
    elif file_type == 'selfie':
        kyc.selfie = filename

    if kyc.status == 'NOT_STARTED':
        kyc.status = 'DRAFT'
    kyc.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Fichier téléchargé avec succès.',
        'kyc': kyc.to_dict(),
    })


@app.route('/api/kyc/submit', methods=['POST'])
@login_required
def api_kyc_submit():
    """Soumettre le dossier KYC pour vérification."""
    kyc = KycRequest.query.filter_by(user_id=current_user.id).first()

    if not kyc:
        return jsonify({'success': False, 'message': 'Aucun dossier KYC. Commencez par remplir vos informations.'}), 400

    if kyc.status in ('SUBMITTED', 'UNDER_REVIEW', 'APPROVED'):
        return jsonify({'success': False, 'message': 'Votre dossier a déjà été soumis ou est en cours de vérification.'}), 400

    # Vérifications minimales
    missing = []
    if not kyc.first_name:
        missing.append('Prénom')
    if not kyc.last_name:
        missing.append('Nom')
    if not kyc.birth_date:
        missing.append('Date de naissance')
    if not kyc.document_type:
        missing.append('Type de document')
    if not kyc.document_front:
        missing.append('Document (recto)')

    if missing:
        return jsonify({
            'success': False,
            'message': f'Informations manquantes : {", ".join(missing)}.',
        }), 400

    kyc.status = 'SUBMITTED'
    kyc.submitted_at = datetime.utcnow()
    kyc.updated_at = datetime.utcnow()
    kyc.ip_address = request.remote_addr
    kyc.device_info = request.headers.get('User-Agent', '')[:500]

    # Mise à jour du statut KYC de l'utilisateur
    current_user.kyc_status = 'pending'

    db.session.commit()
    app.logger.info(f'[KYC] Dossier soumis : {kyc.reference} par {current_user.email}')

    return jsonify({
        'success': True,
        'message': 'Votre dossier KYC a été soumis avec succès. Nous vous tiendrons informé.',
        'kyc': kyc.to_dict(),
    })


@app.route('/api/kyc/status')
@login_required
def api_kyc_status():
    """Obtenir le statut KYC actuel."""
    kyc = KycRequest.query.filter_by(user_id=current_user.id).first()
    if not kyc:
        return jsonify({
            'success': True,
            'kyc_exists': False,
            'status': 'NOT_STARTED',
            'progress_percent': 0,
        })

    return jsonify({
        'success': True,
        'kyc_exists': True,
        'kyc': kyc.to_dict(),
    })

# ==================== NOTIFICATIONS ====================

@app.route('/notifications')
@login_required
def notifications_page():
    """Page du centre de notifications."""
    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .limit(100).all()
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template(
        'notifications.html',
        user=current_user,
        notifications=notifications,
        unread_count=unread_count,
    )


@app.route('/notifications/read/<int:notification_id>', methods=['POST'])
@login_required
def notifications_read_one(notification_id):
    """Marque une notification comme lue."""
    notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first()
    if not notification:
        return jsonify({'success': False, 'message': 'Notification introuvable.'}), 404

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.session.commit()

    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'success': True, 'unread_count': unread_count})


@app.route('/notifications/read-all', methods=['POST'])
@login_required
def notifications_read_all():
    """Marque toutes les notifications de l'utilisateur comme lues."""
    now = datetime.utcnow()
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({
        'is_read': True,
        'read_at': now,
    })
    db.session.commit()
    return jsonify({'success': True, 'unread_count': 0})


@app.route('/notifications/delete/<int:notification_id>', methods=['DELETE'])
@login_required
def notifications_delete_one(notification_id):
    """Supprime une notification."""
    notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first()
    if not notification:
        return jsonify({'success': False, 'message': 'Notification introuvable.'}), 404

    db.session.delete(notification)
    db.session.commit()

    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'success': True, 'unread_count': unread_count})


@app.route('/api/notifications')
@login_required
def api_notifications():
    """API : retourne les notifications récentes et le nombre de non lues."""
    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .limit(50).all()
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()

    return jsonify({
        'success': True,
        'unread_count': unread_count,
        'notifications': [n.to_dict() for n in notifications],
    })


@app.context_processor
def inject_dashboard_globals():
    if current_user.is_authenticated:
        unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        return dict(
            unread_notifications=unread_count,
            country_flags=COUNTRY_FLAGS,
            country_names=COUNTRY_NAMES,
        )

    return dict(
        unread_notifications=0,
        country_flags=COUNTRY_FLAGS,
        country_names=COUNTRY_NAMES,
    )
# ==================== SUPPORT ====================

@app.route('/support')
@login_required
def support_page():
    """Page du centre d'assistance."""
    tickets = SupportTicket.query.filter_by(user_id=current_user.id).order_by(
        SupportTicket.created_at.desc()
    ).all()
    return render_template('support.html', user=current_user, tickets=tickets)


@app.route('/support/ticket/create', methods=['POST'])
@login_required
def support_create_ticket():
    """Créer un nouveau ticket de support."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Données requises.'}), 400

    subject = data.get('subject', '').strip()
    category = data.get('category', 'Other').strip()
    priority = data.get('priority', 'NORMAL').strip()
    message = data.get('message', '').strip()
    attachment = data.get('attachment', '').strip() or None

    if not subject or not message:
        return jsonify({'success': False, 'message': 'Sujet et message requis.'}), 400

    if category not in SupportTicket.CATEGORY_CHOICES:
        category = 'Other'
    if priority not in SupportTicket.PRIORITY_CHOICES:
        priority = 'NORMAL'

    ticket = SupportTicket(
        user_id=current_user.id,
        subject=subject,
        category=category,
        priority=priority,
        message=message,
        attachment=attachment,
    )
    db.session.add(ticket)
    db.session.commit()

    app.logger.info(f'[SUPPORT] Ticket créé: {ticket.ticket_number} par {current_user.email}')

    return jsonify({
        'success': True,
        'message': 'Ticket créé avec succès.',
        'ticket': ticket.to_dict(),
    })


@app.route('/support/tickets')
@login_required
def support_get_tickets():
    """Récupérer tous les tickets de l'utilisateur."""
    tickets = SupportTicket.query.filter_by(user_id=current_user.id).order_by(
        SupportTicket.created_at.desc()
    ).all()
    return jsonify({
        'success': True,
        'tickets': [t.to_dict() for t in tickets],
    })


@app.route('/support/ticket/<int:ticket_id>')
@login_required
def support_get_ticket(ticket_id):
    """Récupérer un ticket et ses messages."""
    ticket = SupportTicket.query.filter_by(id=ticket_id, user_id=current_user.id).first()
    if not ticket:
        return jsonify({'success': False, 'message': 'Ticket introuvable.'}), 404

    msgs = ticket.messages.order_by(SupportMessage.created_at.asc()).all()
    return jsonify({
        'success': True,
        'ticket': ticket.to_dict(),
        'messages': [m.to_dict() for m in msgs],
    })


@app.route('/support/message/send', methods=['POST'])
@login_required
def support_send_message():
    """Envoyer un message dans un ticket."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Données requises.'}), 400

    ticket_id = data.get('ticket_id')
    message = data.get('message', '').strip()
    attachment = data.get('attachment', '').strip() or None

    if not ticket_id or not message:
        return jsonify({'success': False, 'message': 'Ticket et message requis.'}), 400

    ticket = SupportTicket.query.filter_by(id=ticket_id, user_id=current_user.id).first()
    if not ticket:
        return jsonify({'success': False, 'message': 'Ticket introuvable.'}), 404

    if ticket.status in ('CLOSED', 'RESOLVED'):
        return jsonify({'success': False, 'message': 'Ce ticket est fermé. Créez un nouveau ticket si nécessaire.'}), 400

    msg = SupportMessage(
        ticket_id=ticket.id,
        sender_type='user',
        sender_id=current_user.id,
        message=message,
        attachment=attachment,
    )
    db.session.add(msg)
    ticket.status = 'WAITING_USER'
    ticket.updated_at = datetime.utcnow()
    db.session.commit()

    app.logger.info(f'[SUPPORT] Message envoyé sur ticket {ticket.ticket_number}')

    return jsonify({
        'success': True,
        'message': 'Message envoyé.',
        'chat_message': msg.to_dict(),
        'ticket': ticket.to_dict(),
    })


@app.route('/support/upload', methods=['POST'])
@login_required
def support_upload():
    """Upload de pièce jointe pour le support."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Aucun fichier.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Fichier vide.'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
    if ext not in ('jpg', 'jpeg', 'png', 'pdf'):
        return jsonify({'success': False, 'message': 'Format non autorisé (JPG, PNG, PDF).'}), 400

    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > 10 * 1024 * 1024:
        return jsonify({'success': False, 'message': 'Fichier trop volumineux (max 10 Mo).'}), 400

    upload_dir = os.path.join(app.root_path, 'uploads', 'support')
    os.makedirs(upload_dir, exist_ok=True)

    ts = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
    filename = f'support_{current_user.id}_{ts}.{ext}'
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    return jsonify({
        'success': True,
        'message': 'Fichier téléchargé.',
        'filename': filename,
        'path': f'/uploads/support/{filename}',
    })


# ══════════════════════════════════════════════════════════════════════════
# PUSH NOTIFICATIONS — API routes
# ══════════════════════════════════════════════════════════════════════════

@app.route('/api/push/vapid-public-key')
def push_vapid_public_key():
    """Expose la clé publique VAPID pour le frontend JS."""
    from services.push_service import get_public_key_for_frontend
    key = get_public_key_for_frontend()
    return jsonify({'public_key': key})


@app.route('/api/push/subscribe', methods=['POST'])
@login_required
def push_subscribe():
    """Enregistre un abonnement Push depuis le navigateur."""
    from services.push_service import save_subscription
    data = request.get_json(silent=True) or {}
    subscription = data.get('subscription', {})
    user_agent = request.headers.get('User-Agent', '')

    result = save_subscription(
        user_id=current_user.id,
        subscription_data=subscription,
        user_agent=user_agent,
    )
    return jsonify(result), 200 if result.get('success') else 400


@app.route('/api/push/unsubscribe', methods=['POST'])
@login_required
def push_unsubscribe():
    """Supprime un abonnement Push."""
    from services.push_service import remove_subscription
    data = request.get_json(silent=True) or {}
    endpoint = data.get('endpoint', '').strip()

    if not endpoint:
        return jsonify({'success': False, 'error': 'Aucun endpoint fourni.'}), 400

    result = remove_subscription(user_id=current_user.id, endpoint=endpoint)
    return jsonify(result)


@app.route('/api/push/status', methods=['GET'])
@login_required
def push_status():
    """Retourne le statut des abonnements Push de l'utilisateur connecté."""
    from services.push_service import get_user_subscriptions

    subs = get_user_subscriptions(current_user.id)
    has_push = Notification.permission if hasattr(__builtins__, 'Notification') else 'denied'

    return jsonify({
        'success': True,
        'subscriptions': subs,
        'count': len(subs),
        'notification_permission': Notification.permission if 'Notification' in request.headers.get('User-Agent', '') else 'unknown',
        'push_supported': True,
    })


@app.route('/api/push/send-test', methods=['POST'])
@login_required
def push_send_test():
    """Envoie une notification push de test à l'utilisateur connecté."""
    from services.push_service import send_push_to_user

    data = request.get_json(silent=True) or {}
    title = data.get('title', 'Test TransAfrik')
    body = data.get('body', 'Ceci est une notification de test ! 👍')
    url = data.get('url', '/')

    result = send_push_to_user(
        user_id=current_user.id,
        title=title,
        body=body,
        url=url,
    )
    return jsonify(result)


# ══════════════════════════════════════════════════════════════════════════
# RECEIVE MONEY — DEMANDE DE PAIEMENT
# ══════════════════════════════════════════════════════════════════════════

@app.route('/receive')
@login_required
def receive_page():
    """Page de demande de paiement — créer un QR code / lien de paiement."""
    recent_payments = get_recent_received_payments(current_user.id, limit=5)
    return render_template('receive_money.html',
                           user=current_user,
                           recent_payments=recent_payments,
                           country_flags=COUNTRY_FLAGS,
                           country_names=COUNTRY_NAMES)


@app.route('/api/receive/create', methods=['POST'])
@login_required
def api_create_payment_request():
    """Crée une demande de paiement."""
    data = request.get_json(silent=True) or {}
    amount = int(data.get('amount', 0))
    currency = data.get('currency', 'XOF').upper()
    description = data.get('description', '').strip()
    expiry_hours = int(data.get('expiry_hours', 48))

    if amount <= 0:
        return jsonify({'success': False, 'message': 'Montant invalide.'}), 400

    success, payment_request, error = create_payment_request(
        user=current_user,
        amount=amount,
        currency=currency,
        description=description,
        expiry_hours=expiry_hours,
    )

    if not success:
        return jsonify({'success': False, 'message': error}), 400

    return jsonify({
        'success': True,
        'message': 'Demande de paiement créée avec succès.',
        'request': payment_request.to_dict(),
    })


@app.route('/api/receive/cancel', methods=['POST'])
@login_required
def api_cancel_payment_request():
    """Annule une demande de paiement."""
    data = request.get_json(silent=True) or {}
    request_code = data.get('request_code', '').strip()

    if not request_code:
        return jsonify({'success': False, 'message': 'Code de demande requis.'}), 400

    success, error = cancel_payment_request(current_user.id, request_code)
    if not success:
        return jsonify({'success': False, 'message': error}), 400

    return jsonify({'success': True, 'message': 'Demande annulée.'})


@app.route('/api/receive/list')
@login_required
def api_payment_requests_list():
    """Liste les demandes de paiement de l'utilisateur."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    result = get_user_payment_requests(current_user.id, page=page, per_page=per_page)
    return jsonify({'success': True, **result})


@app.route('/api/receive/recent-payments')
@login_required
def api_recent_received_payments():
    """Paiements récents reçus."""
    limit = request.args.get('limit', 10, type=int)
    payments = get_recent_received_payments(current_user.id, limit=limit)
    return jsonify({'success': True, 'payments': payments})


@app.route('/receive/qr/<request_code>')
@login_required
def receive_qr_page(request_code):
    """Affiche le QR code d'une demande de paiement."""
    pr = get_payment_request_by_code(request_code)
    if not pr or pr.receiver_id != current_user.id:
        flash('Demande introuvable.', 'error')
        return redirect(url_for('receive_page'))
    return render_template('receive_money.html',
                           user=current_user,
                           payment_request=pr,
                           show_qr=True,
                           country_flags=COUNTRY_FLAGS,
                           country_names=COUNTRY_NAMES)


@app.route('/request/<request_code>')
def public_payment_request_page(request_code):
    """Page publique pour payer une demande (accessible sans login)."""
    print("REQUEST TOKEN:", request_code)
    pr = get_payment_request_by_code(request_code)
    if not pr:
        return render_template('receive_pay.html',
                               payment_request=None,
                               receiver=None,
                               error_message='Demande de paiement introuvable ou expirée.')

    # Vérifier si expirée
    if pr.status == 'EXPIRED' or (pr.expires_at and pr.expires_at < datetime.utcnow()):
        if pr.status == 'PENDING':
            pr.status = 'EXPIRED'
            pr.updated_at = datetime.utcnow()
            db.session.commit()
        return render_template('receive_pay.html',
                               payment_request=pr,
                               receiver=User.query.get(pr.receiver_id),
                               error_message='Cette demande de paiement a expiré.')

    if pr.status == 'PAID':
        return render_template('receive_pay.html',
                               payment_request=pr,
                               receiver=User.query.get(pr.receiver_id),
                               error_message='Cette demande de paiement a déjà été payée.')

    receiver = User.query.get(pr.receiver_id)
    return render_template('receive_pay.html',
                           payment_request=pr,
                           receiver=receiver)


@app.route('/pay/@<username>')
def pay_username(username):
    """Page publique de paiement vers un utilisateur (accessible sans login)."""
    print("PAY LINK:", username)
    # Utiliser search_user_for_payment qui cherche par username, email, téléphone ou UUID
    target = search_user_for_payment(username)
    if not target:
        return render_template('receive_pay.html',
                               payment_request=None,
                               receiver=None,
                               error_message=f'Utilisateur "@{username}" introuvable.')

    # Vérifier si l'utilisateur a une demande de paiement active
    active_request = PaymentRequest.query.filter_by(
        receiver_id=target['id'],
        status='PENDING'
    ).first()

    if active_request and active_request.expires_at and active_request.expires_at >= datetime.utcnow():
        # Il y a une demande active, afficher la page de paiement avec cette demande
        receiver = User.query.get(active_request.receiver_id)
        return render_template('receive_pay.html',
                               payment_request=active_request,
                               receiver=receiver)

    # Pas de demande active, afficher une page de paiement libre
    from models import User as UserModel
    receiver = UserModel.query.get(target['id'])
    return render_template('receive_pay.html',
                           payment_request=None,
                           receiver=receiver)


@app.route('/api/receive/pay', methods=['POST'])
@login_required
def api_receive_pay():
    """Payer une demande de paiement."""
    data = request.get_json(silent=True) or {}
    request_code = data.get('request_code', '').strip()
    amount = int(data.get('amount', 0))
    currency = data.get('currency', 'XOF').upper()

    if not request_code:
        return jsonify({'success': False, 'message': 'Code de demande requis.'}), 400

    if amount <= 0:
        return jsonify({'success': False, 'message': 'Montant invalide.'}), 400

    pr = get_payment_request_by_code(request_code)
    if not pr:
        return jsonify({'success': False, 'message': 'Demande introuvable.'}), 404

    if pr.receiver_id == current_user.id:
        return jsonify({'success': False, 'message': 'Vous ne pouvez pas vous payer vous-même.'}), 400

    # Vérifier le solde
    if current_user.balance < amount:
        return jsonify({
            'success': False,
            'message': f'Solde insuffisant. Votre solde est de {current_user.balance} {currency}.',
        }), 400

    success, tx, error = process_receive_payment(
        request_code=request_code,
        sender_id=current_user.id,
        amount=amount,
        currency=currency,
    )

    if not success:
        return jsonify({'success': False, 'message': error}), 400

    # Envoyer notification push au receveur
    try:
        receiver_name = tx.receiver.fullname if tx.receiver else 'Utilisateur'
        send_push_to_user(
            user_id=tx.receiver_id,
            title='Nouveau paiement reçu ! 💸',
            body=f'{current_user.fullname} vous a envoyé {amount} {currency}.',
            url='/dashboard',
            tag='receive-payment',
            data={'transaction_ref': tx.reference, 'amount': amount, 'currency': currency},
        )
    except Exception as push_err:
        app.logger.warning(f'[PUSH] Échec notification paiement: {push_err}')

    return jsonify({
        'success': True,
        'message': 'Paiement effectué avec succès !',
        'transaction': tx.to_dict(),
    })


@app.route('/api/pay-to-receiver', methods=['POST'])
@login_required
def api_pay_to_receiver():
    """Paiement libre vers un utilisateur (sans demande de paiement)."""
    data = request.get_json(silent=True) or {}
    amount = int(data.get('amount', 0))
    currency = data.get('currency', 'XOF').upper()
    receiver_id = int(data.get('receiver_id', 0))

    if not receiver_id:
        return jsonify({'success': False, 'message': 'Destinataire requis.'}), 400

    if amount <= 0:
        return jsonify({'success': False, 'message': 'Montant invalide.'}), 400

    if receiver_id == current_user.id:
        return jsonify({'success': False, 'message': 'Vous ne pouvez pas vous payer vous-même.'}), 400

    # Vérifier le solde
    if current_user.balance < amount:
        return jsonify({
            'success': False,
            'message': f'Solde insuffisant. Votre solde est de {current_user.balance} {currency}.',
        }), 400

    success, result, error = process_free_payment(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        amount=amount,
        currency=currency,
    )

    if not success:
        return jsonify({'success': False, 'message': error}), 400

    tx = result['transaction']
    fee = result['fee']
    total_debit = amount + fee

    # Envoyer notification push au receveur
    try:
        receiver = User.query.get(receiver_id)
        receiver_name = receiver.fullname if receiver else 'Utilisateur'
        send_push_to_user(
            user_id=receiver_id,
            title='Nouveau paiement reçu ! 💸',
            body=f'{current_user.fullname} vous a envoyé {amount} {currency}.',
            url='/dashboard',
            tag='receive-payment',
            data={'transaction_ref': tx.reference, 'amount': amount, 'currency': currency},
        )
    except Exception as push_err:
        app.logger.warning(f'[PUSH] Échec notification paiement libre: {push_err}')

    return jsonify({
        'success': True,
        'message': f'Paiement de {amount} {currency} effectué avec succès ! (frais : {fee} {currency})',
        'transaction': tx.to_dict(),
        'fee': fee,
        'total_debit': total_debit,
    })


@app.route('/api/receive/search')
@login_required
def api_receive_search_user():
    """Recherche d'utilisateurs pour un paiement (liste de résultats)."""
    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return jsonify({'success': False, 'message': 'Recherche trop courte (min. 2 caractères).'}), 400

    results = search_users_for_payment(q, limit=10)

    # Filtrer l'utilisateur courant
    results = [u for u in results if u['id'] != current_user.id]

    if not results:
        return jsonify({'success': True, 'users': [], 'message': 'Aucun utilisateur trouvé.'})

    return jsonify({'success': True, 'users': results})


# --- ENVOI VERS UN UTILISATEUR (wallet interne → wallet interne, sans SoleasPay) ---
@app.route('/api/pay-to-user', methods=['POST'])
@login_required
def api_pay_to_user():
    """Envoi d'argent à un autre utilisateur TransAfrik (wallet à wallet).
    Pas de Mobile Money, pas de SoleasPay — purement interne.
    1. Vérifie le solde wallet
    2. Débite le wallet de l'expéditeur (montant + frais 2%)
    3. Crédite le wallet du destinataire
    4. Enregistre la TransactionReceive
    """
    import math

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Données JSON requises.'}), 400

    receiver_id = data.get('receiver_id')
    amount = int(data.get('amount', 0))
    currency = data.get('currency', 'XOF').upper()

    if not receiver_id:
        return jsonify({'success': False, 'message': 'Destinataire requis.'}), 400
    if amount <= 0:
        return jsonify({'success': False, 'message': 'Montant invalide (min. 500 XOF).'}), 400
    if amount < 500:
        return jsonify({'success': False, 'message': 'Montant minimum : 500 XOF.'}), 400

    # Récupérer le destinataire
    receiver = User.query.get(receiver_id)
    if not receiver:
        return jsonify({'success': False, 'message': 'Destinataire introuvable.'}), 404

    if receiver.id == current_user.id:
        return jsonify({'success': False, 'message': 'Vous ne pouvez pas vous envoyer de l\'argent.'}), 400

    # Frais plateforme : 2% plafonnés à 5000 XOF
    fee = min(math.ceil(amount * 0.02), 5000)
    total_debit = amount + fee

    # Vérifier le solde de l'expéditeur
    if (current_user.balance or 0) < total_debit:
        return jsonify({
            'success': False,
            'message': f'Solde insuffisant. Votre solde : {current_user.balance:,} {currency}. '
                       f'Total requis : {total_debit:,} {currency} (montant {amount:,} + frais {fee:,}).',
        }), 400

    # ---- Débiter l'expéditeur ----
    current_user.balance = (current_user.balance or 0) - total_debit
    current_user.used_daily = (current_user.used_daily or 0) + total_debit

    # ---- Créditer le destinataire (montant net) ----
    receiver.balance = (receiver.balance or 0) + amount

    # ---- Créer la TransactionReceive ----
    ref = generate_receive_reference()
    tx = TransactionReceive(
        payment_request_id=None,
        sender_id=current_user.id,
        receiver_id=receiver_id,
        amount=amount,
        currency=currency,
        status='completed',
        reference=ref,
    )
    db.session.add(tx)

    # ---- Créer une Transaction "send" pour l'historique ----
    send_tx = Transaction(
        user_id=current_user.id,
        type='send',
        amount=amount,
        currency=currency,
        fee=fee,
        status='success',
        recipient_name=receiver.fullname or receiver.username,
        recipient_phone=receiver.phone or '',
        recipient_country=receiver.country or '',
        recipient_operator='TransAfrik',
    )
    db.session.add(send_tx)

    db.session.commit()

    # Notification push au receveur
    try:
        send_push_to_user(
            user_id=receiver_id,
            title='Nouveau paiement reçu ! 💸',
            body=f'{current_user.fullname} vous a envoyé {amount:,} {currency}.',
            url='/dashboard',
            tag='receive-payment',
            data={'transaction_ref': ref, 'amount': amount, 'currency': currency},
        )
    except Exception as push_err:
        app.logger.warning(f'[PUSH] Échec notification paiement : {push_err}')

    return jsonify({
        'success': True,
        'message': f'Transfert de {amount:,} {currency} vers @{receiver.username} effectué avec succès.',
        'transaction': tx.to_dict() if hasattr(tx, 'to_dict') else {'id': tx.id, 'reference': ref},
        'fee': fee,
        'total_debit': total_debit,
        'amount': amount,
        'currency': currency,
        'receiver': {
            'id': receiver.id,
            'username': receiver.username,
            'fullname': receiver.fullname,
        },
    })


@app.route('/api/scan/lookup', methods=['POST'])
@login_required
def api_scan_lookup():
    """Recherche un utilisateur à partir du contenu du QR code.
    Reçoit: {"email": "email@exemple.com"} ou {"qr_data": "TAUSER:email@exemple.com"}
    Retourne: {"success": True, "user": {...}} ou {"success": False, "message": "..."}
    """
    data = request.get_json(silent=True) or {}
    raw = data.get('qr_data', data.get('email', '')).strip()

    if not raw:
        return jsonify({'success': False, 'message': 'Aucune donnée fournie.'}), 400

    # Parse le format TAUSER:email
    email = raw
    if raw.upper().startswith('TAUSER:'):
        email = raw[7:].strip()

    if not email or '@' not in email:
        return jsonify({'success': False, 'message': 'Format invalide. Utilisez TAUSER:email@exemple.com.'}), 400

    # Rechercher l'utilisateur par email exact
    user = User.query.filter_by(email=email.lower().strip()).first()

    if not user:
        return jsonify({'success': False, 'message': 'Utilisateur introuvable.'}), 404

    # Ne pas se payer soi-même
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'Vous ne pouvez pas vous payer vous-même.'}), 400

    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'fullname': user.fullname or user.username or 'Utilisateur',
            'username': user.username or '',
            'email': user.email,
            'phone': user.phone or '',
            'country': user.country or '',
            'currency': user.currency or 'XOF',
            'profile_picture': user.profile_picture or '',
            'kyc_status': user.kyc_status or '',
        }
    })


@app.route('/api/scan/pay', methods=['POST'])
@login_required
def api_scan_pay():
    """Effectue un paiement direct par scan QR.
    Reçoit: {"receiver_id": 123, "amount": 1000, "currency": "XOF"}
    Débite le sender, crédite le receiver, crée les transactions.
    """
    data = request.get_json(silent=True) or {}
    receiver_id = data.get('receiver_id')
    amount = data.get('amount')
    currency = data.get('currency', current_user.currency or 'XOF')

    # Validation
    try:
        receiver_id = int(receiver_id)
        amount = int(amount)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Données invalides.'}), 400

    if amount <= 0:
        return jsonify({'success': False, 'message': 'Le montant doit être supérieur à 0.'}), 400

    if receiver_id == current_user.id:
        return jsonify({'success': False, 'message': 'Vous ne pouvez pas vous payer vous-même.'}), 400

    # Vérifier que le receiver existe
    receiver = User.query.get(receiver_id)
    if not receiver:
        return jsonify({'success': False, 'message': 'Destinataire introuvable.'}), 404

    # Utiliser process_free_payment (alias process_wallet_to_wallet)
    success, result, error = process_wallet_to_wallet(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        amount=amount,
        currency=currency,
    )

    if not success:
        return jsonify({'success': False, 'message': error or 'Erreur lors du paiement.'}), 400

    tx = result.get('transaction') if isinstance(result, dict) else result
    fee = result.get('fee', 0) if isinstance(result, dict) else 0
    ref = tx.reference if hasattr(tx, 'reference') else ''

    # Notification push au receveur
    try:
        send_push_to_user(
            user_id=receiver_id,
            title='Nouveau paiement reçu ! 💸',
            body=f'{current_user.fullname or current_user.username} vous a envoyé {amount:,} {currency}.',
            url='/dashboard',
            tag='scan-payment',
            data={'transaction_ref': ref, 'amount': amount, 'currency': currency},
        )
    except Exception as push_err:
        app.logger.warning(f'[PUSH] Échec notification scan : {push_err}')

    return jsonify({
        'success': True,
        'message': f'Paiement de {amount:,} {currency} vers {receiver.fullname or receiver.username} effectué avec succès.',
        'transaction': {
            'reference': ref,
            'amount': amount,
            'currency': currency,
            'fee': fee,
        },
        'receiver': {
            'id': receiver.id,
            'fullname': receiver.fullname or receiver.username,
            'email': receiver.email,
        },
    })


# ══════════════════════════════════════════════════════════════════════════
# SEO ROUTES — sitemap.xml, robots.txt, manifest.webmanifest
# ══════════════════════════════════════════════════════════════════════════

@app.route('/sitemap.xml')
def seo_sitemap():
    """Génère dynamiquement le sitemap XML."""
    xml = generate_sitemap_xml()
    response = app.response_class(
        response=xml,
        status=200,
        mimetype='application/xml'
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@app.route('/robots.txt')
def seo_robots():
    """Sert le fichier robots.txt."""
    response = app.response_class(
        response=ROBOTS_TXT,
        status=200,
        mimetype='text/plain'
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@app.route('/manifest.webmanifest')
def seo_manifest():
    """Sert le manifest PWA au format .webmanifest."""
    manifest = {
        "name": "TransAfrik",
        "short_name": "TransAfrik",
        "description": SITE_DESCRIPTION,
        "start_url": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": SITE_BG_COLOR,
        "theme_color": SITE_THEME_COLOR,
        "lang": "fr",
        "scope": "/",
        "icons": [
            {
                "src": f"/static/img/icons/icon-72x72.png",
                "sizes": "72x72",
                "type": "image/png"
            },
            {
                "src": f"/static/img/icons/icon-96x96.png",
                "sizes": "96x96",
                "type": "image/png"
            },
            {
                "src": f"/static/img/icons/icon-128x128.png",
                "sizes": "128x128",
                "type": "image/png"
            },
            {
                "src": f"/static/img/icons/icon-144x144.png",
                "sizes": "144x144",
                "type": "image/png"
            },
            {
                "src": f"/static/img/icons/icon-152x152.png",
                "sizes": "152x152",
                "type": "image/png"
            },
            {
                "src": f"/static/img/icons/icon-192x192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": f"/static/img/icons/icon-384x384.png",
                "sizes": "384x384",
                "type": "image/png"
            },
            {
                "src": f"/static/img/icons/icon-512x512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": SITE_LOGO,
                "sizes": "512x512",
                "type": "image/jpeg",
                "purpose": "any"
            }
        ],
        "categories": ["finance", "utilities"],
        "prefer_related_applications": False,
        "related_applications": [],
        "shortcuts": [
            {
                "name": "Envoyer de l'argent",
                "short_name": "Envoyer",
                "description": "Envoyez de l'argent en Afrique",
                "url": "/send-money",
                "icons": [{"src": "/static/img/icons/icon-96x96.png", "sizes": "96x96"}]
            },
            {
                "name": "Scanner un QR Code",
                "short_name": "Scanner",
                "description": "Scannez pour payer",
                "url": "/scan",
                "icons": [{"src": "/static/img/icons/icon-96x96.png", "sizes": "96x96"}]
            }
        ]
    }
    response = app.response_class(
        response=json.dumps(manifest, indent=2, ensure_ascii=False),
        status=200,
        mimetype='application/manifest+json'
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


# ══════════════════════════════════════════════════════════════════════════
# ERROR HANDLERS — Pages d'erreur SEO-friendly
# ══════════════════════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found_error(e):
    """Page 404 personnalisée."""
    seo = get_seo_context(path="/404")
    seo["seo_title"] = "Page introuvable — Erreur 404 | TransAfrik"
    seo["seo_description"] = "La page que vous cherchez n'existe pas ou a été déplacée."
    seo["seo_robots"] = "noindex, follow"
    seo["error_code"] = 404
    seo["error_title"] = "Page introuvable"
    seo["error_message"] = "La page que vous cherchez n'existe pas ou a été déplacée."
    return render_template('error.html', **seo), 404


@app.errorhandler(403)
def forbidden_error(e):
    """Page 403 personnalisée."""
    seo = get_seo_context(path="/403")
    seo["seo_title"] = "Accès refusé — Erreur 403 | TransAfrik"
    seo["seo_description"] = "Vous n'avez pas les permissions nécessaires pour accéder à cette page."
    seo["seo_robots"] = "noindex, follow"
    seo["error_code"] = 403
    seo["error_title"] = "Accès refusé"
    seo["error_message"] = "Vous n'avez pas les permissions pour accéder à cette ressource."
    return render_template('error.html', **seo), 403


@app.errorhandler(500)
def internal_error(e):
    """Page 500 personnalisée."""
    seo = get_seo_context(path="/500")
    seo["seo_title"] = "Erreur serveur — Erreur 500 | TransAfrik"
    seo["seo_description"] = "Une erreur interne est survenue. Notre équipe a été notifiée."
    seo["seo_robots"] = "noindex, follow"
    seo["error_code"] = 500
    seo["error_title"] = "Erreur serveur"
    seo["error_message"] = "Une erreur interne est survenue. Veuillez réessayer dans quelques instants."
    return render_template('error.html', **seo), 500


# ══════════════════════════════════════════════════════════════════════════
# SECURITY HEADERS (after_request)
# ══════════════════════════════════════════════════════════════════════════

@app.after_request
def add_security_headers(response):
    """Ajoute les en-têtes de sécurité à toutes les réponses."""
    # X-Content-Type-Options
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # Referrer-Policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # Permissions-Policy
    response.headers['Permissions-Policy'] = (
        'camera=(self), microphone=(), geolocation=(self), '
        'payment=(self), usb=(), bluetooth=(), '
        'accelerometer=(), gyroscope=(), magnetometer=()'
    )
    # Strict-Transport-Security (uniquement si HTTPS)
    if request.is_secure or request.headers.get('X-Forwarded-Proto', '') == 'https':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    # X-Frame-Options
    response.headers['X-Frame-Options'] = 'DENY'
    # X-XSS-Protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response


# ══════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
