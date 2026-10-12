# 🎂 Birthday Alarm

A professional, simple Flask web application that sends you email reminders on
birthdays — your own, and the birthdays of the family members and friends you add.

## Features

- **Sign up / Sign in** with your name, email, password and birthday.
- **Automatic birthday alarm** — a background scheduler checks every day and
  emails you on the exact date.
- **Track unlimited members** — add, edit and delete people whose birthdays you
  want to be reminded about.
- **Notification history** — see every reminder that has been sent.
- **Professional UI** — clean, responsive interface with no heavy front-end build.

## Project structure

```
python/
├── app.py               # Flask routes & application logic
├── config.py            # Configuration (email/SMTP, secret key)
├── db.py                # SQLite database helpers
├── email_service.py     # SMTP email delivery
├── scheduler.py         # Background birthday checker
├── requirements.txt
├── templates/           # HTML pages
└── static/css/          # Stylesheet
```

## Setup

1. **Install dependencies**

   ```bash
   python3 -m pip install -r requirements.txt
   ```

2. **Configure email (so real notifications are sent)**

   Set the following environment variables (otherwise the app runs in
   *simulation* mode and simply logs reminders in the dashboard):

   ```bash
   export SMTP_HOST="smtp.gmail.com"
   export SMTP_PORT="465"
   export SMTP_USER="you@gmail.com"
   export SMTP_PASSWORD="your-app-password"   # Gmail: use an App Password
   export MAIL_FROM="you@gmail.com"
   ```

   > For Gmail, enable 2-Step Verification and create an **App Password**
   > (Google Account → Security → App passwords). Never commit real passwords.

3. **Run the app**

   ```bash
   python3 app.py
   ```

   Then open http://localhost:5000

## How it works

- The scheduler runs a background thread that wakes up periodically
  (`SCHEDULER_INTERVAL`, default 1 hour) and checks for birthdays matching
  today's month/day.
- Duplicate sends are prevented, so you only get one email per person per day.
- If SMTP is not configured, reminders are recorded as `simulated` so you can
  still test the full flow end to end.
