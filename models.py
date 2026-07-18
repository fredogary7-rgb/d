from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone
import uuid

db = SQLAlchemy()


def generate_referral_code():
    return 'TAF-' + uuid.uuid4().hex[:8].upper()


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30), nullable=False)
    country = db.Column(db.String(5), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # ---- Nouveaux champs dashboard ----
    balance = db.Column(db.Integer, default=0)            # balance in minor units (e.g. XOF)
    pending_balance = db.Column(db.Integer, default=0)    # pending transfers
    currency = db.Column(db.String(10), default='XOF')
    profile_picture = db.Column(db.String(255), nullable=True)
    kyc_status = db.Column(db.String(20), default='pending')   # pending | verified | rejected
    referral_code = db.Column(db.String(30), unique=True, default=generate_referral_code)
    last_login = db.Column(db.DateTime, nullable=True)          # dernière connexion
    language = db.Column(db.String(5), default='fr')            # fr | en
    pin_hash = db.Column(db.String(255), nullable=True)         # code PIN transaction
    is_deleted = db.Column(db.Boolean, default=False)           # soft delete
    qr_identifier = db.Column(db.String(20), unique=True, nullable=True)  # TA-XXXX

    # ---- Champs profil ----
    birth_date = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(10), nullable=True)            # male | female | other
    profession = db.Column(db.String(150), nullable=True)
    address = db.Column(db.String(300), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    theme = db.Column(db.String(10), default='light')           # light | dark
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_method = db.Column(db.String(20), nullable=True)  # sms | email | authenticator
    last_ip = db.Column(db.String(45), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True)
    # Limites
    daily_limit = db.Column(db.Integer, default=500000)     # XOF minor units
    monthly_limit = db.Column(db.Integer, default=5000000)  # XOF minor units
    used_daily = db.Column(db.Integer, default=0)
    used_monthly = db.Column(db.Integer, default=0)
    # Notifications
    notification_email = db.Column(db.Boolean, default=True)
    notification_sms = db.Column(db.Boolean, default=True)
    notification_push = db.Column(db.Boolean, default=True)
    vibrations = db.Column(db.Boolean, default=True)
    # Parrainage
    referred_by = db.Column(db.Integer, nullable=True)       # id du parrain

    # Relations
    transactions = db.relationship('Transaction', backref='user', lazy='dynamic',
                                   foreign_keys='Transaction.user_id')
    beneficiaries = db.relationship('Beneficiary', backref='user', lazy='dynamic')

    @property
    def first_name(self):
        """Extract first name from fullname."""
        parts = self.fullname.strip().split()
        return parts[0] if parts else self.fullname

    @property
    def username(self):
        """Derive username from email (part before @)."""
        return self.email.split('@')[0] if '@' in self.email else self.email

    @property
    def total_sent(self):
        """Sum of all send-type transactions."""
        return db.session.query(db.func.coalesce(db.func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == self.id,
            Transaction.type == 'send',
            Transaction.status == 'success'
        ).scalar()

    @property
    def total_received(self):
        """Sum of all receive-type transactions."""
        return db.session.query(db.func.coalesce(db.func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == self.id,
            Transaction.type == 'receive',
            Transaction.status == 'success'
        ).scalar()

    @property
    def tx_count(self):
        """Total number of transactions."""
        return self.transactions.count()

    @property
    def beneficiary_count(self):
        """Number of saved beneficiaries."""
        return self.beneficiaries.count()

    @property
    def unread_notifications(self):
        """Count of unread notifications."""
        return Notification.query.filter_by(user_id=self.id, is_read=False).count()

    def recent_transactions(self, limit=5):
        return self.transactions.order_by(Transaction.created_at.desc()).limit(limit).all()

    def __repr__(self):
        return f'<User {self.email}>'


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    type = db.Column(db.String(20), nullable=False)          # send | receive | deposit | withdraw
    amount = db.Column(db.Integer, nullable=False)            # minor units
    currency = db.Column(db.String(10), default='XOF')
    fee = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='pending')     # pending | processing | success | failed
    recipient_name = db.Column(db.String(150), nullable=True)
    recipient_phone = db.Column(db.String(30), nullable=True)
    recipient_country = db.Column(db.String(5), nullable=True)
    recipient_operator = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Transaction {self.id} {self.type} {self.amount}>'


def generate_transfer_reference():
    """Génère une référence unique de transfert (format: TA20260710A83F91)."""
    now = datetime.utcnow()
    date_part = now.strftime('%Y%m%d')
    random_part = uuid.uuid4().hex[:6].upper()
    return f'TA{date_part}{random_part}'


class Transfer(db.Model):
    """Transfert d'argent complet avec workflow SoleasPay."""

    __tablename__ = 'transfers'

    STATUS_CHOICES = [
        'CREATED',
        'WAITING_PAYMENT',
        'PAYMENT_PROCESSING',
        'PAYMENT_SUCCESS',
        'PAYMENT_FAILED',
        'WITHDRAW_PROCESSING',
        'COMPLETED',
        'FAILED',
        'CANCELLED',
    ]

    # ---- Identification ----
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(64), unique=True, nullable=False, index=True,
                          default=generate_transfer_reference)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True,
                          nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                          onupdate=datetime.utcnow, nullable=False)

    # ---- Expéditeur ----
    sender_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False,
                              index=True)
    sender_name = db.Column(db.String(150), nullable=False)
    sender_email = db.Column(db.String(255), nullable=True)
    sender_phone = db.Column(db.String(30), nullable=False)
    sender_country = db.Column(db.String(5), nullable=False)
    sender_operator = db.Column(db.String(50), nullable=False)
    sender_operator_id = db.Column(db.Integer, nullable=True)

    # ---- Destinataire ----
    receiver_name = db.Column(db.String(150), nullable=False)
    receiver_phone = db.Column(db.String(30), nullable=False)
    receiver_country = db.Column(db.String(5), nullable=False)
    receiver_operator = db.Column(db.String(50), nullable=False)
    receiver_operator_id = db.Column(db.Integer, nullable=True)

    # ---- Financier ----
    amount = db.Column(db.Integer, nullable=False)               # unités mineures
    fees = db.Column(db.Integer, nullable=False, default=0)       # unités mineures
    total_amount = db.Column(db.Integer, nullable=False)          # unités mineures
    currency = db.Column(db.String(10), nullable=False, default='XOF')
    exchange_rate = db.Column(db.Float, nullable=True, default=1.0)

    # ---- Références SoleasPay ----
    payin_reference = db.Column(db.String(200), nullable=True)
    withdraw_reference = db.Column(db.String(200), nullable=True)
    payin_external_reference = db.Column(db.String(200), nullable=True)
    withdraw_external_reference = db.Column(db.String(200), nullable=True)

    # ---- Statut ----
    status = db.Column(db.String(30), nullable=False, default='CREATED', index=True)

    # ---- JSON (réponses brutes + webhook) ----
    payin_response = db.Column(db.JSON, nullable=True)
    withdraw_response = db.Column(db.JSON, nullable=True)
    webhook_payload = db.Column(db.JSON, nullable=True)

    # ---- Relation ----
    sender = db.relationship('User', backref=db.backref('transfers', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'reference': self.reference,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'sender_user_id': self.sender_user_id,
            'sender_name': self.sender_name,
            'sender_email': self.sender_email,
            'sender_phone': self.sender_phone,
            'sender_country': self.sender_country,
            'sender_operator': self.sender_operator,
            'sender_operator_id': self.sender_operator_id,
            'receiver_name': self.receiver_name,
            'receiver_phone': self.receiver_phone,
            'receiver_country': self.receiver_country,
            'receiver_operator': self.receiver_operator,
            'receiver_operator_id': self.receiver_operator_id,
            'amount': self.amount,
            'fees': self.fees,
            'total_amount': self.total_amount,
            'currency': self.currency,
            'exchange_rate': self.exchange_rate,
            'payin_reference': self.payin_reference,
            'withdraw_reference': self.withdraw_reference,
            'payin_external_reference': self.payin_external_reference,
            'withdraw_external_reference': self.withdraw_external_reference,
            'status': self.status,
            'payin_response': self.payin_response,
            'withdraw_response': self.withdraw_response,
            'webhook_payload': self.webhook_payload,
        }

    def __repr__(self):
        return f'<Transfer {self.reference} {self.status}>'


class Deposit(db.Model):
    """Dépôt d'argent pour alimenter le portefeuille TransAfrik."""

    __tablename__ = 'deposits'

    STATUS_CHOICES = [
        'CREATED',
        'PAYMENT_PROCESSING',
        'COMPLETED',
        'FAILED',
        'CANCELLED',
    ]

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ---- Détails du dépôt ----
    phone = db.Column(db.String(30), nullable=False)
    country = db.Column(db.String(5), nullable=False)
    operator = db.Column(db.String(50), nullable=False)
    operator_id = db.Column(db.Integer, nullable=True)
    amount = db.Column(db.Integer, nullable=False)
    fees = db.Column(db.Integer, nullable=False, default=0)
    total_amount = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(10), nullable=False, default='XOF')

    # ---- Références SoleasPay ----
    payin_reference = db.Column(db.String(200), nullable=True)
    external_reference = db.Column(db.String(200), nullable=True)
    payin_response = db.Column(db.JSON, nullable=True)
    webhook_payload = db.Column(db.JSON, nullable=True)

    # ---- Statut ----
    status = db.Column(db.String(30), nullable=False, default='CREATED', index=True)
    status_message = db.Column(db.String(500), nullable=True)

    # ---- Relation ----
    user = db.relationship('User', backref=db.backref('deposits', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'reference': self.reference,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'phone': self.phone,
            'country': self.country,
            'operator': self.operator,
            'operator_id': self.operator_id,
            'amount': self.amount,
            'fees': self.fees,
            'total_amount': self.total_amount,
            'currency': self.currency,
            'payin_reference': self.payin_reference,
            'external_reference': self.external_reference,
            'status': self.status,
            'status_message': self.status_message,
        }

    def __repr__(self):
        return f'<Deposit {self.reference} {self.status}>'


class Beneficiary(db.Model):
    __tablename__ = 'beneficiaries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    country = db.Column(db.String(5), nullable=False)
    operator = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    nickname = db.Column(db.String(100), nullable=True)
    photo = db.Column(db.String(500), nullable=True)
    is_favorite = db.Column(db.Boolean, default=False, index=True)
    transfer_count = db.Column(db.Integer, default=0)
    total_sent = db.Column(db.Integer, default=0)
    last_transfer_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'phone': self.phone,
            'country': self.country,
            'operator': self.operator,
            'email': self.email,
            'nickname': self.nickname,
            'photo': self.photo,
            'is_favorite': self.is_favorite,
            'transfer_count': self.transfer_count,
            'total_sent': self.total_sent,
            'last_transfer_at': self.last_transfer_at.isoformat() if self.last_transfer_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def update_stats(self, amount: int):
        """Met à jour les stats après un transfert vers ce bénéficiaire."""
        self.transfer_count = (self.transfer_count or 0) + 1
        self.total_sent = (self.total_sent or 0) + amount
        self.last_transfer_at = datetime.utcnow()

    def __repr__(self):
        return f'<Beneficiary {self.name}>'


class KycRequest(db.Model):
    """Demande de vérification KYC (Know Your Customer) — niveau premium international."""
    __tablename__ = 'kyc_requests'

    STATUS_CHOICES = [
        'NOT_STARTED',
        'DRAFT',
        'SUBMITTED',
        'UNDER_REVIEW',
        'APPROVED',
        'REJECTED',
        'EXPIRED',
    ]

    DOCUMENT_TYPES = ['national_id', 'passport', 'driving_license']

    # ---- Identification ----
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True, index=True)
    reference = db.Column(db.String(64), unique=True, nullable=False, default=lambda: 'KYC-' + uuid.uuid4().hex[:10].upper())

    # ---- Étape 1 — Informations personnelles ----
    first_name = db.Column(db.String(150), nullable=True)
    last_name = db.Column(db.String(150), nullable=True)
    birth_date = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(10), nullable=True)              # male | female | other
    nationality = db.Column(db.String(5), nullable=True)
    profession = db.Column(db.String(150), nullable=True)
    address = db.Column(db.String(300), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(5), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(255), nullable=True)

    # ---- Étape 2 — Document officiel ----
    document_type = db.Column(db.String(30), nullable=True)       # national_id | passport | driving_license
    document_front = db.Column(db.String(500), nullable=True)     # chemin fichier recto
    document_back = db.Column(db.String(500), nullable=True)      # chemin fichier verso

    # ---- Étape 3 — Selfie ----
    selfie = db.Column(db.String(500), nullable=True)             # chemin fichier selfie

    # ---- Statut & Révision ----
    status = db.Column(db.String(20), nullable=False, default='NOT_STARTED', index=True)
    review_note = db.Column(db.Text, nullable=True)               # commentaire du vérificateur
    reviewed_by = db.Column(db.Integer, nullable=True)            # admin user id

    # ---- Métadonnées ----
    submitted_at = db.Column(db.DateTime, nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)
    device_info = db.Column(db.String(500), nullable=True)

    # ---- Relation ----
    user = db.relationship('User', backref=db.backref('kyc_request', uselist=False, lazy='joined'))

    @property
    def progress_percent(self):
        """Calcule le pourcentage de progression du KYC."""
        filled = 0
        total = 0

        # Étape 1 : informations personnelles (11 champs)
        step1_fields = ['first_name', 'last_name', 'birth_date', 'gender', 'nationality',
                       'profession', 'address', 'city', 'postal_code', 'country', 'phone', 'email']
        for f in step1_fields:
            total += 1
            if getattr(self, f, None):
                filled += 1

        # Étape 2 : document (2 fichiers)
        doc_fields = ['document_type', 'document_front', 'document_back']
        for f in doc_fields:
            total += 1
            if getattr(self, f, None):
                filled += 1

        # Étape 3 : selfie
        total += 1
        if self.selfie:
            filled += 1

        if total == 0:
            return 0
        return min(100, round((filled / total) * 100))

    @property
    def status_label(self):
        labels = {
            'NOT_STARTED': 'Non commencée',
            'DRAFT': 'Brouillon',
            'SUBMITTED': 'Soumis',
            'UNDER_REVIEW': 'En cours de vérification',
            'APPROVED': 'Vérifié',
            'REJECTED': 'Refusé',
            'EXPIRED': 'Expiré',
        }
        return labels.get(self.status, self.status)

    @property
    def status_color(self):
        colors = {
            'NOT_STARTED': 'neutral',
            'DRAFT': 'warning',
            'SUBMITTED': 'info',
            'UNDER_REVIEW': 'warning',
            'APPROVED': 'success',
            'REJECTED': 'danger',
            'EXPIRED': 'neutral',
        }
        return colors.get(self.status, 'neutral')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'reference': self.reference,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'birth_date': str(self.birth_date) if self.birth_date else None,
            'gender': self.gender,
            'nationality': self.nationality,
            'profession': self.profession,
            'address': self.address,
            'city': self.city,
            'postal_code': self.postal_code,
            'country': self.country,
            'phone': self.phone,
            'email': self.email,
            'document_type': self.document_type,
            'document_front': self.document_front,
            'document_back': self.document_back,
            'selfie': self.selfie,
            'status': self.status,
            'status_label': self.status_label,
            'review_note': self.review_note,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'progress_percent': self.progress_percent,
        }

    def __repr__(self):
        return f'<KycRequest {self.reference} {self.status}>'


