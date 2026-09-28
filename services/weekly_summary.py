"""
Service de bilan hebdomadaire — TransAfrik.

Chaque lundi à 7h (heure d'Afrique de l'Ouest par défaut), envoie à chaque
utilisateur actif un récapitulatif de ses transactions de la semaine
précédente (lundi 00:00 → dimanche 23:59:59).

Le job est idempotent : un enregistrement `WeeklySummaryRun` (clé unique par
semaine) empêche tout doublon, y compris avec plusieurs workers gunicorn.

Exécution manuelle (pour test ou cron externe) :
    python -m services.weekly_summary
"""

import logging
from datetime import datetime, timedelta

from models import (
    db,
    User,
    Transaction,
    TransactionReceive,
    Notification,
    WeeklySummaryRun,
)
from services.push_service import send_push_to_user

logger = logging.getLogger(__name__)

# Planification par défaut : lundi 07:00.
WEEKLY_SUMMARY_DAY = "mon"
WEEKLY_SUMMARY_HOUR = 7
WEEKLY_SUMMARY_MINUTE = 0

# Par défaut, ne notifier que les utilisateurs ayant eu au moins une
# transaction sur la semaine (évite de spammer les comptes inactifs).
INCLUDE_INACTIVE_USERS = False


def _fmt(amount) -> str:
    """Formate un montant entier avec séparateur de milliers (ex: 1 250)."""
    return f"{int(amount or 0):,}".replace(",", " ")


