"""Background scheduler that checks for birthdays and sends notifications."""
import logging
import threading
import time
from datetime import date, datetime

from config import Config
from db import get_db
from email_service import is_configured, send_email

logger = logging.getLogger(__name__)


def next_birthday_info(birthday_str):
    """Return next-birthday details for a 'YYYY-MM-DD' date."""
    today = date.today()
    bd = datetime.strptime(birthday_str, "%Y-%m-%d").date()
    next_bd = bd.replace(year=today.year)
    if next_bd < today:
        next_bd = next_bd.replace(year=today.year + 1)
    days = (next_bd - today).days
    return {
        "next_date": next_bd.strftime("%B %d, %Y"),
        "days_until": days,
        "is_today": days == 0,
        "age_turning": next_bd.year - bd.year,
    }


def _build_email_html(user_name, person_name, birthday_str, age_turning,
                      relationship=None, is_self=False):
    """Build a friendly HTML reminder email."""
    when = datetime.strptime(birthday_str, "%Y-%m-%d").strftime("%B %d")

    if is_self:
        headline = f"Today is <strong>your</strong> birthday ({when})!"
        detail = f"You are turning <strong>{age_turning}</strong> years old."
        call_to_action = "Make it a great one! 🎂🎈"
    else:
        rel = f" ({relationship})" if relationship else ""
        headline = f"Today is <strong>{person_name}{rel}</strong>'s birthday ({when})!"
        detail = f"They are turning <strong>{age_turning}</strong> years old."
        call_to_action = "Don't forget to wish them a wonderful day! 🎂🎈"

    return f"""\
<html>
  <body style="margin:0;padding:24px;background:#f4f6fb;font-family:Arial,Helvetica,sans-serif;">
    <div style="max-width:520px;margin:auto;background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 6px 24px rgba(0,0,0,.08);">
      <div style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:28px;text-align:center;color:#ffffff;">
        <h1 style="margin:0;font-size:24px;">🎉 Birthday Reminder</h1>
      </div>
      <div style="padding:28px;color:#333333;">
        <p style="font-size:16px;">Hi {user_name},</p>
        <p style="font-size:16px;">{headline}</p>
        <p style="font-size:16px;">{detail}</p>
        <p style="font-size:16px;">{call_to_action}</p>
        <p style="margin-top:28px;text-align:center;">
          <a href="http://localhost:5000/dashboard"
             style="display:inline-block;background:#6366f1;color:#ffffff;text-decoration:none;padding:12px 24px;border-radius:8px;">
            Open Dashboard
          </a>
        </p>
      </div>
      <div style="background:#f4f6fb;padding:16px;text-align:center;color:#888888;font-size:12px;">
        Sent by Birthday Alarm
      </div>
    </div>
  </body>
</html>
"""


def _already_sent(conn, user_id, person_name, birthday_str):
    """Avoid sending duplicate notifications for the same person on the same day."""
    today_prefix = datetime.now().strftime("%Y-%m-%d")
    row = conn.execute(
        "SELECT id FROM notifications "
        "WHERE user_id = ? AND person_name = ? AND birthday = ? AND sent_at LIKE ?",
        (user_id, person_name, birthday_str, today_prefix + "%"),
    ).fetchone()
    return row is not None


def _record_notification(conn, user_id, person_name, birthday_str, sent_to, status):
    conn.execute(
        "INSERT INTO notifications (user_id, person_name, birthday, sent_to, status) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, person_name, birthday_str, sent_to, status),
    )
    conn.commit()


def check_birthdays():
    """Find every birthday that is today and email the relevant user."""
    today = date.today()
    mmdd = today.strftime("%m-%d")
    sent_count = 0

    conn = get_db()
    users = conn.execute("SELECT * FROM users").fetchall()

    for user in users:
        user_id = user["id"]

        # 1) The user's own birthday.
        if user["birthday"][5:] == mmdd and not _already_sent(conn, user_id, user["name"], user["birthday"]):
            info = next_birthday_info(user["birthday"])
            if is_configured():
                body = _build_email_html(user["name"], user["name"], user["birthday"],
                                         info["age_turning"], is_self=True)
                ok, msg = send_email(user["email"], f"🎂 Happy Birthday, {user['name']}!", body)
                _record_notification(conn, user_id, user["name"], user["birthday"],
                                     user["email"], "sent" if ok else f"failed: {msg}")
                if ok:
                    sent_count += 1
            else:
                _record_notification(conn, user_id, user["name"], user["birthday"],
                                     user["email"], "simulated")

        # 2) Members the user is tracking.
        members = conn.execute(
            "SELECT * FROM members WHERE user_id = ?", (user_id,)
        ).fetchall()
        for member in members:
            if member["birthday"][5:] == mmdd and not _already_sent(conn, user_id, member["name"], member["birthday"]):
                info = next_birthday_info(member["birthday"])
                if is_configured():
                    body = _build_email_html(user["name"], member["name"], member["birthday"],
                                             info["age_turning"], member["relationship"])
                    ok, msg = send_email(user["email"], f"🎉 Birthday Reminder: {member['name']}", body)
                    _record_notification(conn, user_id, member["name"], member["birthday"],
                                         user["email"], "sent" if ok else f"failed: {msg}")
                    if ok:
                        sent_count += 1
                else:
                    _record_notification(conn, user_id, member["name"], member["birthday"],
                                         user["email"], "simulated")

    conn.close()
    if sent_count:
        logger.info("Birthday check sent %d notification(s).", sent_count)
    return sent_count


def _loop(interval):
    while True:
        try:
            check_birthdays()
        except Exception:  # noqa: BLE001 - keep the scheduler alive
            logger.exception("Birthday check failed")
        time.sleep(interval)


def start_scheduler():
    """Start the background birthday-checking thread."""
    thread = threading.Thread(
        target=_loop,
        args=(Config.SCHEDULER_INTERVAL,),
        daemon=True,
        name="birthday-scheduler",
    )
    thread.start()
    logger.info("Birthday scheduler started (checks every %d seconds).", Config.SCHEDULER_INTERVAL)
