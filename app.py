"""Birthday Alarm — a simple, professional Flask web application.

Features:
  * Sign up with name, email, password and your own birthday.
  * Get an email notification on your birthday (and for every member you add).
  * Add, edit and remove members (family/friends) whose birthdays you track.
"""
import functools
import logging
from datetime import date, datetime

from flask import (Flask, flash, redirect, render_template, request, session,
                   url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from db import get_db, init_db
from scheduler import check_birthdays, next_birthday_info, start_scheduler

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config["SECRET_KEY"] = Config.SECRET_KEY

# Ensure tables exist on first launch.
init_db()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def login_required(view):
    """Decorator that requires an authenticated session."""

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("login"))
        return view(**kwargs)

    return wrapped_view


def current_user():
    """Return the logged-in user's row, or None."""
    if "user_id" not in session:
        return None
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE id = ?", (session["user_id"],)
        ).fetchone()
    finally:
        conn.close()


def parse_birthday(value):
    """Validate a birthday and return it as YYYY-MM-DD, or None if invalid."""
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    if parsed > date.today():
        return None
    return parsed.strftime("%Y-%m-%d")


@app.context_processor
def inject_globals():
    """Make the current user available to every template."""
    return {"user": current_user()}


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        birthday = request.form.get("birthday", "")

        error = None
        if not name:
            error = "Name is required."
        elif not email or "@" not in email:
            error = "A valid email address is required."
        elif not password or len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != confirm:
            error = "Passwords do not match."
        elif not parse_birthday(birthday):
            error = "Please enter a valid birthday (it cannot be in the future)."

        conn = get_db()
        if error is None:
            exists = conn.execute(
                "SELECT id FROM users WHERE email = ?", (email,)
            ).fetchone()
            if exists:
                error = "An account with that email already exists."

        if error:
            conn.close()
            flash(error, "danger")
            return render_template("signup.html")

        conn.execute(
            "INSERT INTO users (name, email, password_hash, birthday) VALUES (?, ?, ?, ?)",
            (name, email, generate_password_hash(password), parse_birthday(birthday)),
        )
        conn.commit()
        user_id = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()["id"]
        conn.close()

        session.clear()
        session["user_id"] = user_id
        flash("Welcome aboard! Your birthday alarm is now active. 🎉", "success")
        return redirect(url_for("dashboard"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "danger")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        flash(f"Welcome back, {user['name']}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    conn = get_db()

    members = conn.execute(
        "SELECT * FROM members WHERE user_id = ? ORDER BY birthday", (user["id"],)
    ).fetchall()
    notifications = conn.execute(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY sent_at DESC LIMIT 10",
        (user["id"],),
    ).fetchall()
    conn.close()

    user_info = next_birthday_info(user["birthday"])

    member_rows = []
    for member in members:
        row = dict(member)
        row["info"] = next_birthday_info(member["birthday"])
        member_rows.append(row)

    upcoming = [m for m in member_rows if m["info"]["days_until"] <= 7]

    return render_template(
        "dashboard.html",
        user_info=user_info,
        members=member_rows,
        upcoming_count=len(upcoming),
        notifications=notifications,
    )


# ---------------------------------------------------------------------------
# Members (CRUD)
# ---------------------------------------------------------------------------

@app.route("/members/add", methods=["GET", "POST"])
@login_required
def add_member():
    user = current_user()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        birthday = request.form.get("birthday", "")
        email = request.form.get("email", "").strip()
        relationship = request.form.get("relationship", "").strip()

        error = None
        if not name:
            error = "Member name is required."
        elif not parse_birthday(birthday):
            error = "Please enter a valid birthday."

        if error:
            flash(error, "danger")
            return render_template("member_form.html", member=None)

        conn = get_db()
        conn.execute(
            "INSERT INTO members (user_id, name, birthday, email, relationship) "
            "VALUES (?, ?, ?, ?, ?)",
            (user["id"], name, parse_birthday(birthday), email or None, relationship or None),
        )
        conn.commit()
        conn.close()

        flash(f"{name} has been added and their birthday alarm is set. 🎂", "success")
        return redirect(url_for("dashboard"))

    return render_template("member_form.html", member=None)


@app.route("/members/<int:member_id>/edit", methods=["GET", "POST"])
@login_required
def edit_member(member_id):
    user = current_user()
    conn = get_db()
    member = conn.execute(
        "SELECT * FROM members WHERE id = ? AND user_id = ?", (member_id, user["id"])
    ).fetchone()

    if member is None:
        conn.close()
        flash("Member not found.", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        birthday = request.form.get("birthday", "")
        email = request.form.get("email", "").strip()
        relationship = request.form.get("relationship", "").strip()

        error = None
        if not name:
            error = "Member name is required."
        elif not parse_birthday(birthday):
            error = "Please enter a valid birthday."

        if error:
            conn.close()
            flash(error, "danger")
            return render_template("member_form.html", member=member)

        conn.execute(
            "UPDATE members SET name = ?, birthday = ?, email = ?, relationship = ? "
            "WHERE id = ? AND user_id = ?",
            (name, parse_birthday(birthday), email or None, relationship or None,
             member_id, user["id"]),
        )
        conn.commit()
        conn.close()

        flash(f"{name}'s details have been updated.", "success")
        return redirect(url_for("dashboard"))

    conn.close()
    return render_template("member_form.html", member=member)


@app.route("/members/<int:member_id>/delete", methods=["POST"])
@login_required
def delete_member(member_id):
    user = current_user()
    conn = get_db()
    conn.execute(
        "DELETE FROM members WHERE id = ? AND user_id = ?", (member_id, user["id"])
    )
    conn.commit()
    conn.close()
    flash("Member removed.", "info")
    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

@app.route("/notifications")
@login_required
def notifications():
    user = current_user()
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY sent_at DESC",
        (user["id"],),
    ).fetchall()
    conn.close()
    return render_template("notifications.html", notifications=rows)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    start_scheduler()
    # use_reloader=False keeps the background scheduler from starting twice.
    app.run(host="0.0.0.0", port=5001, debug=True, use_reloader=False)