def compute_week_bounds(now=None):
    """Calcule les bornes de la semaine précédente.

    Returns:
        (week_start, week_end, run_key)
        - week_start : lundi 00:00 (inclus), datetime naïf UTC
        - week_end   : lundi 00:00 suivant (exclu)
        - run_key    : date ISO du lundi de la semaine résumée (ex: "2026-09-21")
    """
    if now is None:
        now = datetime.utcnow()

    days_since_monday = now.weekday()  # lundi = 0
    this_monday = (now - timedelta(days=days_since_monday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_start = this_monday - timedelta(days=7)
    week_end = this_monday
    run_key = week_start.strftime("%Y-%m-%d")
    return week_start, week_end, run_key


def build_user_summary(user_id, week_start, week_end):
    """Construit le bilan hebdomadaire d'un utilisateur.

    Returns:
        dict avec les totaux (sent, withdrawn, deposited, received, ...)
        ou None si aucune transaction sur la période.
    """
    sent_amount, sent_fees, sent_count = db.session.query(
        db.func.coalesce(db.func.sum(Transaction.amount), 0),
        db.func.coalesce(db.func.sum(Transaction.fee), 0),
        db.func.count(Transaction.id),
    ).filter(
        Transaction.user_id == user_id,
        Transaction.type == "send",
        Transaction.status == "success",
        Transaction.created_at >= week_start,
        Transaction.created_at < week_end,
    ).first()

    withdrawn_amount, withdrawn_count = db.session.query(
        db.func.coalesce(db.func.sum(Transaction.amount), 0),
        db.func.count(Transaction.id),
    ).filter(
        Transaction.user_id == user_id,
        Transaction.type == "withdraw",
        Transaction.status == "success",
        Transaction.created_at >= week_start,
        Transaction.created_at < week_end,
    ).first()

    deposited_amount, deposited_count = db.session.query(
        db.func.coalesce(db.func.sum(Transaction.amount), 0),
        db.func.count(Transaction.id),
    ).filter(
        Transaction.user_id == user_id,
        Transaction.type == "deposit",
        Transaction.status == "success",
        Transaction.created_at >= week_start,
        Transaction.created_at < week_end,
    ).first()

    received_amount = db.session.query(
        db.func.coalesce(db.func.sum(TransactionReceive.amount), 0)
    ).filter(
        TransactionReceive.receiver_id == user_id,
        TransactionReceive.status == "completed",
        TransactionReceive.created_at >= week_start,
        TransactionReceive.created_at < week_end,
    ).scalar()

    received_count = db.session.query(
        db.func.count(TransactionReceive.id)
    ).filter(
        TransactionReceive.receiver_id == user_id,
        TransactionReceive.status == "completed",
        TransactionReceive.created_at >= week_start,
        TransactionReceive.created_at < week_end,
    ).scalar()

    tx_count = (
        int(sent_count or 0)
        + int(withdrawn_count or 0)
        + int(deposited_count or 0)
        + int(received_count or 0)
    )

    if tx_count == 0:
        return None

    return {
        "sent": int(sent_amount or 0),
        "sent_fees": int(sent_fees or 0),
        "sent_count": int(sent_count or 0),
        "withdrawn": int(withdrawn_amount or 0),
        "withdrawn_count": int(withdrawn_count or 0),
        "deposited": int(deposited_amount or 0),
        "deposited_count": int(deposited_count or 0),
        "received": int(received_amount or 0),
        "received_count": int(received_count or 0),
        "tx_count": tx_count,
    }


def _build_message(user, summary, week_start, week_end):
    """Construit le titre et le corps du bilan hebdomadaire."""
    currency = (user.currency or "XOF").upper()
    start_label = week_start.strftime("%d/%m")
    end_label = (week_end - timedelta(days=1)).strftime("%d/%m")

    title = "📊 Votre bilan hebdomadaire"

    if summary["tx_count"] == 0:
        body = f"Semaine du {start_label} au {end_label} : aucune transaction."
        return title, body

    lines = [
        f"Semaine du {start_label} au {end_label} • {summary['tx_count']} transaction(s)"
    ]
    if summary["received"]:
        lines.append(f"Reçus : {_fmt(summary['received'])} {currency}")
    if summary["sent"]:
        lines.append(f"Envoyés : {_fmt(summary['sent'])} {currency}")
    if summary["deposited"]:
        lines.append(f"Dépôts : {_fmt(summary['deposited'])} {currency}")
    if summary["withdrawn"]:
        lines.append(f"Retraits : {_fmt(summary['withdrawn'])} {currency}")

    return title, "\n".join(lines)


def send_weekly_summaries(now=None, force=False):
    """Envoie les bilans hebdomadaires de la semaine précédente.

    Idempotent : si la semaine a déjà été traitée (run_key en base), ne fait
    rien (sauf force=True).

    Returns:
        dict de statistiques.
    """
    week_start, week_end, run_key = compute_week_bounds(now)

    existing = WeeklySummaryRun.query.filter_by(run_key=run_key).first()
    if existing and not force:
        logger.info(f"WEEKLY SUMMARY | {run_key} déjà traité — ignoré.")
        return {"skipped": True, "run_key": run_key}

    run = existing or WeeklySummaryRun(
        run_key=run_key,
        week_start=week_start,
        week_end=week_end,
        started_at=datetime.utcnow(),
    )
    db.session.add(run)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        # Un autre worker vient d'insérer le run_key : on abandonne proprement.
        logger.info(f"WEEKLY SUMMARY | {run_key} déjà inséré par un autre worker — ignoré.")
        return {"skipped": True, "run_key": run_key}

    users = User.query.filter_by(is_active=True, is_deleted=False).all()

    stats = {
        "run_key": run_key,
        "week_start": week_start.isoformat(),
        "week_end": (week_end - timedelta(seconds=1)).isoformat(),
        "users_scanned": len(users),
        "users_notified": 0,
        "users_skipped": 0,
        "push_sent": 0,
        "push_failed": 0,
    }

    for user in users:
        try:
            summary = build_user_summary(user.id, week_start, week_end)
            if summary is None:
                if not INCLUDE_INACTIVE_USERS:
                    stats["users_skipped"] += 1
                    continue
                summary = {
                    "sent": 0, "sent_fees": 0, "sent_count": 0,
                    "withdrawn": 0, "withdrawn_count": 0,
                    "deposited": 0, "deposited_count": 0,
                    "received": 0, "received_count": 0,
                    "tx_count": 0,
                }

            title, body = _build_message(user, summary, week_start, week_end)

            # Notification in-app (centre de notifications)
            notif = Notification(
                user_id=user.id,
                title=title,
                message=body,
                category="system",
                link="/dashboard",
            )
            db.session.add(notif)
            db.session.commit()

            # Push web (si l'utilisateur l'autorise)
            if user.notification_push is not False:
                r = send_push_to_user(
                    user_id=user.id,
                    title=title,
                    body=body,
                    url="/dashboard",
                    tag=f"weekly-summary-{run_key}",
                    data={"type": "weekly_summary", "run_key": run_key},
                )
                stats["push_sent"] += r.get("sent", 0)
                stats["push_failed"] += r.get("failed", 0)

            stats["users_notified"] += 1
        except Exception as e:
            db.session.rollback()
            logger.error(f"WEEKLY SUMMARY | erreur user={user.id}: {e}", exc_info=True)

    run.completed_at = datetime.utcnow()
    run.users_notified = stats["users_notified"]
    run.users_skipped = stats["users_skipped"]
    run.push_sent = stats["push_sent"]
    run.push_failed = stats["push_failed"]
    db.session.add(run)
    db.session.commit()

    logger.info(
        f"WEEKLY SUMMARY | {run_key} terminé | "
        f"scannés={stats['users_scanned']} notifiés={stats['users_notified']} "
        f"ignorés={stats['users_skipped']} push_envoyés={stats['push_sent']} "
        f"push_échoués={stats['push_failed']}"
    )
    return stats


if __name__ == "__main__":
    # Exécution manuelle : python -m services.weekly_summary
    # (ou via un cron externe type Heroku Scheduler).
    import os
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

    from app import app

    with app.app_context():
        result = send_weekly_summaries()
    print(result)
