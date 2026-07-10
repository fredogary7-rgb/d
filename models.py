from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
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
    qr_identifier = db.Column(db.String(20), unique=True, nullable=True)  # TA-XXXX

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
        """Count of unread notifications (placeholder – will use a future Notification model)."""
        return 0

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
