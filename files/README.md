# Finance Dashboard — Flask + MySQL

A full-stack personal expense tracker with user authentication and email verification.

---

## Features
- Register / Login / Logout
- Email verification (required before login)
- Forgot password + reset via email link
- Add / Edit / Delete expenses
- Dashboard with:
  - Daily expenses bar chart (7-day / 14-day / month toggle)
  - Category spending horizontal bar chart
  - Summary metric cards
  - Recent transactions list

---

## Project Structure

```
finance_app/
├── app.py                  # Flask application + all routes
├── schema.sql              # MySQL database schema
├── requirements.txt
├── static/
│   ├── css/style.css
│   └── js/main.js
└── templates/
    ├── base.html
    ├── login.html
    ├── register.html
    ├── forgot_password.html
    ├── reset_password.html
    ├── dashboard.html
    ├── expenses.html
    └── add_expense.html
```

---

## Setup

### 1. Create the database

```bash
mysql -u root -p < schema.sql
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure credentials

Edit `app.py` and update these sections, **or** set environment variables:

**Database:**
```python
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "your_mysql_password",
    "database": "finance_db",
}
```

**Gmail SMTP (for email verification):**
```python
SMTP_CONFIG = {
    "host":     "smtp.gmail.com",
    "port":     587,
    "user":     "your_gmail@gmail.com",
    "password": "your_gmail_app_password",  # Use an App Password, not your main Gmail password
    "from":     "Finance App <your_gmail@gmail.com>",
}
```

> To generate a Gmail App Password:
> Google Account → Security → 2-Step Verification → App passwords

**App URL (for email links):**
```python
APP_URL = "http://127.0.0.1:5000"  # Change to your domain in production
```

### 4. Run the app

```bash
python app.py
```

Visit: http://127.0.0.1:5000

---

## Environment Variables (optional)

You can set these instead of editing `app.py`:

| Variable       | Description                     |
|----------------|---------------------------------|
| `DB_HOST`      | MySQL host (default: localhost) |
| `DB_USER`      | MySQL user                      |
| `DB_PASSWORD`  | MySQL password                  |
| `DB_NAME`      | Database name (finance_db)      |
| `SMTP_HOST`    | SMTP server host                |
| `SMTP_PORT`    | SMTP port (default: 587)        |
| `SMTP_USER`    | SMTP login email                |
| `SMTP_PASSWORD`| SMTP password / App Password    |
| `SMTP_FROM`    | Sender display name + email     |
| `APP_URL`      | Public URL for email links      |
| `SECRET_KEY`   | Flask session secret key        |

---

## Email verification flow

1. User registers → verification email sent
2. User clicks link → account activated
3. User can now log in
4. If link expires (24h), user can request a new one from the login page

## Password reset flow

1. User clicks "Forgot password" → enters email
2. Reset link sent (expires in 1 hour)
3. User sets new password → redirected to login
