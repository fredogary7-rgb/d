"""Admin Routes — Back Office TransAfrik"""

import functools
import json
from datetime import datetime, timedelta

from flask import (abort, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_login import current_user, login_required
from sqlalchemy import func

from admin import admin_bp
from admin.models import AdminLog, AdminUser, PlatformNotification, SystemConfig, UserNotification
from models import (Beneficiary, Notification, PaymentRequest, Review, SupportMessage, SupportTicket,
                    Transaction, TransactionReceive, User, PushSubscription, db)
from services.push_service import send_push_to_user


# ── Decorator ──────────────────────────────────────────────────────────────
def admin_required(f):
    """Protect admin routes. Only users with an active AdminUser profile may access."""
    @functools.wraps(f)
    @login_required
    def wrapped(*args, **kwargs):
        admin = AdminUser.query.filter_by(user_id=current_user.id, is_active=True).first()
        if not admin:
            abort(403)
        # Store admin profile on current_user for template use
        current_user._admin = admin
        return f(*args, **kwargs)
    return wrapped


def get_admin():
    """Return current admin profile or None."""
    if not current_user.is_authenticated:
        return None
    return AdminUser.query.filter_by(user_id=current_user.id, is_active=True).first()


def log_action(admin, action, target_type=None, target_id=None, detail=None):
    """Record an admin action in the audit log."""
    try:
        log = AdminLog(
            admin_id=admin.id,
            admin_email=current_user.email,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=json.dumps(detail) if isinstance(detail, dict) else detail,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()


# ══════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════

@admin_bp.route('/')
@admin_required
def dashboard():
    admin = get_admin()
    today = datetime.utcnow().date()
    start_of_day = datetime.combine(today, datetime.min.time())

    # ── Statistics ──
    total_users = User.query.filter_by(is_deleted=False).count()
    verified_users = User.query.filter_by(is_deleted=False, kyc_status='verified').count()
    pending_kyc = User.query.filter_by(is_deleted=False, kyc_status='pending').count()
    suspended_users = User.query.filter_by(is_deleted=False, is_active=False).count()

    # Today's transactions
    today_tx = Transaction.query.filter(
        Transaction.created_at >= start_of_day,
        Transaction.status == 'success'
    )
    today_tx_count = today_tx.count()

    # Amounts
    today_total_sent = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.created_at >= start_of_day,
        Transaction.type == 'send',
        Transaction.status == 'success'
    ).scalar()

    total_sent = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.type == 'send',
        Transaction.status == 'success'
    ).scalar()

    # Platform revenue (commission = 1.5% of transfers)
    commission = SystemConfig.get_float('commission_percent', 1.5)
    platform_revenue = int(total_sent * commission / 100)

    # Deposits & Withdrawals
    total_deposits = Transaction.query.filter_by(type='deposit').count()
    total_withdrawals = Transaction.query.filter_by(type='withdraw').count()
    total_transfers = Transaction.query.filter_by(type='send').count()
    total_beneficiaries = Beneficiary.query.count()

    # QR codes generated (users with qr_identifier)
    qr_count = User.query.filter(User.qr_identifier.isnot(None), User.is_deleted == False).count()

    # Support tickets
    open_tickets = SupportTicket.query.filter_by(status='open').count()

    # Today's deposits & withdrawals
    today_deposits = Transaction.query.filter(
        Transaction.created_at >= start_of_day,
        Transaction.type == 'deposit'
    ).count()
    today_withdrawals = Transaction.query.filter(
        Transaction.created_at >= start_of_day,
        Transaction.type == 'withdraw'
    ).count()

    # ── Recent activity ──
    recent_tx = Transaction.query.order_by(Transaction.created_at.desc()).limit(10).all()
    recent_users = User.query.filter_by(is_deleted=False).order_by(User.created_at.desc()).limit(8).all()
    recent_logins = User.query.filter(User.last_login.isnot(None), User.is_deleted == False)\
        .order_by(User.last_login.desc()).limit(8).all()

    # ── Revenue per day (last 30 days) ──
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    daily_revenue = db.session.query(
        func.date(Transaction.created_at).label('day'),
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.type == 'send',
        Transaction.status == 'success',
        Transaction.created_at >= thirty_days_ago
    ).group_by(func.date(Transaction.created_at)).order_by('day').all()

    revenue_labels = [str(r.day) for r in daily_revenue]
    revenue_values = [int(r.total * commission / 100) for r in daily_revenue]

    # ── Sign-ups per day (last 30 days) ──
    daily_signups = db.session.query(
        func.date(User.created_at).label('day'),
        func.count(User.id)
    ).filter(
        User.created_at >= thirty_days_ago,
        User.is_deleted == False
    ).group_by(func.date(User.created_at)).order_by('day').all()

    signup_labels = [str(s.day) for s in daily_signups]
    signup_values = [s[1] for s in daily_signups]

    # ── Transfers per day (last 30 days) ──
    daily_transfers = db.session.query(
        func.date(Transaction.created_at).label('day'),
        func.count(Transaction.id)
    ).filter(
        Transaction.type == 'send',
        Transaction.created_at >= thirty_days_ago
    ).group_by(func.date(Transaction.created_at)).order_by('day').all()

    transfer_labels = [str(t.day) for t in daily_transfers]
    transfer_values = [t[1] for t in daily_transfers]

    stats = {
        'total_users': total_users,
        'verified_users': verified_users,
        'pending_kyc': pending_kyc,
        'suspended_users': suspended_users,
        'today_tx': today_tx_count,
        'today_amount': today_total_sent,
        'total_sent': total_sent,
        'platform_revenue': platform_revenue,
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'total_transfers': total_transfers,
        'total_beneficiaries': total_beneficiaries,
        'qr_count': qr_count,
        'open_tickets': open_tickets,
        'today_deposits': today_deposits,
        'today_withdrawals': today_withdrawals,
        'recent_tx': recent_tx,
        'recent_users': recent_users,
        'recent_logins': recent_logins,
        'revenue_labels': json.dumps(revenue_labels),
        'revenue_values': json.dumps(revenue_values),
        'signup_labels': json.dumps(signup_labels),
        'signup_values': json.dumps(signup_values),
        'transfer_labels': json.dumps(transfer_labels),
        'transfer_values': json.dumps(transfer_values),
    }

    return render_template('admin_dashboard.html', page='dashboard', stats=stats)