class PushSubscription(db.Model):
    """Abonnement Push Web — Web Push API (PWA, Chrome, Firefox, Edge, Safari 16+)."""

    __tablename__ = 'push_subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    endpoint = db.Column(db.Text, nullable=False)
    p256dh = db.Column(db.Text, nullable=False)
    auth = db.Column(db.Text, nullable=False)
    user_agent = db.Column(db.String(500), nullable=True)
    platform = db.Column(db.String(50), nullable=True)        # android | windows | ios | macos | linux
    browser = db.Column(db.String(50), nullable=True)          # chrome | firefox | edge | safari | opera
    device_name = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    # Relation
    user = db.relationship('User', backref=db.backref('push_subscriptions', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'endpoint', name='uq_user_endpoint'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'platform': self.platform,
            'browser': self.browser,
            'device_name': self.device_name,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
        }

    def __repr__(self):
        return f'<PushSubscription {self.id} user={self.user_id} platform={self.platform}>'


class PaymentRequest(db.Model):
    """Demande de paiement — permet à un utilisateur de demander un paiement à un tiers."""

    __tablename__ = 'payment_requests'

    STATUS_CHOICES = ['PENDING', 'PAID', 'EXPIRED', 'CANCELLED']

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    request_code = db.Column(db.String(12), unique=True, nullable=False, index=True)
    sender_id = db.Column(db.Integer, nullable=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    amount = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(10), nullable=False, default='XOF')
    description = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='PENDING', index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    payment_link = db.Column(db.String(500), nullable=True)
    qr_data = db.Column(db.Text, nullable=True)
    payment_reference = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    receiver = db.relationship('User', backref=db.backref('payment_requests', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'request_code': self.request_code,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'amount': self.amount,
            'currency': self.currency,
            'description': self.description,
            'status': self.status,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'payment_link': self.payment_link,
            'qr_data': self.qr_data,
            'payment_reference': self.payment_reference,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<PaymentRequest {self.request_code} {self.status}>'


class TransactionReceive(db.Model):
    """Transaction reçue via PaymentRequest — historisation des paiements reçus."""

    __tablename__ = 'transaction_receives'

    id = db.Column(db.Integer, primary_key=True)
    payment_request_id = db.Column(db.Integer, db.ForeignKey('payment_requests.id'), nullable=True, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    amount = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(10), nullable=False, default='XOF')
    status = db.Column(db.String(20), nullable=False, default='completed', index=True)
    reference = db.Column(db.String(64), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    payment_request = db.relationship('PaymentRequest', backref=db.backref('transactions', lazy='dynamic'))
    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('payments_sent_receive', lazy='dynamic'))
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref=db.backref('payments_received', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'payment_request_id': self.payment_request_id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'amount': self.amount,
            'currency': self.currency,
            'status': self.status,
            'reference': self.reference,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<TransactionReceive {self.id} {self.amount} {self.currency}>'


class OtpCode(db.Model):
    """Code OTP pour vérification par email via Resend (inscription, connexion, reset mdp)."""

    __tablename__ = 'otp_codes'

    # ---- Identification ----
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(30), nullable=True, index=True)       # conservé pour rétrocompatibilité
    email = db.Column(db.String(255), nullable=False, index=True)     # email pour envoi OTP via Resend
    code = db.Column(db.String(10), nullable=False)
    purpose = db.Column(db.String(20), nullable=False, index=True)  # register | login | reset_password | change_phone
    expires_at = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.Integer, default=0)
    is_verified = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    @property
    def is_expired(self):
        """Vérifie si le code OTP a expiré."""
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)

    @property
    def attempts_remaining(self):
        """Nombre de tentatives restantes (max 3)."""
        return max(0, 3 - self.attempts)

    def __repr__(self):
        return f'<OtpCode {self.id} email={self.email} purpose={self.purpose} verified={self.is_verified}>'


def generate_ticket_number():
    """Génère un numéro de ticket unique (format: TK-20260714-A83F)."""
    now = datetime.utcnow()
    date_part = now.strftime('%Y%m%d')
    random_part = uuid.uuid4().hex[:4].upper()
    return f'TK-{date_part}-{random_part}'


class SupportTicket(db.Model):
    """Ticket de support client TransAfrik."""

    __tablename__ = 'support_tickets'

    STATUS_CHOICES = ['OPEN', 'IN_PROGRESS', 'WAITING_USER', 'RESOLVED', 'CLOSED']
    PRIORITY_CHOICES = ['LOW', 'NORMAL', 'HIGH', 'URGENT']
    CATEGORY_CHOICES = ['Transfer', 'Payment', 'Account', 'KYC', 'Card', 'Technical', 'Other']

    # ---- Identification ----
    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(30), unique=True, nullable=False, index=True,
                              default=generate_ticket_number)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    # ---- Détails ----
    subject = db.Column(db.String(300), nullable=False)
    category = db.Column(db.String(30), nullable=False, default='Other')
    priority = db.Column(db.String(10), nullable=False, default='NORMAL')
    status = db.Column(db.String(20), nullable=False, default='OPEN', index=True)
    message = db.Column(db.Text, nullable=False)
    attachment = db.Column(db.String(500), nullable=True)

    # ---- Métadonnées ----
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)
    assigned_to = db.Column(db.Integer, nullable=True)           # admin/agent user id

    # ---- Relation ----
    user = db.relationship('User', backref=db.backref('support_tickets', lazy='dynamic'))
    messages = db.relationship('SupportMessage', backref='ticket', lazy='dynamic',
                               order_by='SupportMessage.created_at')

    @property
    def status_label(self):
        labels = {
            'OPEN': 'Ouvert',
            'IN_PROGRESS': 'En cours',
            'WAITING_USER': 'En attente',
            'RESOLVED': 'Résolu',
            'CLOSED': 'Fermé',
        }
        return labels.get(self.status, self.status)

    @property
    def priority_label(self):
        labels = {
            'LOW': 'Faible',
            'NORMAL': 'Normale',
            'HIGH': 'Élevée',
            'URGENT': 'Urgente',
        }
        return labels.get(self.priority, self.priority)

    @property
    def category_label(self):
        labels = {
            'Transfer': 'Transfert',
            'Payment': 'Paiement',
            'Account': 'Compte',
            'KYC': 'KYC',
            'Card': 'Carte',
            'Technical': 'Technique',
            'Other': 'Autre',
        }
        return labels.get(self.category, self.category)

    def to_dict(self):
        return {
            'id': self.id,
            'ticket_number': self.ticket_number,
            'user_id': self.user_id,
            'subject': self.subject,
            'category': self.category,
            'category_label': self.category_label,
            'priority': self.priority,
            'priority_label': self.priority_label,
            'status': self.status,
            'status_label': self.status_label,
            'message': self.message,
            'attachment': self.attachment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'assigned_to': self.assigned_to,
            'messages_count': self.messages.count() if self.messages else 0,
        }

    def __repr__(self):
        return f'<SupportTicket {self.ticket_number} {self.status}>'


