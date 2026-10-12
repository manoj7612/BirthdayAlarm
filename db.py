"""SQLite database helpers."""
import sqlite3

from config import Config


def get_db():
    """Return a new database connection with row-based access."""
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the tables if they do not already exist."""
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            birthday      TEXT NOT NULL,               -- YYYY-MM-DD
            created_at    TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS members (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            name         TEXT NOT NULL,
            birthday     TEXT NOT NULL,                -- YYYY-MM-DD
            email        TEXT,
            relationship TEXT,
            created_at   TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            person_name TEXT NOT NULL,
            birthday    TEXT NOT NULL,
            sent_to     TEXT NOT NULL,
            status      TEXT NOT NULL,                 -- 'sent' | 'simulated' | 'failed: ...'
            sent_at     TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()
    conn.close()