# ══════════════════════════════════════════════════════════════════════════
# USERS
# ══════════════════════════════════════════════════════════════════════════

@admin_bp.route('/users')
@admin_required
def users():
    admin = get_admin()
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    country = request.args.get('country', '')
    status = request.args.get('status', '')
    kyc = request.args.get('kyc', '')
    per_page = 20

    query = User.query.filter_by(is_deleted=False)

    if search:
        query = query.filter(
            db.or_(
                User.fullname.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%'),
                User.phone.ilike(f'%{search}%'),
                User.qr_identifier.ilike(f'%{search}%')
            )
        )
    if country:
        query = query.filter_by(country=country)
    if status:
        query = query.filter_by(is_active=(status == 'active'))
    if kyc:
        query = query.filter_by(kyc_status=kyc)

    users_paginated = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)

    # Country list for filters
    countries = db.session.query(User.country, func.count(User.id)).filter(
        User.is_deleted == False).group_by(User.country).order_by(User.country).all()

    return render_template('admin_users.html', page='users',
                           users=users_paginated, countries=countries,
                           search=search, country=country, status=status, kyc=kyc)


@admin_bp.route('/users/<int:user_id>')
@admin_required
def user_detail(user_id):
    admin = get_admin()
    user = User.query.get_or_404(user_id)
    transactions = Transaction.query.filter_by(user_id=user.id)\
        .order_by(Transaction.created_at.desc()).limit(50).all()
    return render_template('admin_users_view.html', page='user_detail',
                           target_user=user, transactions=transactions)


@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@admin_required
def toggle_user(user_id):
    admin = get_admin()
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    action = 'user_activate' if user.is_active else 'user_suspend'
    log_action(admin, action, 'user', user.id, {
        'user_email': user.email,
        'new_status': str(user.is_active)
    })
    db.session.commit()
    try:
        if user.is_active:
            send_push_to_user(user.id, "✅ Compte réactivé", "Votre compte TransAfrik a été réactivé par l'administrateur.", url="/dashboard")
        else:
            send_push_to_user(user.id, "⚠️ Compte suspendu", "Votre compte TransAfrik a été suspendu. Contactez le support pour plus d'informations.", url="/support")
    except Exception:
        pass
    flash(f'Utilisateur {"activé" if user.is_active else "suspendu"} avec succès.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def soft_delete_user(user_id):
    admin = get_admin()
    user = User.query.get_or_404(user_id)
    user.is_deleted = True
    log_action(admin, 'user_delete', 'user', user.id, {'user_email': user.email})
    db.session.commit()
    try:
        send_push_to_user(user.id, "❌ Compte supprimé", "Votre compte TransAfrik a été supprimé par l'administrateur.", url="/")
    except Exception:
        pass
    flash('Utilisateur supprimé avec succès.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/credit', methods=['POST'])
@admin_required
def credit_user(user_id):
    admin = get_admin()
    user = User.query.get_or_404(user_id)
    amount = request.form.get('amount', 0, type=int)
    reason = request.form.get('reason', 'Crédit administrateur')

    if amount <= 0:
        flash('Montant invalide.', 'error')
        return redirect(url_for('admin.user_detail', user_id=user_id))

    user.balance = (user.balance or 0) + amount

    # Create transaction
    tx = Transaction(
        user_id=user.id,
        type='deposit',
        amount=amount,
        currency=user.currency or 'XOF',
        status='success',
        recipient_name=user.fullname,
        recipient_phone=user.phone,
        recipient_country=user.country
    )
    db.session.add(tx)
    log_action(admin, 'user_credit', 'user', user.id, {
        'amount': amount,
        'reason': reason,
        'user_email': user.email
    })
    db.session.commit()
    try:
        send_push_to_user(user.id, "💰 Compte crédité", f"Votre compte a été crédité de {amount:,.0f} {user.currency or 'XOF'} par l'administrateur.", url="/dashboard")
    except Exception:
        pass
    flash(f'Compte crédité de {amount:,.0f} {user.currency or "XOF"}.', 'success')
    return redirect(url_for('admin.user_detail', user_id=user_id))


@admin_bp.route('/users/<int:user_id>/debit', methods=['POST'])
@admin_required
def debit_user(user_id):
    admin = get_admin()
    user = User.query.get_or_404(user_id)
    amount = request.form.get('amount', 0, type=int)
    reason = request.form.get('reason', 'Débit administrateur')

    if amount <= 0:
        flash('Montant invalide.', 'error')
        return redirect(url_for('admin.user_detail', user_id=user_id))
    if amount > (user.balance or 0):
        flash('Solde insuffisant.', 'error')
        return redirect(url_for('admin.user_detail', user_id=user_id))

    user.balance = (user.balance or 0) - amount

    tx = Transaction(
        user_id=user.id,
        type='withdraw',
        amount=amount,
        currency=user.currency or 'XOF',
        status='success',
        recipient_name=user.fullname,
        recipient_phone=user.phone,
        recipient_country=user.country
    )
    db.session.add(tx)
    log_action(admin, 'user_debit', 'user', user.id, {
        'amount': amount,
        'reason': reason,
        'user_email': user.email
    })
    db.session.commit()
    try:
        send_push_to_user(user.id, "💸 Compte débité", f"Votre compte a été débité de {amount:,.0f} {user.currency or 'XOF'} par l'administrateur.", url="/dashboard")
    except Exception:
        pass
    flash(f'Compte débité de {amount:,.0f} {user.currency or "XOF"}.', 'success')
    return redirect(url_for('admin.user_detail', user_id=user_id))


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def reset_user_password(user_id):
    admin = get_admin()
    user = User.query.get_or_404(user_id)
    from werkzeug.security import generate_password_hash
    new_password = request.form.get('new_password', '')
    if len(new_password) < 6:
        flash('Le mot de passe doit contenir au moins 6 caractères.', 'error')
        return redirect(url_for('admin.user_detail', user_id=user_id))
    user.password_hash = generate_password_hash(new_password)
    log_action(admin, 'user_password_reset', 'user', user.id, {'user_email': user.email})
    db.session.commit()
    try:
        send_push_to_user(user.id, "🔑 Mot de passe réinitialisé", "Votre mot de passe a été réinitialisé par l'administrateur. Utilisez votre nouveau mot de passe pour vous connecter.", url="/connexion")
    except Exception:
        pass
    flash(f'Mot de passe réinitialisé pour {user.email}.', 'success')
    return redirect(url_for('admin.user_detail', user_id=user_id))


# ══════════════════════════════════════════════════════════════════════════
# KYC
# ══════════════════════════════════════════════════════════════════════════

@admin_bp.route('/kyc')
@admin_required
def kyc():
    admin = get_admin()
    status_filter = request.args.get('status', 'pending')
    page = request.args.get('page', 1, type=int)
    per_page = 15

    query = User.query.filter_by(is_deleted=False)
    if status_filter:
        query = query.filter_by(kyc_status=status_filter)

    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)

    counts = {
        'pending': User.query.filter_by(is_deleted=False, kyc_status='pending').count(),
        'verified': User.query.filter_by(is_deleted=False, kyc_status='verified').count(),
        'rejected': User.query.filter_by(is_deleted=False, kyc_status='rejected').count(),
    }

    return render_template('admin_kyc.html', page='kyc',
                           users=users, status_filter=status_filter, counts=counts)