class Notification(db.Model):
    """Notification utilisateur — centre de notifications."""

    __tablename__ = 'notifications'

    CATEGORIES = [
        'payment_received',
        'payment_sent',
        'withdrawal',
        'deposit',
        'kyc',
        'login',
        'security',
        'promo',
        'support',
        'system',
    ]

    ICONS_MAP = {
        'payment_received': 'fa-arrow-down-wide-short',
        'payment_sent': 'fa-paper-plane',
        'withdrawal': 'fa-building-columns',
        'deposit': 'fa-wallet',
        'kyc': 'fa-user-check',
        'login': 'fa-right-to-bracket',
        'security': 'fa-shield-halved',
        'promo': 'fa-gift',
        'support': 'fa-headset',
        'system': 'fa-gear',
    }

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(30), nullable=False, default='system', index=True)
    is_read = db.Column(db.Boolean, default=False, index=True)
    read_at = db.Column(db.DateTime, nullable=True)
    link = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relation
    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic'))

    @property
    def icon(self):
        return self.ICONS_MAP.get(self.category, 'fa-bell')

    @property
    def date_label(self):
        """Retourne un label lisible pour la date (Aujourd'hui, Hier, etc.)."""
        now = datetime.utcnow()
        delta = now - (self.read_at or self.created_at)
        days = delta.days

        if days == 0:
            secs = delta.total_seconds()
            if secs < 60:
                return "À l'instant"
            elif secs < 3600:
                mins = int(secs // 60)
                return f"Il y a {mins} minute{'s' if mins > 1 else ''}"
            elif secs < 7200:
                return "Il y a 1 heure"
            elif secs < 86400:
                return f"Il y a {int(secs // 3600)} heures"
            else:
                return "Aujourd'hui"
        elif days == 1:
            return "Hier"
        elif days <= 30:
            return f"Il y a {days} jours"
        elif days <= 365:
            months = days // 30
            return f"Il y a {months} mois"
        else:
            years = days // 365
            return f"Il y a {years} an{'s' if years > 1 else ''}"

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'category': self.category,
            'icon': self.icon,
            'is_read': self.is_read,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'date_label': self.date_label,
            'link': self.link,
        }

    def __repr__(self):
        return f'<Notification {self.id} user={self.user_id} category={self.category} read={self.is_read}>'


