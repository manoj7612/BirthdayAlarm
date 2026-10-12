"""Application configuration.

All sensitive values can be overridden with environment variables so that
credentials never have to be hard-coded in source files.
"""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Secret key used to sign the session cookie. Change this in production.
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-key-in-production")

    # SQLite database file.
    DATABASE = os.path.join(BASE_DIR, "birthday_alarm.db")

    # ---- Email (SMTP) settings -------------------------------------------
    # For Gmail use: host=smtp.gmail.com, port=465, and an "App Password".
    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    MAIL_FROM = os.environ.get("MAIL_FROM", "birthday-alarm@example.com")

    # How often (in seconds) the background scheduler checks for birthdays.
    SCHEDULER_INTERVAL = int(os.environ.get("SCHEDULER_INTERVAL", "3600"))