@admin_bp.route('/kyc/<int:user_id>/approve', methods=['POST'])
@admin_required
def kyc_approve(user_id):
    admin = get_admin()
    user = User.query.get_or_404(user_id)
    user.kyc_status = 'verified'
    log_action(admin, 'kyc_approve', 'user', user.id, {'user_email': user.email})
    db.session.commit()
    try:
        send_push_to_user(user.id, "✅ KYC approuvé", "Votre vérification d'identité a été approuvée. Toutes les fonctionnalités sont désormais débloquées !", url="/dashboard")
    except Exception:
        pass
    flash('KYC approuvé avec succès.', 'success')
    return redirect(url_for('admin.kyc'))


@admin_bp.route('/kyc/<int:user_id>/reject', methods=['POST'])
@admin_required
def kyc_reject(user_id):
    admin = get_admin()
    user = User.query.get_or_404(user_id)
    user.kyc_status = 'rejected'
    note = request.form.get('note', '')
    log_action(admin, 'kyc_reject', 'user', user.id, {
        'user_email': user.email,
        'note': note
    })
    db.session.commit()
    try:
        reason_text = f" : {note}" if note else ""
        send_push_to_user(user.id, "❌ KYC refusé", f"Votre vérification d'identité a été refusée{reason_text}. Veuillez soumettre de nouveaux documents.", url="/kyc")
    except Exception:
        pass
    flash('KYC refusé.', 'warning')
    return redirect(url_for('admin.kyc'))


# ══════════════════════════════════════════════════════════════════════════
# TRANSACTIONS
# ══════════════════════════════════════════════════════════════════════════

@admin_bp.route('/transactions')
@admin_required
def transactions():
    admin = get_admin()
    page = request.args.get('page', 1, type=int)
    per_page = 25
    tx_type = request.args.get('type', '')
    status = request.args.get('status', '')
    country = request.args.get('country', '')
    search = request.args.get('search', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = Transaction.query

    if tx_type:
        query = query.filter_by(type=tx_type)
    if status:
        query = query.filter_by(status=status)
    if country:
        query = query.filter_by(recipient_country=country)
    if search:
        query = query.filter(
            db.or_(
                Transaction.recipient_name.ilike(f'%{search}%'),
                Transaction.recipient_phone.ilike(f'%{search}%'),
                Transaction.transfer_id.ilike(f'%{search}%')
            )
        )
    if date_from:
        query = query.filter(Transaction.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(Transaction.created_at <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))

    txs = query.order_by(Transaction.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)

    # Country list for filters
    countries = db.session.query(Transaction.recipient_country, func.count(Transaction.id))\
        .group_by(Transaction.recipient_country).order_by(Transaction.recipient_country).all()

    return render_template('admin_transactions.html', page='transactions',
                           txs=txs, countries=countries,
                           tx_type=tx_type, status=status, country=country,
                           search=search, date_from=date_from, date_to=date_to)


@admin_bp.route('/transactions/export')
@admin_required
def export_transactions():
    """Export transactions as CSV."""
    from io import StringIO
    import csv
    from flask import make_response

    txs = Transaction.query.order_by(Transaction.created_at.desc()).limit(10000).all()

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['ID', 'Type', 'Montant', 'Devise', 'Statut', 'Expéditeur', 'Bénéficiaire',
                     'Téléphone', 'Pays', 'Opérateur', 'Référence', 'Date'])
    for tx in txs:
        user_email = tx.user.email if tx.user else 'N/A'
        writer.writerow([
            tx.id, tx.type, tx.amount, tx.currency or 'XOF', tx.status,
            user_email, tx.recipient_name, tx.recipient_phone,
            tx.recipient_country, tx.recipient_operator,
            tx.transfer_id, tx.created_at
        ])

    output = make_response(si.getvalue())
    output.headers['Content-Disposition'] = 'attachment; filename=transactions.csv'
    output.headers['Content-Type'] = 'text/csv; charset=utf-8'
    log_action(admin, 'transactions_export', 'transaction', None, {'format': 'csv'})
    return output


# ══════════════════════════════════════════════════════════════════════════
# DEPOSITS
# ══════════════════════════════════════════════════════════════════════════