class SupportMessage(db.Model):
    """Message dans un ticket de support."""

    __tablename__ = 'support_messages'

    # ---- Identification ----
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id'), nullable=False,
                          index=True)
    sender_type = db.Column(db.String(10), nullable=False, default='user')  # user | admin
    sender_id = db.Column(db.Integer, nullable=True)
    message = db.Column(db.Text, nullable=True)
    attachment = db.Column(db.String(500), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'sender_type': self.sender_type,
            'sender_id': self.sender_id,
            'message': self.message,
            'attachment': self.attachment,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<SupportMessage {self.id} ticket={self.ticket_id} sender={self.sender_type}>'


class Withdrawal(db.Model):
    """Retrait direct vers Mobile Money / Compte bancaire via SoleasPay."""

    __tablename__ = 'withdrawals'

    STATUS_CHOICES = [
        'CREATED',
        'WAITING_WITHDRAW',
        'WITHDRAW_PROCESSING',
        'COMPLETED',
        'FAILED',
        'REJECTED',
        'CANCELLED',
    ]

    # ---- Identification ----
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(64), unique=True, nullable=False, index=True,
                          default=lambda: 'WDR' + uuid.uuid4().hex[:10].upper())
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ---- Destinataire ----
    recipient_name = db.Column(db.String(150), nullable=True)
    recipient_phone = db.Column(db.String(30), nullable=False)
    recipient_country = db.Column(db.String(5), nullable=False)
    recipient_operator = db.Column(db.String(50), nullable=False)
    recipient_operator_id = db.Column(db.Integer, nullable=True)

    # ---- Financier ----
    amount = db.Column(db.Integer, nullable=False)               # unités mineures
    currency = db.Column(db.String(10), nullable=False, default='XOF')
    fees = db.Column(db.Integer, nullable=False, default=0)       # unités mineures
    total_debited = db.Column(db.Integer, nullable=False)          # amount + fees
    converted_amount = db.Column(db.Integer, nullable=True)        # si conversion devise
    exchange_rate = db.Column(db.Float, nullable=True, default=1.0)

    # ---- Statut ----
    status = db.Column(db.String(30), nullable=False, default='CREATED', index=True)
    status_message = db.Column(db.Text, nullable=True)

    # ---- Références SoleasPay ----
    withdraw_reference = db.Column(db.String(200), nullable=True)   # reference retournée par SoleasPay
    external_reference = db.Column(db.String(200), nullable=True)

    # ---- Payloads ----
    request_payload = db.Column(db.Text, nullable=True)    # JSON envoyé à SoleasPay
    response_payload = db.Column(db.Text, nullable=True)   # JSON reçu de SoleasPay
    webhook_payload = db.Column(db.Text, nullable=True)    # JSON reçu du webhook

    # ---- Remboursement ----
    refunded = db.Column(db.Boolean, default=False)
    refund_amount = db.Column(db.Integer, nullable=True)
    refund_at = db.Column(db.DateTime, nullable=True)

    # ---- Relation ----
    user = db.relationship('User', backref=db.backref('withdrawals', lazy='dynamic'))

    def amount_display(self):
        return self.amount / 100

    def fees_display(self):
        return self.fees / 100

    def total_display(self):
        return self.total_debited / 100

    def to_dict(self):
        return {
            'id': self.id,
            'reference': self.reference,
            'user_id': self.user_id,
            'recipient_name': self.recipient_name,
            'recipient_phone': self.recipient_phone,
            'recipient_country': self.recipient_country,
            'recipient_operator': self.recipient_operator,
            'amount': self.amount,
            'currency': self.currency,
            'fees': self.fees,
            'total_debited': self.total_debited,
            'converted_amount': self.converted_amount,
            'exchange_rate': self.exchange_rate,
            'status': self.status,
            'status_message': self.status_message,
            'withdraw_reference': self.withdraw_reference,
            'external_reference': self.external_reference,
            'refunded': self.refunded,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<Withdrawal {self.reference} {self.status} {self.amount} {self.currency}>'
