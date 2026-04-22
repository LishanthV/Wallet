import os
import secrets
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from datetime             import datetime, date, timedelta
from functools            import wraps

from flask import (Flask, render_template, request, redirect,
                   url_for, jsonify, flash, session)
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error
import calendar

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "finance_super_secret_2025")

# ── Database config ────────────────────────────
DB_CONFIG = {
    "host":     os.environ.get("DB_HOST",     "localhost"),
    "user":     os.environ.get("DB_USER",     "root"),
    "password": os.environ.get("DB_PASSWORD", "your_password"),
    "database": os.environ.get("DB_NAME",     "finance_db"),
}

# ── Email / SMTP config ────────────────────────
SMTP_CONFIG = {
    "host":     os.environ.get("SMTP_HOST",     "smtp.gmail.com"),
    "port":     int(os.environ.get("SMTP_PORT", "587")),
    "user":     os.environ.get("SMTP_USER",     "your_gmail@gmail.com"),
    "password": os.environ.get("SMTP_PASSWORD", "your_app_password"),
    "from":     os.environ.get("SMTP_FROM",     "Finance App <your_gmail@gmail.com>"),
}

APP_URL = os.environ.get("APP_URL", "http://127.0.0.1:5000")

CATEGORIES = [
    "Food", "Rent", "Transport", "Shopping",
    "Bills", "Entertainment", "Health", "Others"
]

CAT_ICONS = {
    "Food": "🛒", "Rent": "🏠", "Transport": "🚗",
    "Shopping": "🛍️", "Bills": "🌐", "Entertainment": "🎬",
    "Health": "💊", "Others": "💳"
}


# ─────────────────────────────────────────────
#  DB helper
# ─────────────────────────────────────────────
def get_db():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        print(f"[DB Error] {e}")
        return None


# ─────────────────────────────────────────────
#  Auth decorator
# ─────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
#  Email helpers
# ─────────────────────────────────────────────
def send_email(to_addr, subject, html_body):
    """
    Send HTML email via SMTP.
    Tries STARTTLS on port 587 first, then falls back to SSL on port 465.
    All errors are printed so you can see exactly what went wrong.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SMTP_CONFIG["from"]
    msg["To"]      = to_addr
    msg.attach(MIMEText(html_body, "html"))

    # ── Attempt 1: STARTTLS on port 587 ──
    try:
        print(f"[Email] Connecting to {SMTP_CONFIG['host']}:587 (STARTTLS)...")
        with smtplib.SMTP(SMTP_CONFIG["host"], 587, timeout=15) as s:
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(SMTP_CONFIG["user"], SMTP_CONFIG["password"])
            s.sendmail(SMTP_CONFIG["user"], to_addr, msg.as_string())
        print(f"[Email] Sent to {to_addr} via STARTTLS")
        return True
    except Exception as e1:
        print(f"[Email] STARTTLS failed: {e1}")

    # ── Attempt 2: SSL on port 465 ──
    try:
        print(f"[Email] Retrying {SMTP_CONFIG['host']}:465 (SSL)...")
        import ssl
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_CONFIG["host"], 465, context=ctx, timeout=15) as s:
            s.login(SMTP_CONFIG["user"], SMTP_CONFIG["password"])
            s.sendmail(SMTP_CONFIG["user"], to_addr, msg.as_string())
        print(f"[Email] Sent to {to_addr} via SSL")
        return True
    except Exception as e2:
        print(f"[Email] SSL failed: {e2}")

    print("[Email] Both attempts failed. Check SMTP credentials and App Password.")
    return False


def create_token(user_id, token_type="verify", hours=24):
    token  = secrets.token_urlsafe(32)
    expiry = datetime.utcnow() + timedelta(hours=hours)
    conn   = get_db()
    cur    = conn.cursor()
    cur.execute("""
        UPDATE email_tokens SET used=1
        WHERE user_id=%s AND token_type=%s AND used=0
    """, (user_id, token_type))
    cur.execute("""
        INSERT INTO email_tokens (user_id, token, token_type, expires_at)
        VALUES (%s, %s, %s, %s)
    """, (user_id, token, token_type, expiry))
    conn.commit()
    cur.close(); conn.close()
    return token


def send_verification_email(email, name, token):
    link = f"{APP_URL}/verify-email/{token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px;background:#f5f4f8;border-radius:16px">
      <div style="background:#7F77DD;border-radius:12px;padding:24px;text-align:center;margin-bottom:24px">
        <h2 style="color:#fff;margin:0;font-size:22px">Finance Dashboard</h2>
      </div>
      <h3 style="color:#1a1a2e">Hi {name},</h3>
      <p style="color:#6b6a75;line-height:1.7">
        Thanks for signing up! Please verify your email to activate your account.
        This link expires in <strong>24 hours</strong>.
      </p>
      <div style="text-align:center;margin:28px 0">
        <a href="{link}" style="background:#7F77DD;color:#fff;padding:13px 36px;
           border-radius:8px;text-decoration:none;font-weight:600;font-size:15px">
          Verify Email
        </a>
      </div>
      <p style="color:#9f9ea8;font-size:12px;text-align:center">
        Or copy: <a href="{link}" style="color:#7F77DD">{link}</a>
      </p>
      <p style="color:#c0bfc8;font-size:11px;text-align:center;margin-top:16px">
        If you didn't create this account, you can safely ignore this email.
      </p>
    </div>"""
    return send_email(email, "Verify your Finance Dashboard account", html)