@admin_bp.route('/deposits')
@admin_required
def deposits():
    admin = get_admin()
    page = request.args.get('page', 1, type=int)
    per_page = 25
    status = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = Transaction.query.filter_by(type='deposit')
    if status:
        query = query.filter_by(status=status)
    if date_from:
        query = query.filter(Transaction.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(Transaction.created_at <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))

    deposits_paginated = query.order_by(Transaction.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)

    pending_count = Transaction.query.filter_by(type='deposit', status='pending').count()
    success_count = Transaction.query.filter_by(type='deposit', status='success').count()
    failed_count = Transaction.query.filter_by(type='deposit', status='failed').count()

    return render_template('admin_deposits.html', page='deposits',
                           deposits=deposits_paginated,
                           pending_count=pending_count, success_count=success_count,
                           failed_count=failed_count,
                           status=status, date_from=date_from, date_to=date_to)


@admin_bp.route('/deposits/<int:tx_id>/validate', methods=['POST'])
@admin_required
def validate_deposit(tx_id):
    admin = get_admin()
    tx = Transaction.query.get_or_404(tx_id)
    if tx.type != 'deposit':
        flash('Cette transaction n\'est pas un dépôt.', 'error')
        return redirect(url_for('admin.deposits'))

    tx.status = 'success'
    user = tx.user
    if user:
        user.balance = (user.balance or 0) + tx.amount
    log_action(admin, 'deposit_validate', 'transaction', tx.id, {
        'amount': tx.amount,
        'user_id': tx.user_id
    })
    db.session.commit()
    flash('Dépôt validé avec succès.', 'success')
    return redirect(url_for('admin.deposits'))


@admin_bp.route('/deposits/<int:tx_id>/reject', methods=['POST'])
@admin_required
def reject_deposit(tx_id):
    admin = get_admin()
    tx = Transaction.query.get_or_404(tx_id)
    if tx.type != 'deposit':
        flash('Cette transaction n\'est pas un dépôt.', 'error')
        return redirect(url_for('admin.deposits'))

    tx.status = 'failed'
    log_action(admin, 'deposit_reject', 'transaction', tx.id, {
        'amount': tx.amount,
        'user_id': tx.user_id
    })
    db.session.commit()
    flash('Dépôt refusé.', 'warning')
    return redirect(url_for('admin.deposits'))


# ══════════════════════════════════════════════════════════════════════════
# WITHDRAWALS
# ══════════════════════════════════════════════════════════════════════════

@admin_bp.route('/withdrawals')
@admin_required
def withdrawals():
    admin = get_admin()
    page = request.args.get('page', 1, type=int)
    per_page = 25
    status = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = Transaction.query.filter_by(type='withdraw')
    if status:
        query = query.filter_by(status=status)
    if date_from:
        query = query.filter(Transaction.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(Transaction.created_at <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))

    withdrawals_paginated = query.order_by(Transaction.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)

    pending_count = Transaction.query.filter_by(type='withdraw', status='pending').count()
    success_count = Transaction.query.filter_by(type='withdraw', status='success').count()
    failed_count = Transaction.query.filter_by(type='withdraw', status='failed').count()

    return render_template('admin_withdrawals.html', page='withdrawals',
                           withdrawals=withdrawals_paginated,
                           pending_count=pending_count, success_count=success_count,
                           failed_count=failed_count,
                           status=status, date_from=date_from, date_to=date_to)


@admin_bp.route('/withdrawals/<int:tx_id>/validate', methods=['POST'])
@admin_required
def validate_withdrawal(tx_id):
    admin = get_admin()
    tx = Transaction.query.get_or_404(tx_id)
    if tx.type != 'withdraw':
        flash('Cette transaction n\'est pas un retrait.', 'error')
        return redirect(url_for('admin.withdrawals'))

    tx.status = 'success'
    log_action(admin, 'withdrawal_validate', 'transaction', tx.id, {
        'amount': tx.amount,
        'user_id': tx.user_id
    })
    db.session.commit()
    flash('Retrait validé avec succès.', 'success')
    return redirect(url_for('admin.withdrawals'))


@admin_bp.route('/withdrawals/<int:tx_id>/reject', methods=['POST'])
@admin_required
def reject_withdrawal(tx_id):
    admin = get_admin()
    tx = Transaction.query.get_or_404(tx_id)
    if tx.type != 'withdraw':
        flash('Cette transaction n\'est pas un retrait.', 'error')
        return redirect(url_for('admin.withdrawals'))

    # Refund user on rejection
    if tx.status == 'pending':
        user = tx.user
        if user:
            user.balance = (user.balance or 0) + tx.amount
    tx.status = 'failed'
    log_action(admin, 'withdrawal_reject', 'transaction', tx.id, {
        'amount': tx.amount,
        'user_id': tx.user_id
    })
    db.session.commit()
    flash('Retrait refusé et remboursé.', 'warning')
    return redirect(url_for('admin.withdrawals'))


# ══════════════════════════════════════════════════════════════════════════
# SUPPORT
# ══════════════════════════════════════════════════════════════════════════

@admin_bp.route('/support')
@admin_required
def support():
    admin = get_admin()
    status_filter = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = SupportTicket.query
    if status_filter:
        query = query.filter_by(status=status_filter)

    tickets = query.order_by(SupportTicket.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)

    open_count = SupportTicket.query.filter_by(status='open').count()
    closed_count = SupportTicket.query.filter_by(status='closed').count()

    return render_template('admin_support.html', page='support',
                           tickets=tickets, open_count=open_count,
                           closed_count=closed_count, status_filter=status_filter)


@admin_bp.route('/support/<int:ticket_id>')
@admin_required
def support_detail(ticket_id):
    admin = get_admin()
    ticket = SupportTicket.query.get_or_404(ticket_id)
    messages = SupportMessage.query.filter_by(ticket_id=ticket.id)\
        .order_by(SupportMessage.created_at.asc()).all()
    return render_template('admin_support_detail.html', page='support_detail',
                           ticket=ticket, messages=messages)


