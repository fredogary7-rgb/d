"""Admin Models – Back Office TransAfrik"""

from datetime import datetime
from models import db


class AdminUser(db.Model):
    """Administrator account linked to a User."""
    __tablename__ = 'admin_users'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False, index=True)
    role = db.Column(db.String(30), nullable=False, default='admin')
    # super_admin | admin | support | finance | compliance
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('admin_users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    # Relations
    user = db.relationship('User', backref=db.backref('admin_profile', uselist=False))
    created_by = db.relationship('AdminUser', remote_side=[id], backref='created_admins')

    PERMISSIONS = {
        'super_admin': [
            'dashboard', 'users', 'kyc', 'transactions', 'deposits', 'withdrawals',
            'support', 'notifications', 'settings', 'logs', 'audit', 'stats',
            'roles', 'system', 'export', 'delete', 'credit', 'debit'
        ],
        'admin': [
            'dashboard', 'users', 'kyc', 'transactions', 'deposits', 'withdrawals',
            'support', 'notifications', 'settings', 'logs', 'stats', 'export'
        ],
        'support': ['dashboard', 'users_view', 'support', 'transactions_view'],
        'finance': ['dashboard', 'transactions', 'deposits', 'withdrawals', 'stats', 'export', 'credit', 'debit'],
        'compliance': ['dashboard', 'kyc', 'users_view', 'logs', 'audit'],
    }

    def has_permission(self, permission):
        """Check if this admin role has the given permission."""
        return permission in self.PERMISSIONS.get(self.role, [])

    def __repr__(self):
        return f'<AdminUser {self.user.email if self.user else self.id} ({self.role})>'


class AdminLog(db.Model):
    """Audit log for all admin actions."""
    __tablename__ = 'admin_logs'

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin_users.id'), nullable=True, index=True)
    admin_email = db.Column(db.String(255), nullable=True)
    action = db.Column(db.String(100), nullable=False, index=True)          # user_suspend, kyc_approve, etc.
    target_type = db.Column(db.String(50), nullable=True)                    # user, transaction, kyc...
    target_id = db.Column(db.Integer, nullable=True)
    detail = db.Column(db.Text, nullable=True)                               # JSON description
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    admin = db.relationship('AdminUser', backref='logs')

    def __repr__(self):
        return f'<AdminLog {self.action} by {self.admin_email}>'


class SystemConfig(db.Model):
    """Dynamic system configuration."""
    __tablename__ = 'system_config'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    DEFAULT_CONFIGS = {
        'platform_name': ('TransAfrik', 'Nom de la plateforme'),
        'platform_url': ('https://transafrik.com', 'URL de la plateforme'),
        'support_email': ('support@transafrik.com', 'Email de support'),
        'commission_percent': ('1.5', 'Commission en pourcentage'),
        'min_transfer': ('500', 'Montant minimum de transfert (XOF)'),
        'max_transfer': ('5000000', 'Montant maximum de transfert (XOF)'),
        'max_daily_transfer': ('10000000', 'Plafond journalier (XOF)'),
        'base_currency': ('XOF', 'Devise de base'),
        'maintenance_mode': ('false', 'Mode maintenance (true/false)'),
        'maintenance_message': ('La plateforme est en maintenance. Veuillez réessayer plus tard.', 'Message de maintenance'),
        'version': ('1.0.0', 'Version de l\'application'),
        'sms_enabled': ('false', 'Notifications SMS activées'),
        'email_enabled': ('true', 'Notifications email activées'),
        'soleaspay_api_key': ('', 'Clé API SoleasPay'),
        'soleaspay_api_url': ('https://api.soleaspay.com', 'URL API SoleasPay'),
        'max_login_attempts': ('5', 'Tentatives de connexion max'),
        'session_timeout': ('3600', 'Timeout de session (secondes)'),
        'kyc_required': ('true', 'KYC obligatoire'),
        'referral_bonus': ('500', 'Bonus de parrainage (XOF)'),
        'referral_bonus_sender': ('250', 'Bonus parrain pour le parrain'),
        'referral_bonus_receiver': ('250', 'Bonus parrain pour le filleul'),
    }

    @classmethod
    def get(cls, key, default=None):
        """Get a config value by key."""
        config = cls.query.filter_by(key=key).first()
        return config.value if config else (cls.DEFAULT_CONFIGS.get(key, (default,))[0] if key in cls.DEFAULT_CONFIGS else default)

    @classmethod
    def set(cls, key, value):
        """Set a config value."""
        config = cls.query.filter_by(key=key).first()
        if config:
            config.value = str(value)
        else:
            config = cls(key=key, value=str(value))
            db.session.add(config)
        return config

    @classmethod
    def get_bool(cls, key, default=False):
        """Get a config value as boolean."""
        val = cls.get(key, str(default))
        return val.lower() in ('true', '1', 'yes', 'on')

    @classmethod
    def get_int(cls, key, default=0):
        """Get a config value as integer."""
        try:
            return int(cls.get(key, str(default)))
        except (ValueError, TypeError):
            return default

    @classmethod
    def get_float(cls, key, default=0.0):
        """Get a config value as float."""
        try:
            return float(cls.get(key, str(default)))
        except (ValueError, TypeError):
            return default

    @classmethod
    def seed_defaults(cls):
        """Insert all default configurations if they don't exist."""
        existing = {c.key for c in cls.query.all()}
        for key, (value, desc) in cls.DEFAULT_CONFIGS.items():
            if key not in existing:
                config = cls(key=key, value=value, description=desc)
                db.session.add(config)
        db.session.commit()

    def __repr__(self):
        return f'<SystemConfig {self.key}={self.value}>'


class PlatformNotification(db.Model):
    """Notification sent by admin to users."""
    __tablename__ = 'platform_notifications'

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin_users.id'), nullable=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(50), default='fa-bell')
    target_type = db.Column(db.String(20), nullable=False, default='all')   # all | country | user | segment
    target_value = db.Column(db.String(100), nullable=True)                  # country code or user id
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_sent = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime, nullable=True)

    admin = db.relationship('AdminUser', backref='notifications')

    def __repr__(self):
        return f'<Notification {self.title}>'


class UserNotification(db.Model):
    """Link between notification and user."""
    __tablename__ = 'user_notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    notification_id = db.Column(db.Integer, db.ForeignKey('platform_notifications.id'), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='notifications')
    notification = db.relationship('PlatformNotification', backref='user_links')

    def __repr__(self):
        return f'<UserNotification user={self.user_id} notif={self.notification_id}>'