def send_reset_email(email, name, token):
    link = f"{APP_URL}/reset-password/{token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px;background:#f5f4f8;border-radius:16px">
      <div style="background:#534AB7;border-radius:12px;padding:24px;text-align:center;margin-bottom:24px">
        <h2 style="color:#fff;margin:0;font-size:22px">Finance Dashboard</h2>
      </div>
      <h3 style="color:#1a1a2e">Hi {name},</h3>
      <p style="color:#6b6a75;line-height:1.7">
        We received a request to reset your password. This link expires in <strong>1 hour</strong>.
      </p>
      <div style="text-align:center;margin:28px 0">
        <a href="{link}" style="background:#534AB7;color:#fff;padding:13px 36px;
           border-radius:8px;text-decoration:none;font-weight:600;font-size:15px">
          Reset Password
        </a>
      </div>
      <p style="color:#9f9ea8;font-size:12px;text-align:center">
        If you didn't request this, ignore this email — your password won't change.
      </p>
    </div>"""
    return send_email(email, "Reset your Finance Dashboard password", html)


# ─────────────────────────────────────────────
#  AUTH ROUTES
# ─────────────────────────────────────────────

@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name    = request.form["name"].strip()
        email   = request.form["email"].strip().lower()
        pw      = request.form["password"]
        confirm = request.form["confirm_password"]

        if len(name) < 2:
            flash("Name must be at least 2 characters.", "danger")
            return render_template("register.html")
        if len(pw) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return render_template("register.html")
        if pw != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM users WHERE email=%s", (email,))
        if cur.fetchone():
            flash("An account with that email already exists.", "danger")
            cur.close(); conn.close()
            return render_template("register.html")

        cur.execute("""
            INSERT INTO users (name, email, password_hash) VALUES (%s,%s,%s)
        """, (name, email, generate_password_hash(pw)))
        conn.commit()
        user_id = cur.lastrowid
        cur.close(); conn.close()

        token = create_token(user_id, "verify", hours=24)
        sent  = send_verification_email(email, name, token)
        if sent:
            flash("Account created! Check your email to verify your account.", "success")
        else:
            flash("Account created but email delivery failed. Use Resend Verification.", "warning")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        pw    = request.form["password"]

        conn = get_db()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close(); conn.close()

        if not user or not check_password_hash(user["password_hash"], pw):
            flash("Invalid email or password.", "danger")
            return render_template("login.html")

        if not user["is_verified"]:
            flash("Please verify your email before logging in.", "warning")
            return render_template("login.html", unverified=True, unverified_email=email)

        session["user_id"]    = user["id"]
        session["user_name"]  = user["name"]
        session["user_email"] = user["email"]
        flash(f"Welcome back, {user['name']}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You've been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/verify-email/<token>")
def verify_email(token):
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT * FROM email_tokens
        WHERE token=%s AND token_type='verify' AND used=0
    """, (token,))
    rec = cur.fetchone()

    if not rec:
        flash("Invalid or already-used verification link.", "danger")
        cur.close(); conn.close()
        return redirect(url_for("login"))
    if datetime.utcnow() > rec["expires_at"]:
        flash("Verification link expired. Request a new one below.", "warning")
        cur.close(); conn.close()
        return redirect(url_for("login"))

    cur.execute("UPDATE users SET is_verified=1 WHERE id=%s", (rec["user_id"],))
    cur.execute("UPDATE email_tokens SET used=1 WHERE id=%s", (rec["id"],))
    conn.commit()
    cur.close(); conn.close()

    flash("Email verified! You can now log in.", "success")
    return redirect(url_for("login"))