@admin_bp.route('/support/<int:ticket_id>/reply', methods=['POST'])
@admin_required
def support_reply(ticket_id):
    admin = get_admin()
    ticket = SupportTicket.query.get_or_404(ticket_id)
    content = request.form.get('content', '').strip()
    if not content:
        flash('Le message ne peut pas être vide.', 'error')
        return redirect(url_for('admin.support_detail', ticket_id=ticket_id))

    message = SupportMessage(
        ticket_id=ticket.id,
        sender_type='admin',
        sender_name=f"Admin: {current_user.fullname}",
        content=content
    )
    db.session.add(message)
    ticket.updated_at = datetime.utcnow()
    log_action(admin, 'support_reply', 'support_ticket', ticket.id)
    db.session.commit()
    flash('Réponse envoyée.', 'success')
    return redirect(url_for('admin.support_detail', ticket_id=ticket_id))


@admin_bp.route('/support/<int:ticket_id>/close', methods=['POST'])
@admin_required
def support_close(ticket_id):
    admin = get_admin()
    ticket = SupportTicket.query.get_or_404(ticket_id)
    ticket.status = 'closed'
    ticket.updated_at = datetime.utcnow()
    log_action(admin, 'support_close', 'support_ticket', ticket.id)
    db.session.commit()
    flash('Ticket fermé.', 'success')
    return redirect(url_for('admin.support'))


@admin_bp.route('/support/<int:ticket_id>/assign', methods=['POST'])
@admin_required
def support_assign(ticket_id):
    admin = get_admin()
    ticket = SupportTicket.query.get_or_404(ticket_id)
    ticket.assigned_admin_id = admin.id
    ticket.updated_at = datetime.utcnow()
    db.session.commit()
    flash(f'Ticket assigné à {current_user.fullname}.', 'success')
    return redirect(url_for('admin.support'))


# ══════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════════════

@admin_bp.route('/notifications')
@admin_required
def notifications():
    admin = get_admin()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    notifs = PlatformNotification.query.order_by(
        PlatformNotification.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    countries = db.session.query(User.country, func.count(User.id)).filter(
        User.is_deleted == False).group_by(User.country).all()

    return render_template('admin_notifications.html', page='notifications',
                           notifs=notifs, countries=countries)


@admin_bp.route('/notifications/send', methods=['POST'])
@admin_required
def notification_send():
    admin = get_admin()
    title = request.form.get('title', '').strip()
    message_text = request.form.get('message', '').strip()
    target_type = request.form.get('target_type', 'all')
    target_value = request.form.get('target_value', '')

    if not title or not message_text:
        flash('Titre et message requis.', 'error')
        return redirect(url_for('admin.notifications'))

    notification = PlatformNotification(
        admin_id=admin.id,
        title=title,
        message=message_text,
        target_type=target_type,
        target_value=target_value,
        is_sent=True,
        sent_at=datetime.utcnow()
    )
    db.session.add(notification)
    db.session.flush()

    # Link to users
    if target_type == 'all':
        users = User.query.filter_by(is_deleted=False).all()
    elif target_type == 'country':
        users = User.query.filter_by(is_deleted=False, country=target_value).all()
    elif target_type == 'user':
        users = User.query.filter_by(is_deleted=False, id=int(target_value)).all()
    else:
        users = []

    for u in users:
        link = UserNotification(user_id=u.id, notification_id=notification.id)
        db.session.add(link)
        # Also create entry in user-facing notifications table
        user_notif = Notification(
            user_id=u.id,
            title=title,
            message=message_text,
            category='system',
            link='/notifications',
        )
        db.session.add(user_notif)

    log_action(admin, 'notification_send', 'notification', notification.id, {
        'title': title,
        'target_type': target_type,
        'target_value': target_value,
        'recipient_count': len(users)
    })
    db.session.commit()
    flash(f'Notification envoyée à {len(users)} utilisateur(s).', 'success')
    return redirect(url_for('admin.notifications'))


# ══════════════════════════════════════════════════════════════════════════
# LOGS & AUDIT
# ══════════════════════════════════════════════════════════════════════════

@admin_bp.route('/logs')
@admin_required
def logs():
    admin = get_admin()
    page = request.args.get('page', 1, type=int)
    per_page = 30
    action = request.args.get('action', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = AdminLog.query
    if action:
        query = query.filter_by(action=action)
    if date_from:
        query = query.filter(AdminLog.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(AdminLog.created_at <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))

    log_entries = query.order_by(AdminLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)

    # Get distinct actions for filter
    actions = db.session.query(AdminLog.action).distinct().order_by(AdminLog.action).all()

    return render_template('admin_logs.html', page='logs',
                           log_entries=log_entries, actions=actions,
                           action=action, date_from=date_from, date_to=date_to)


# ══════════════════════════════════════════════════════════════════════════
# SETTINGS
# ══════════════════════════════════════════════════════════════════════════

@admin_bp.route('/settings')
@admin_required
def settings():
    admin = get_admin()
    configs = SystemConfig.query.order_by(SystemConfig.key).all()

    # Group configs
    groups = {
        'Général': ['platform_name', 'platform_url', 'support_email', 'base_currency', 'version'],
        'Transferts': ['commission_percent', 'min_transfer', 'max_transfer', 'max_daily_transfer'],
        'Sécurité': ['max_login_attempts', 'session_timeout', 'kyc_required'],
        'Maintenance': ['maintenance_mode', 'maintenance_message'],
        'Notifications': ['sms_enabled', 'email_enabled'],
        'Parrainage': ['referral_bonus', 'referral_bonus_sender', 'referral_bonus_receiver'],
        'API': ['soleaspay_api_key', 'soleaspay_api_url'],
    }

    grouped = {}
    for group_name, keys in groups.items():
        grouped[group_name] = [c for c in configs if c.key in keys]

    # Unassigned
    assigned = set()
    for keys in groups.values():
        assigned.update(keys)
    grouped['Autre'] = [c for c in configs if c.key not in assigned]

    return render_template('admin_settings.html', page='settings', grouped=grouped)


@admin_bp.route('/settings/update', methods=['POST'])
@admin_required
def settings_update():
    admin = get_admin()
    for key, value in request.form.items():
        if key.startswith('config_'):
            config_key = key[7:]  # remove 'config_' prefix
            SystemConfig.set(config_key, value)

    log_action(admin, 'settings_update', 'system_config', None)
    db.session.commit()
    flash('Paramètres mis à jour avec succès.', 'success')
    return redirect(url_for('admin.settings'))


# ══════════════════════════════════════════════════════════════════════════
# ROLES (RBAC)
# ══════════════════════════════════════════════════════════════════════════

@admin_bp.route('/roles')
@admin_required
def roles():
    admin = get_admin()
    admins = AdminUser.query.order_by(AdminUser.created_at.desc()).all()
    users = User.query.filter_by(is_deleted=False).order_by(User.fullname).all()
    return render_template('admin_roles.html', page='roles',
                           admins=admins, users=users)


@admin_bp.route('/roles/add', methods=['POST'])
@admin_required
def roles_add():
    admin = get_admin()
    if admin.role != 'super_admin':
        flash('Seul le Super Admin peut gérer les rôles.', 'error')
        return redirect(url_for('admin.roles'))

    user_id = request.form.get('user_id', type=int)
    role = request.form.get('role', 'admin')

    user = User.query.get(user_id)
    if not user:
        flash('Utilisateur introuvable.', 'error')
        return redirect(url_for('admin.roles'))

    existing = AdminUser.query.filter_by(user_id=user_id).first()
    if existing:
        flash('Cet utilisateur est déjà administrateur.', 'error')
        return redirect(url_for('admin.roles'))

    new_admin = AdminUser(
        user_id=user_id,
        role=role,
        created_by_id=admin.id
    )
    db.session.add(new_admin)
    log_action(admin, 'admin_role_add', 'admin_user', user_id, {
        'role': role,
        'user_email': user.email
    })
    db.session.commit()
    flash(f'Rôle {role} attribué à {user.email}.', 'success')
    return redirect(url_for('admin.roles'))


@admin_bp.route('/roles/<int:admin_id>/update', methods=['POST'])
@admin_required
def roles_update(admin_id):
    admin = get_admin()
    if admin.role != 'super_admin':
        flash('Seul le Super Admin peut modifier les rôles.', 'error')
        return redirect(url_for('admin.roles'))

    target = AdminUser.query.get_or_404(admin_id)
    role = request.form.get('role', 'admin')
    target.role = role
    log_action(admin, 'admin_role_update', 'admin_user', admin_id, {
        'new_role': role,
        'user_email': target.user.email if target.user else 'N/A'
    })
    db.session.commit()
    flash('Rôle mis à jour.', 'success')
    return redirect(url_for('admin.roles'))


@admin_bp.route('/roles/<int:admin_id>/toggle', methods=['POST'])
@admin_required
def roles_toggle(admin_id):
    admin = get_admin()
    if admin.role != 'super_admin':
        flash('Seul le Super Admin peut gérer les rôles.', 'error')
        return redirect(url_for('admin.roles'))

    target = AdminUser.query.get_or_404(admin_id)
    target.is_active = not target.is_active
    log_action(admin, 'admin_role_toggle', 'admin_user', admin_id, {
        'is_active': str(target.is_active)
    })
    db.session.commit()
    flash(f'Administrateur {"activé" if target.is_active else "désactivé"}.', 'success')
    return redirect(url_for('admin.roles'))


# ══════════════════════════════════════════════════════════════════════════
# STATISTICS
# ══════════════════════════════════════════════════════════════════════════

@admin_bp.route('/statistics')
@admin_required
def statistics():
    admin = get_admin()

    # Users by country
    users_by_country = db.session.query(
        User.country, func.count(User.id)
    ).filter(User.is_deleted == False).group_by(User.country).all()

    country_labels = json.dumps([c[0] for c in users_by_country])
    country_values = json.dumps([c[1] for c in users_by_country])

    # Transactions by type
    tx_by_type = db.session.query(
        Transaction.type, func.count(Transaction.id)
    ).group_by(Transaction.type).all()
    tx_type_labels = json.dumps([t[0] for t in tx_by_type])
    tx_type_values = json.dumps([t[1] for t in tx_by_type])

    # Amounts by country
    amount_by_country = db.session.query(
        Transaction.recipient_country,
        func.sum(Transaction.amount)
    ).filter(
        Transaction.status == 'success',
        Transaction.recipient_country.isnot(None)
    ).group_by(Transaction.recipient_country).order_by(
        func.sum(Transaction.amount).desc()
    ).limit(10).all()

    amount_labels = json.dumps([a[0] for a in amount_by_country])
    amount_values = json.dumps([int(a[1]) for a in amount_by_country])

    return render_template('admin_statistics.html', page='statistics',
                           country_labels=country_labels, country_values=country_values,
                           tx_type_labels=tx_type_labels, tx_type_values=tx_type_values,
                           amount_labels=amount_labels, amount_values=amount_values)


# ══════════════════════════════════════════════════════════════════════════
# SEARCH (AJAX)
# ══════════════════════════════════════════════════════════════════════════

@admin_bp.route('/search')
@admin_required
def global_search():
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify({'users': [], 'transactions': []})

    users = User.query.filter(
        User.is_deleted == False,
        db.or_(
            User.fullname.ilike(f'%{query}%'),
            User.email.ilike(f'%{query}%'),
            User.phone.ilike(f'%{query}%'),
            User.qr_identifier.ilike(f'%{query}%')
        )
    ).limit(8).all()

    txs = Transaction.query.filter(
        db.or_(
            Transaction.recipient_name.ilike(f'%{query}%'),
            Transaction.transfer_id.ilike(f'%{query}%')
        )
    ).limit(8).all()

    return jsonify({
        'users': [{'id': u.id, 'name': u.fullname, 'email': u.email, 'avatar': u.first_name[0].upper()} for u in users],
        'transactions': [{'id': t.id, 'type': t.type, 'amount': t.amount, 'currency': t.currency or 'XOF', 'recipient': t.recipient_name, 'status': t.status} for t in txs]
    })


# ══════════════════════════════════════════════════════════════════════════
# PUSH SUBSCRIPTIONS — Admin Panel Page
# ══════════════════════════════════════════════════════════════════════════

@admin_bp.route('/push-subscriptions')
@admin_required
def push_subscriptions():
    """Page listant tous les abonnements Push Web."""
    from services.push_service import get_subscription_stats
    stats = get_subscription_stats()
    return render_template('admin_push_subscriptions.html', page='push_subscriptions', stats=stats)


@admin_bp.route('/api/push-subscriptions')
@admin_required
def api_push_subscriptions():
    """JSON: liste paginée des abonnements Push."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    search = request.args.get('search', '').strip()
    platform_filter = request.args.get('platform', '').strip()
    browser_filter = request.args.get('browser', '').strip()

    query = PushSubscription.query

    if search:
        query = query.join(User).filter(
            db.or_(
                User.fullname.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%'),
                PushSubscription.device_name.ilike(f'%{search}%'),
                PushSubscription.user_agent.ilike(f'%{search}%'),
            )
        )
    if platform_filter:
        query = query.filter(PushSubscription.platform == platform_filter)
    if browser_filter:
        query = query.filter(PushSubscription.browser == browser_filter)

    pagination = query.order_by(PushSubscription.last_seen.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    subs_data = []
    for sub in pagination.items:
        subs_data.append({
            'id': sub.id,
            'user_id': sub.user_id,
            'user_name': sub.user.fullname if sub.user else 'Inconnu',
            'user_email': sub.user.email if sub.user else '',
            'platform': sub.platform or 'unknown',
            'browser': sub.browser or 'unknown',
            'device_name': sub.device_name or 'Inconnu',
            'user_agent': (sub.user_agent or '')[:150],
            'created_at': sub.created_at.isoformat() if sub.created_at else None,
            'last_seen': sub.last_seen.isoformat() if sub.last_seen else None,
            'updated_at': sub.updated_at.isoformat() if sub.updated_at else None,
        })

    return jsonify({
        'success': True,
        'subscriptions': subs_data,
        'page': pagination.page,
        'pages': pagination.pages,
        'total': pagination.total,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
    })


@admin_bp.route('/api/push-send', methods=['POST'])
@admin_required
def api_push_send():
    """Envoyer une notification Push à tous les utilisateurs (broadcast)."""
    from services.push_service import send_push_to_all, get_all_active_subscriptions
    data = request.get_json(silent=True) or {}
    title = data.get('title', 'TransAfrik')
    body = data.get('body', 'Nouvelle notification de TransAfrik.')
    url = data.get('url', '/')

    # Create user-facing Notification entries for unique users
    subs = get_all_active_subscriptions()
    notified_user_ids = set()
    for sub in subs:
        if sub.user_id not in notified_user_ids:
            notified_user_ids.add(sub.user_id)
            notif = Notification(
                user_id=sub.user_id,
                title=title,
                message=body,
                category='system',
                link=url,
            )
            db.session.add(notif)
    db.session.commit()

    result = send_push_to_all(title=title, body=body, url=url)
    return jsonify(result)


@admin_bp.route('/api/push-delete/<int:subscription_id>', methods=['DELETE'])
@admin_required
def api_push_delete(subscription_id):
    """Supprimer un abonnement Push (admin)."""
    from services.push_service import remove_subscription_by_id
    result = remove_subscription_by_id(subscription_id)
    return jsonify(result)


# ══════════════════════════════════════════════════════════════════════════
# PAIEMENT REQUESTS (RECEIVE MONEY) — Admin
# ══════════════════════════════════════════════════════════════════════════

@admin_bp.route('/payment-requests')
@admin_required
def payment_requests():
    """Page listant toutes les demandes de paiement (Recevoir)."""
    admin = get_admin()
    page = request.args.get('page', 1, type=int)
    per_page = 25
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '').strip()

    query = PaymentRequest.query

    if status_filter:
        query = query.filter_by(status=status_filter)
    if search:
        query = query.join(User, PaymentRequest.receiver_id == User.id).filter(
            db.or_(
                User.fullname.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%'),
                PaymentRequest.request_code.ilike(f'%{search}%'),
                PaymentRequest.description.ilike(f'%{search}%'),
            )
        )

    requests_paginated = query.order_by(PaymentRequest.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Aggregates for stats
    pending_count = PaymentRequest.query.filter_by(status='PENDING').count()
    paid_count = PaymentRequest.query.filter_by(status='PAID').count()
    cancelled_count = PaymentRequest.query.filter_by(status='CANCELLED').count()
    expired_count = PaymentRequest.query.filter_by(status='EXPIRED').count()

    # Total amount of paid requests
    total_paid = db.session.query(func.coalesce(func.sum(PaymentRequest.amount), 0)).filter(
        PaymentRequest.status == 'PAID'
    ).scalar()

    return render_template(
        'admin_payment_requests.html',
        page='payment_requests',
        requests=requests_paginated,
        pending_count=pending_count,
        paid_count=paid_count,
        cancelled_count=cancelled_count,
        expired_count=expired_count,
        total_paid=int(total_paid),
        status_filter=status_filter,
        search=search,
    )


@admin_bp.route('/payment-requests/<int:pr_id>')
@admin_required
def payment_request_detail(pr_id):
    """Détail d'une demande de paiement."""
    admin = get_admin()
    payment_request = PaymentRequest.query.get_or_404(pr_id)
    receiver = User.query.get(payment_request.receiver_id)

    # Related transaction receive record
    tx_receive = TransactionReceive.query.filter_by(
        user_id=payment_request.receiver_id,
        description=f'Paiement reçu (request {payment_request.request_code})'
    ).first()

    return render_template(
        'admin_payment_requests.html',
        page='payment_requests_detail',
        payment_request=payment_request,
        receiver=receiver,
        tx_receive=tx_receive,
    )


@admin_bp.route('/payment-requests/<int:pr_id>/cancel', methods=['POST'])
@admin_required
def admin_cancel_payment_request(pr_id):
    """Forcer l'annulation d'une demande de paiement."""
    admin = get_admin()
    pr = PaymentRequest.query.get_or_404(pr_id)
    if pr.status not in ('PENDING',):
        flash('Seules les demandes en attente peuvent être annulées.', 'error')
        return redirect(url_for('admin.payment_requests'))

    pr.status = 'CANCELLED'
    log_action(admin, 'payment_request_cancel', 'payment_request', pr.id, {
        'request_code': pr.request_code,
        'receiver_id': pr.receiver_id,
        'amount': pr.amount,
    })
    db.session.commit()
    flash(f'Demande {pr.request_code} annulée.', 'success')
    return redirect(url_for('admin.payment_requests'))


@admin_bp.route('/api/payment-requests')
@admin_required
def api_payment_requests():
    """JSON: liste paginée des demandes de paiement."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    status = request.args.get('status', '')
    search = request.args.get('search', '').strip()

    query = PaymentRequest.query

    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.join(User, PaymentRequest.receiver_id == User.id).filter(
            db.or_(
                User.fullname.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%'),
                PaymentRequest.request_code.ilike(f'%{search}%'),
            )
        )

    pagination = query.order_by(PaymentRequest.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    items = []
    for pr in pagination.items:
        receiver = User.query.get(pr.receiver_id)
        payer = User.query.get(pr.payer_id) if pr.payer_id else None
        items.append({
            'id': pr.id,
            'request_code': pr.request_code,
            'receiver_id': pr.receiver_id,
            'receiver_name': receiver.fullname if receiver else 'Inconnu',
            'receiver_email': receiver.email if receiver else '',
            'payer_name': payer.fullname if payer else None,
            'amount': pr.amount,
            'currency': pr.currency or 'XOF',
            'description': pr.description or '',
            'status': pr.status,
            'created_at': pr.created_at.isoformat() if pr.created_at else None,
            'expires_at': pr.expires_at.isoformat() if pr.expires_at else None,
            'paid_at': pr.paid_at.isoformat() if pr.paid_at else None,
        })

    return jsonify({
        'success': True,
        'items': items,
        'page': pagination.page,
        'pages': pagination.pages,
        'total': pagination.total,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
    })


# ══════════════════════════════════════════════════════════════════════════
# REVIEWS / AVIS CLIENTS — Admin
# ══════════════════════════════════════════════════════════════════════════

@admin_bp.route('/reviews')
@admin_required
def reviews():
    """Page listant tous les avis clients."""
    admin = get_admin()
    page = request.args.get('page', 1, type=int)
    per_page = 25
    approved_filter = request.args.get('approved', '')
    search = request.args.get('search', '').strip()

    query = Review.query

    if approved_filter == 'approved':
        query = query.filter_by(approved=True)
    elif approved_filter == 'pending':
        query = query.filter_by(approved=False)
    if search:
        query = query.join(User).filter(
            db.or_(
                User.fullname.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%'),
                Review.comment.ilike(f'%{search}%'),
                Review.title.ilike(f'%{search}%'),
            )
        )

    reviews_paginated = query.order_by(Review.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Stats
    total_reviews = Review.query.count()
    approved_count = Review.query.filter_by(approved=True).count()
    pending_count = Review.query.filter_by(approved=False).count()
    verified_count = Review.query.filter_by(verified=True, approved=True).count()
    avg_rating = db.session.query(func.coalesce(func.avg(Review.rating), 0)).filter(
        Review.approved == True
    ).scalar()
    avg_rating = round(float(avg_rating), 1)

    return render_template(
        'admin_reviews.html',
        page='reviews',
        reviews=reviews_paginated,
        total_reviews=total_reviews,
        approved_count=approved_count,
        pending_count=pending_count,
        verified_count=verified_count,
        avg_rating=avg_rating,
        approved_filter=approved_filter,
        search=search,
    )


@admin_bp.route('/reviews/<int:review_id>/approve', methods=['POST'])
@admin_required
def reviews_approve(review_id):
    """Approuve un avis pour affichage public."""
    admin = get_admin()
    review = Review.query.get_or_404(review_id)
    review.approved = True
    review.updated_at = datetime.utcnow()
    log_action(admin, 'review_approve', 'review', review.id, {
        'rating': review.rating,
        'user_id': review.user_id,
    })
    db.session.commit()
    flash(f'Avis #{review.id} approuvé avec succès.', 'success')
    return redirect(url_for('admin.reviews'))


@admin_bp.route('/reviews/<int:review_id>/reject', methods=['POST'])
@admin_required
def reviews_reject(review_id):
    """Rejette/Désapprouve un avis (le masque du site)."""
    admin = get_admin()
    review = Review.query.get_or_404(review_id)
    review.approved = False
    review.updated_at = datetime.utcnow()
    log_action(admin, 'review_reject', 'review', review.id, {
        'rating': review.rating,
        'user_id': review.user_id,
    })
    db.session.commit()
    flash(f'Avis #{review.id} désapprouvé.', 'warning')
    return redirect(url_for('admin.reviews'))


@admin_bp.route('/reviews/<int:review_id>/delete', methods=['POST'])
@admin_required
def reviews_delete(review_id):
    """Supprime définitivement un avis."""
    admin = get_admin()
    review = Review.query.get_or_404(review_id)
    user_id = review.user_id
    log_action(admin, 'review_delete', 'review', review.id, {
        'rating': review.rating,
        'user_id': review.user_id,
        'comment': (review.comment or '')[:200],
    })
    db.session.delete(review)
    db.session.commit()
    flash('Avis supprimé définitivement.', 'info')
    return redirect(url_for('admin.reviews'))


@admin_bp.route('/api/reviews')
@admin_required
def api_reviews():
    """JSON: liste paginée des avis."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    approved = request.args.get('approved', '')
    search = request.args.get('search', '').strip()

    query = Review.query

    if approved == 'approved':
        query = query.filter_by(approved=True)
    elif approved == 'pending':
        query = query.filter_by(approved=False)
    if search:
        query = query.join(User).filter(
            db.or_(
                User.fullname.ilike(f'%{search}%'),
                Review.comment.ilike(f'%{search}%'),
            )
        )

    pagination = query.order_by(Review.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'success': True,
        'reviews': [r.to_dict() for r in pagination.items],
        'page': pagination.page,
        'pages': pagination.pages,
        'total': pagination.total,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
    })