@app.route("/resend-verification", methods=["POST"])
def resend_verification():
    email = request.form.get("email", "").strip().lower()
    conn  = get_db()
    cur   = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE email=%s AND is_verified=0", (email,))
    user  = cur.fetchone()
    cur.close(); conn.close()
    if user:
        token = create_token(user["id"], "verify", hours=24)
        send_verification_email(email, user["name"], token)
    flash("If that email is registered and unverified, a new link has been sent.", "info")
    return redirect(url_for("login"))


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        conn  = get_db()
        cur   = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email=%s AND is_verified=1", (email,))
        user  = cur.fetchone()
        cur.close(); conn.close()
        if user:
            token = create_token(user["id"], "reset", hours=1)
            send_reset_email(email, user["name"], token)
        flash("If that email is registered, you'll receive a reset link shortly.", "info")
        return redirect(url_for("login"))
    return render_template("forgot_password.html")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT * FROM email_tokens
        WHERE token=%s AND token_type='reset' AND used=0
    """, (token,))
    rec = cur.fetchone()

    if not rec or datetime.utcnow() > rec["expires_at"]:
        flash("Invalid or expired reset link.", "danger")
        cur.close(); conn.close()
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        pw      = request.form["password"]
        confirm = request.form["confirm_password"]
        if len(pw) < 8:
            flash("Password must be at least 8 characters.", "danger")
            cur.close(); conn.close()
            return render_template("reset_password.html", token=token)
        if pw != confirm:
            flash("Passwords do not match.", "danger")
            cur.close(); conn.close()
            return render_template("reset_password.html", token=token)

        cur.execute("UPDATE users SET password_hash=%s WHERE id=%s",
                    (generate_password_hash(pw), rec["user_id"]))
        cur.execute("UPDATE email_tokens SET used=1 WHERE id=%s", (rec["id"],))
        conn.commit()
        cur.close(); conn.close()
        flash("Password reset! Please log in.", "success")
        return redirect(url_for("login"))

    cur.close(); conn.close()
    return render_template("reset_password.html", token=token)


# ─────────────────────────────────────────────
#  DASHBOARD
# ─────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    user_id     = session["user_id"]
    conn        = get_db()
    cur         = conn.cursor(dictionary=True)
    today       = date.today()
    month, year = today.month, today.year

    cur.execute("""
        SELECT COALESCE(SUM(amount),0) AS total FROM expenses
        WHERE user_id=%s AND MONTH(expense_date)=%s AND YEAR(expense_date)=%s
    """, (user_id, month, year))
    total = float(cur.fetchone()["total"])

    cur.execute("""
        SELECT COALESCE(AVG(ds),0) AS avg_d FROM (
            SELECT SUM(amount) AS ds FROM expenses
            WHERE user_id=%s AND MONTH(expense_date)=%s AND YEAR(expense_date)=%s
            GROUP BY expense_date
        ) x
    """, (user_id, month, year))
    avg_daily = round(float(cur.fetchone()["avg_d"]), 2)

    cur.execute("""
        SELECT expense_date, COALESCE(SUM(amount),0) AS dt FROM expenses
        WHERE user_id=%s AND MONTH(expense_date)=%s AND YEAR(expense_date)=%s
        GROUP BY expense_date ORDER BY dt DESC LIMIT 1
    """, (user_id, month, year))
    peak       = cur.fetchone()
    peak_day   = str(peak["expense_date"]) if peak else "—"
    peak_total = float(peak["dt"]) if peak else 0

    days_in_month = calendar.monthrange(year, month)[1]
    cur.execute("""
        SELECT DAY(expense_date) AS day, SUM(amount) AS total FROM expenses
        WHERE user_id=%s AND MONTH(expense_date)=%s AND YEAR(expense_date)=%s
        GROUP BY DAY(expense_date) ORDER BY day
    """, (user_id, month, year))
    daily_map    = {r["day"]: float(r["total"]) for r in cur.fetchall()}
    daily_labels = list(range(1, days_in_month + 1))
    daily_data   = [daily_map.get(d, 0) for d in daily_labels]

    cur.execute("""
        SELECT category, COALESCE(SUM(amount),0) AS total FROM expenses
        WHERE user_id=%s AND MONTH(expense_date)=%s AND YEAR(expense_date)=%s
        GROUP BY category ORDER BY total DESC
    """, (user_id, month, year))
    cat_rows   = cur.fetchall()
    cat_labels = [r["category"] for r in cat_rows]
    cat_data   = [float(r["total"]) for r in cat_rows]

    cur.execute("""
        SELECT id, title, category, amount, expense_date, note FROM expenses
        WHERE user_id=%s ORDER BY expense_date DESC, id DESC LIMIT 5
    """, (user_id,))
    recent = cur.fetchall()
    cur.close(); conn.close()

    return render_template("dashboard.html",
        total=total, avg_daily=avg_daily,
        peak_day=peak_day, peak_total=peak_total,
        daily_labels=daily_labels, daily_data=daily_data,
        cat_labels=cat_labels, cat_data=cat_data,
        recent=recent, cat_icons=CAT_ICONS,
        month_name=today.strftime("%B %Y")
    )


# ─────────────────────────────────────────────
#  EXPENSES CRUD
# ─────────────────────────────────────────────

@app.route("/expenses")
@login_required
def expenses():
    user_id = session["user_id"]
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM expenses WHERE user_id=%s ORDER BY expense_date DESC, id DESC",
                (user_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return render_template("expenses.html", expenses=rows,
                           categories=CATEGORIES, cat_icons=CAT_ICONS)


@app.route("/add", methods=["GET", "POST"])
@login_required
def add_expense():
    if request.method == "POST":
        user_id  = session["user_id"]
        title    = request.form["title"].strip()
        amount   = float(request.form["amount"])
        category = request.form["category"]
        exp_date = request.form["expense_date"]
        note     = request.form.get("note", "").strip()
        conn = get_db(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO expenses (user_id, title, amount, category, expense_date, note)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (user_id, title, amount, category, exp_date, note))
        conn.commit(); cur.close(); conn.close()
        flash("Expense added!", "success")
        return redirect(url_for("expenses"))
    return render_template("add_expense.html",
                           categories=CATEGORIES, today=date.today().isoformat())


@app.route("/edit/<int:expense_id>", methods=["GET", "POST"])
@login_required
def edit_expense(expense_id):
    user_id = session["user_id"]
    conn = get_db(); cur = conn.cursor(dictionary=True)
    if request.method == "POST":
        cur.execute("""
            UPDATE expenses SET title=%s, amount=%s, category=%s,
                                expense_date=%s, note=%s
            WHERE id=%s AND user_id=%s
        """, (request.form["title"].strip(), float(request.form["amount"]),
              request.form["category"], request.form["expense_date"],
              request.form.get("note","").strip(), expense_id, user_id))
        conn.commit(); cur.close(); conn.close()
        flash("Expense updated!", "success")
        return redirect(url_for("expenses"))

    cur.execute("SELECT * FROM expenses WHERE id=%s AND user_id=%s", (expense_id, user_id))
    expense = cur.fetchone()
    cur.close(); conn.close()
    if not expense:
        flash("Expense not found.", "danger")
        return redirect(url_for("expenses"))
    return render_template("add_expense.html", expense=expense,
                           categories=CATEGORIES, today=date.today().isoformat())


@app.route("/delete/<int:expense_id>", methods=["POST"])
@login_required
def delete_expense(expense_id):
    user_id = session["user_id"]
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE id=%s AND user_id=%s", (expense_id, user_id))
    conn.commit(); cur.close(); conn.close()
    flash("Expense deleted.", "info")
    return redirect(url_for("expenses"))


@app.route("/api/daily")
@login_required
def api_daily():
    user_id     = session["user_id"]
    days        = int(request.args.get("days", 30))
    today       = date.today()
    month, year = today.month, today.year
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT DAY(expense_date) AS day, SUM(amount) AS total FROM expenses
        WHERE user_id=%s AND MONTH(expense_date)=%s
          AND YEAR(expense_date)=%s AND DAY(expense_date)<=%s
        GROUP BY DAY(expense_date) ORDER BY day
    """, (user_id, month, year, days))
    rows      = cur.fetchall()
    cur.close(); conn.close()
    daily_map = {r["day"]: float(r["total"]) for r in rows}
    labels    = list(range(1, days + 1))
    return jsonify({"labels": labels, "data": [daily_map.get(d, 0) for d in labels]})


if __name__ == "__main__":
    app.run(debug=True)


# ─────────────────────────────────────────────
#  Email test route (debug only)
#  Visit: http://127.0.0.1:5000/test-email?to=your@email.com
# ─────────────────────────────────────────────
@app.route("/test-email")
def test_email():
    to = request.args.get("to", "")
    if not to:
        return "Usage: /test-email?to=your@email.com", 400
    ok = send_email(
        to,
        "Finance App — Test Email",
        "<h2>It works!</h2><p>Your SMTP config is set up correctly.</p>"
    )
    if ok:
        return f"<h3 style='color:green'>Email sent to {to}!</h3><p>Check your inbox (and spam).</p>"
    return ("<h3 style='color:red'>Email failed.</h3>"
            "<p>Check your terminal for the exact error message.</p>"
            "<p>Most likely cause: wrong App Password or 2FA not enabled on Gmail.</p>"), 500
