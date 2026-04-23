import os, secrets, smtplib, csv, io, calendar, json, re, uuid
from urllib.request import urlopen, Request
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from datetime             import datetime, date, timedelta
from functools            import wraps

from flask import (Flask, render_template, request, redirect,
                   url_for, jsonify, flash, session, Response)
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error, pooling
import io
import csv
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "finance_super_secret_2025")

# ── Upload config ─────────────────────────────
UPLOAD_FOLDER = 'static/uploads/profiles'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
BILL_UPLOAD_FOLDER = 'static/uploads/bills'
BILL_ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['BILL_UPLOAD_FOLDER'] = BILL_UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_bill_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in BILL_ALLOWED_EXTENSIONS

DB_CONFIG = {
    "host":     os.environ.get("DB_HOST",     "localhost"),
    "user":     os.environ.get("DB_USER",     "root"),
    "password": os.environ.get("DB_PASSWORD", "Li$h@nth2005"),
    "database": os.environ.get("DB_NAME",     "finance_db"),
}
SMTP_CONFIG = {
    "host":     os.environ.get("SMTP_HOST",     "smtp.gmail.com"),
    "port":     int(os.environ.get("SMTP_PORT", "587")),
    "user":     os.environ.get("SMTP_USER",     "your_gmail@gmail.com"),
    "password": os.environ.get("SMTP_PASSWORD", "your_app_password"),
    "from":     os.environ.get("SMTP_FROM",     "Finance App <your_gmail@gmail.com>"),
}

# ── Database Pooling ──────────────────────────
try:
    db_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="nexwallet_pool",
        pool_size=10,
        **DB_CONFIG
    )
except Error as e:
    print(f"❌ Could not initialize DB pool: {e}")
    db_pool = None

# ── Auto Database Migration ────────────────────
def ensure_db_schema():
    if not db_pool: return
    try:
        conn = db_pool.get_connection()
        cur = conn.cursor()
        cur.execute("SHOW COLUMNS FROM users LIKE 'dob'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE users ADD COLUMN dob DATE DEFAULT NULL, ADD COLUMN mobile VARCHAR(20) DEFAULT NULL, ADD COLUMN is_mobile_verified BOOLEAN DEFAULT FALSE")
            print("🚀 Database schema updated: Added dob, mobile, and is_mobile_verified columns.")
        conn.commit()
        cur.close()
        conn.close()
    except Error as e:
        print(f"❌ Migration error: {e}")

ensure_db_schema()

APP_URL     = os.environ.get("APP_URL", "http://127.0.0.1:5000")
CATEGORIES  = ["Food","Rent","Transport","Shopping","Bills","Entertainment","Health","Others"]
INCOME_CATS = ["Salary","Freelance","Business","Investment","Gift","Other"]
CAT_ICONS   = {"Food":"🛒","Rent":"🏠","Transport":"🚗","Shopping":"🛍️",
               "Bills":"🌐","Entertainment":"🎬","Health":"💊","Others":"💳"}
CAT_COLORS  = ["#7F77DD","#AFA9EC","#CECBF6","#534AB7","#888780","#D3D1C7","#3C3489","#B4B2A9"]
GOAL_ICONS  = ["🎯","🏖️","🚗","🏠","💻","✈️","🎓","💍","📱","💰"]
CURRENCY_CODES = {
    "USD","EUR","GBP","JPY","CNY","INR","CAD","MXN","JMD","DOP","TTD","BRL","ARS","CLP","COP","PEN","UYU",
    "CHF","SEK","NOK","DKK","PLN","CZK","HUF","RON","BGN","TRY","UAH","AED","SAR","QAR","KWD","BHD","OMR",
    "JOD","ILS","PKR","BDT","NPR","LKR","THB","SGD","MYR","IDR","PHP","VND","KRW","HKD","TWD","ZAR","EGP",
    "NGN","KES","GHS","MAD","TND","AUD","NZD","FJD","PGK"
}
CURRENCY_SYMBOLS = {
    "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CNY": "¥", "INR": "₹", "CAD": "$", "MXN": "$",
    "JMD": "$", "DOP": "RD$", "TTD": "TT$", "BRL": "R$", "ARS": "$", "CLP": "$", "COP": "$", "PEN": "S/",
    "UYU": "$", "CHF": "CHF", "SEK": "kr", "NOK": "kr", "DKK": "kr", "PLN": "zł", "CZK": "Kc", "HUF": "Ft",
    "RON": "lei", "BGN": "лв", "TRY": "₺", "UAH": "₴", "AED": "د.إ", "SAR": "﷼", "QAR": "﷼", "KWD": "د.ك",
    "BHD": ".د.ب", "OMR": "﷼", "JOD": "د.ا", "ILS": "₪", "PKR": "₨", "BDT": "৳", "NPR": "रू", "LKR": "Rs",
    "THB": "฿", "SGD": "$", "MYR": "RM", "IDR": "Rp", "PHP": "₱", "VND": "₫", "KRW": "₩", "HKD": "$",
    "TWD": "NT$", "ZAR": "R", "EGP": "E£", "NGN": "₦", "KES": "KSh", "GHS": "GH¢", "MAD": "د.م.",
    "TND": "د.ت", "AUD": "$", "NZD": "$", "FJD": "$", "PGK": "K"
}
USD_BASE_RATES = {
    "USD": 1.0, "EUR": 0.92, "GBP": 0.79, "JPY": 155.0, "CNY": 7.24, "INR": 83.5, "CAD": 1.36, "MXN": 16.9,
    "JMD": 156.0, "DOP": 59.0, "TTD": 6.78, "BRL": 5.1, "ARS": 870.0, "CLP": 920.0, "COP": 3900.0, "PEN": 3.7,
    "UYU": 39.0, "CHF": 0.90, "SEK": 10.6, "NOK": 10.8, "DKK": 6.86, "PLN": 3.95, "CZK": 23.2, "HUF": 360.0,
    "RON": 4.58, "BGN": 1.8, "TRY": 32.0, "UAH": 39.0, "AED": 3.67, "SAR": 3.75, "QAR": 3.64, "KWD": 0.31,
    "BHD": 0.38, "OMR": 0.38, "JOD": 0.71, "ILS": 3.65, "PKR": 278.0, "BDT": 117.0, "NPR": 133.0, "LKR": 300.0,
    "THB": 36.3, "SGD": 1.35, "MYR": 4.75, "IDR": 16000.0, "PHP": 57.0, "VND": 25500.0, "KRW": 1370.0, "HKD": 7.82,
    "TWD": 32.2, "ZAR": 18.5, "EGP": 48.0, "NGN": 1450.0, "KES": 129.0, "GHS": 14.0, "MAD": 10.0, "TND": 3.1,
    "AUD": 1.52, "NZD": 1.65, "FJD": 2.25, "PGK": 3.85
}

@app.context_processor
def inject_currency_symbol():
    code = (session.get("currency_code") or "USD").upper()
    return {
        "currency_code": code,
        "currency_symbol": CURRENCY_SYMBOLS.get(code, "$"),
    }


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────
def get_db():
    """Retrieve a connection from the pool."""
    if not db_pool:
        # Fallback to direct connection if pool failed
        return mysql.connector.connect(**DB_CONFIG)
    try:
        return db_pool.get_connection()
    except Error as e:
        print(f"⚠️ Pool exhausted or DB error: {e}")
        return mysql.connector.connect(**DB_CONFIG)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def apply_recurring(user_id):
    today = date.today()
    conn  = get_db(); cur = conn.cursor(dictionary=True)
    first_day = today.replace(day=1)
    cur.execute("""
        SELECT * FROM recurring_expenses
        WHERE user_id=%s AND is_active=1 AND day_of_month<=%s
          AND (last_applied IS NULL OR last_applied < %s)
    """, (user_id, today.day, first_day))
    due = cur.fetchall()
    for r in due:
        cur.execute("""INSERT INTO expenses (user_id,title,amount,category,expense_date,note)
            VALUES(%s,%s,%s,%s,%s,%s)""",
            (user_id, r["title"], r["amount"], r["category"],
             date(today.year, today.month, r["day_of_month"]),
             f"[Auto] {r['note'] or ''}"))
        cur.execute("UPDATE recurring_expenses SET last_applied=%s WHERE id=%s",(today,r["id"]))
    conn.commit(); cur.close(); conn.close()
    return len(due)

def infer_category_from_title(item_title):
    text = item_title.lower()
    keyword_map = {
        "Food": ["rice", "milk", "bread", "snack", "pizza", "burger", "coffee", "tea", "grocery", "fruit", "veg"],
        "Transport": ["petrol", "diesel", "uber", "ola", "taxi", "bus", "metro", "train", "fuel", "parking"],
        "Shopping": ["shirt", "jeans", "dress", "amazon", "flipkart", "mall", "shoe", "bag", "watch"],
        "Bills": ["electric", "water", "internet", "wifi", "bill", "recharge", "mobile", "gas", "subscription"],
        "Health": ["pharmacy", "medicine", "hospital", "clinic", "doctor", "tablet", "med"],
        "Entertainment": ["movie", "netflix", "spotify", "game", "ticket", "cinema", "concert"],
        "Rent": ["rent", "lease", "hostel", "apartment"],
    }
    for category, words in keyword_map.items():
        if any(word in text for word in words):
            return category
    return "Others"

def parse_bill_items(bill_text):
    items = []
    # Enhanced skip words for Indian context (GST, taxes, noisy receipt footers)
    skip_words = {
        "total", "subtotal", "sub total", "grand total", "tax", "cgst", "sgst", "igst", "gst",
        "round off", "change", "cash", "card", "paid", "balance", "discount", "upi", "invoice",
        "bill no", "receipt", "thank you", "txn", "transaction", "amount", "price", "qty",
        "hsn", "sac", "vat", "service tax", "cess", "net amt", "payable"
    }
    
    lines = [line.strip() for line in bill_text.splitlines() if line.strip()]
    for line in lines:
        normalized = re.sub(r"\s+", " ", line)
        lower_line = normalized.lower()
        if any(word in lower_line for word in skip_words):
            continue

        # Pattern 1: "Item Name 2 x 50.00 100.00"
        match = re.search(r"^(.*?)(?:\b\d+(?:\.\d+)?\s*[xX]\s*\d+(?:\.\d+)?\b).*?(\d+(?:\.\d{1,2})?)\s*$", normalized)
        # Pattern 2: "Item Name .... 100.00"
        if not match:
            match = re.search(r"^(.*?)(\d+(?:\.\d{1,2})?)\s*$", normalized)
        if not match:
            continue

        title = match.group(1)
        title = re.sub(r"[^A-Za-z0-9\s\-/&()]", " ", title)
        title = re.sub(r"\s+", " ", title).strip(" .:-")
        try:
            amount = float(match.group(2))
        except ValueError:
            continue
        if not title or amount <= 0 or amount > 100000:
            continue
        if len(title) < 2:
            continue
        items.append({
            "title": title[:150],
            "amount": round(amount, 2),
            "category": infer_category_from_title(title),
        })
    # Deduplicate near-identical repeated OCR lines.
    deduped = []
    seen = set()
    for item in items:
        key = (item["title"].lower(), item["amount"])
        if key not in seen:
            deduped.append(item)
            seen.add(key)
    return deduped

def extract_text_from_bill_image(image_path):
    try:
        from PIL import Image
        import pytesseract
    except Exception:
        return None, "OCR dependencies missing. Install with: pip install pillow pytesseract"
    try:
        img = Image.open(image_path)
        # Improve OCR readability for receipts.
        img = img.convert("L")
        text = pytesseract.image_to_string(img, config="--oem 3 --psm 6")
        if not text or not text.strip():
            return None, "Could not read text from this bill image."
        return text, None
    except Exception as e:
        return None, f"OCR failed: {e}"

def fetch_conversion_rate(from_code, to_code):
    """Fetch FX rate for converting from_code -> to_code.
    Tries live APIs first, then falls back to bundled approximate rates.
    """
    if from_code == to_code:
        return 1.0

    def read_json(url):
        req = Request(url, headers={"User-Agent": "FinanceApp/1.0"})
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # Live source 1: Frankfurter API
    try:
        data = read_json(f"https://api.frankfurter.app/latest?amount=1&from={from_code}&to={to_code}")
        rate = (data.get("rates") or {}).get(to_code)
        if rate:
            return float(rate)
    except Exception as e:
        print(f"[FX] Frankfurter failed {from_code}->{to_code}: {e}")

    # Live source 2: exchangerate.host
    try:
        data = read_json(f"https://api.exchangerate.host/convert?from={from_code}&to={to_code}&amount=1")
        result = data.get("result")
        if result:
            return float(result)
    except Exception as e:
        print(f"[FX] exchangerate.host failed {from_code}->{to_code}: {e}")

    # Offline fallback using bundled USD base rates
    from_rate = USD_BASE_RATES.get(from_code)
    to_rate = USD_BASE_RATES.get(to_code)
    if from_rate and to_rate and from_rate > 0:
        return float(to_rate) / float(from_rate)

    return None


# ─────────────────────────────────────────────
#  Email
# ─────────────────────────────────────────────
def send_email(to_addr, subject, html_body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject; msg["From"] = SMTP_CONFIG["from"]; msg["To"] = to_addr
    msg.attach(MIMEText(html_body, "html"))
    try:
        with smtplib.SMTP(SMTP_CONFIG["host"], 587, timeout=15) as s:
            s.ehlo(); s.starttls(); s.ehlo()
            s.login(SMTP_CONFIG["user"], SMTP_CONFIG["password"])
            s.sendmail(SMTP_CONFIG["user"], to_addr, msg.as_string())
        return True
    except Exception as e1:
        print(f"[Email] STARTTLS failed: {e1}")
    try:
        import ssl; ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_CONFIG["host"], 465, context=ctx, timeout=15) as s:
            s.login(SMTP_CONFIG["user"], SMTP_CONFIG["password"])
            s.sendmail(SMTP_CONFIG["user"], to_addr, msg.as_string())
        return True
    except Exception as e2:
        print(f"[Email] SSL failed: {e2}")
    return False

def create_token(user_id, token_type="verify", hours=24):
    token  = secrets.token_urlsafe(32)
    expiry = datetime.utcnow() + timedelta(hours=hours)
    conn   = get_db(); cur = conn.cursor()
    cur.execute("UPDATE email_tokens SET used=1 WHERE user_id=%s AND token_type=%s AND used=0",
                (user_id, token_type))
    cur.execute("INSERT INTO email_tokens (user_id,token,token_type,expires_at) VALUES(%s,%s,%s,%s)",
                (user_id, token, token_type, expiry))
    conn.commit(); cur.close(); conn.close(); return token

def send_otp_email(email, name, otp):
    html = f"""<div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px;background:#f8fafc;border-radius:20px;border:1px solid #e2e8f0">
      <div style="background:#27ae60;border-radius:12px;padding:24px;text-align:center;margin-bottom:24px">
        <h2 style="color:#fff;margin:0;font-family:Arial">Trackify</h2></div>
      <h3 style="color:#0a3d62">Hi {name},</h3>
      <p style="color:#64748b;line-height:1.7">Your verification code for Trackify is:</p>
      <div style="text-align:center;margin:32px 0;background:#f1f5f9;padding:24px;border-radius:12px">
        <span style="font-size:42px;font-weight:800;letter-spacing:10px;color:#0a3d62">{otp}</span>
      </div>
      <p style="color:#94a3b8;font-size:13px;text-align:center">This code expires in 15 minutes. If you didn't request this, please ignore this email.</p></div>"""
    
    print(f"\n" + "="*50)
    print(f"🚀 DEVELOPMENT OTP FOR {email}: {otp}")
    print("="*50 + "\n")
    
    # Try to send email, but don't worry if it fails in dev
    send_email(email, f"{otp} is your Trackify verification code", html)
    return True


def send_reset_email(email, name, token):
    link = f"{APP_URL}/reset-password/{token}"
    html = f"""<div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px;background:#f5f4f8;border-radius:16px">
      <div style="background:#534AB7;border-radius:12px;padding:24px;text-align:center;margin-bottom:24px">
        <h2 style="color:#fff;margin:0">Finance Dashboard</h2></div>
      <h3 style="color:#1a1a2e">Hi {name},</h3>
      <p style="color:#6b6a75;line-height:1.7">Password reset link — expires in <strong>1 hour</strong>.</p>
      <div style="text-align:center;margin:28px 0">
        <a href="{link}" style="background:#534AB7;color:#fff;padding:13px 36px;border-radius:8px;text-decoration:none;font-weight:600">Reset Password</a></div></div>"""
    return send_email(email, "Reset your Finance Dashboard password", html)


# ─────────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────────
@app.route("/register", methods=["GET","POST"])
def register():
    if "user_id" in session: return redirect(url_for("dashboard"))
    if request.method == "POST":
        name=request.form["name"].strip(); email=request.form["email"].strip().lower()
        pw=request.form["password"]
        if len(name)<2:  flash("Name too short.","danger");        return render_template("register.html")
        if len(pw)<8:    flash("Password min 8 chars.","danger");  return render_template("register.html")
        
        conn=get_db(); cur=conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM users WHERE email=%s",(email,))
        if cur.fetchone():
            flash("Email already registered.","danger"); cur.close(); conn.close()
            return render_template("register.html")
        cur.close(); conn.close()

        # Generate OTP
        otp = "".join([str(secrets.randbelow(10)) for _ in range(6)])
        session["pending_user"] = {
            "name": name, "email": email, "pw_hash": generate_password_hash(pw), "otp": otp,
            "expires": (datetime.utcnow() + timedelta(minutes=15)).timestamp()
        }
        
        sent = send_otp_email(email, name, otp)
        if sent:
            flash(f"For testing, your OTP is: {otp} (Check your email or terminal)", "success")
            return redirect(url_for("verify_otp"))
        else:
            flash(f"Failed to send email. For testing, your OTP is: {otp}", "warning")
            return redirect(url_for("verify_otp"))
    return render_template("register.html")

@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    pending = session.get("pending_user")
    if not pending: return redirect(url_for("register"))

    if request.method == "POST":
        # Combine OTP inputs
        entered_otp = "".join([request.form.get(f"otp_{i}","") for i in range(1,7)])
        
        if datetime.utcnow().timestamp() > pending["expires"]:
            flash("OTP expired. Please register again.", "danger")
            session.pop("pending_user", None); return redirect(url_for("register"))
        
        if entered_otp == pending["otp"]:
            # OTP match - create user
            conn=get_db(); cur=conn.cursor()
            cur.execute("INSERT INTO users (name,email,password_hash,is_verified) VALUES(%s,%s,%s,1)",
                        (pending["name"], pending["email"], pending["pw_hash"]))
            conn.commit(); cur.close(); conn.close()
            session.pop("pending_user", None)
            flash("Account verified! You can now log in.", "success")
            return redirect(url_for("login"))
        else:
            flash("Invalid OTP. Please try again.", "danger")

    return render_template("verify_otp.html", email=pending["email"])

@app.route("/resend-otp")
def resend_otp():
    pending = session.get("pending_user")
    if not pending: return redirect(url_for("register"))
    
    otp = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    pending["otp"] = otp
    pending["expires"] = (datetime.utcnow() + timedelta(minutes=15)).timestamp()
    session["pending_user"] = pending
    
    send_otp_email(pending["email"], pending["name"], otp)
    flash(f"A new code has been sent. For testing, your OTP is: {otp}", "info")
    return redirect(url_for("verify_otp"))

@app.route("/login", methods=["GET","POST"])
def login():
    if "user_id" in session: return redirect(url_for("dashboard"))
    if request.method == "POST":
        email=request.form["email"].strip().lower(); pw=request.form["password"]
        conn=get_db()
        if not conn:
            flash("Database connection failed. Check your MySQL server or credentials in app.py.", "danger")
            return render_template("login.html")
        cur=conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email=%s",(email,))
        user=cur.fetchone(); cur.close(); conn.close()
        if not user or not check_password_hash(user["password_hash"],pw):
            flash("Invalid email or password.","danger"); return render_template("login.html")
        if not user["is_verified"]:
            flash("Please verify your email first.","warning")
            return render_template("login.html",unverified=True,unverified_email=email)
        session.update({
            "user_id": user["id"],
            "user_name": user["name"],
            "user_email": user["email"],
            "profile_pic": user["profile_pic"],
            "currency_code": user.get("currency_code", "USD"),
        })
        n=apply_recurring(user["id"])
        if n: flash(f"{n} recurring expense(s) auto-applied for this month.","info")
        flash(f"Welcome back, {user['name']}!","success")
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear(); flash("Logged out.","info"); return redirect(url_for("login"))

@app.route("/verify-email/<path:token>")
def verify_email(token):
    token=token.strip(); conn=get_db(); cur=conn.cursor(dictionary=True)
    cur.execute("""SELECT et.*,u.is_verified AS already_verified FROM email_tokens et
        JOIN users u ON u.id=et.user_id WHERE et.token=%s AND et.token_type='verify'""",(token,))
    rec=cur.fetchone()
    if not rec: cur.close(); conn.close(); flash("Invalid verification link.","danger"); return redirect(url_for("login"))
    if rec["used"] or rec["already_verified"]: cur.close(); conn.close(); flash("Already verified. Please log in.","info"); return redirect(url_for("login"))
    expires=rec["expires_at"]
    now=(datetime.now(__import__("datetime").timezone.utc) if hasattr(expires,"tzinfo") and expires.tzinfo else datetime.utcnow())
    if now>expires: cur.close(); conn.close(); flash("Link expired. Request a new one.","warning"); return redirect(url_for("login"))
    cur.execute("UPDATE users SET is_verified=1 WHERE id=%s",(rec["user_id"],))
    cur.execute("UPDATE email_tokens SET used=1 WHERE id=%s",(rec["id"],))
    conn.commit(); cur.close(); conn.close()
    flash("Email verified! You can now log in.","success"); return redirect(url_for("login"))

@app.route("/resend-verification", methods=["POST"])
def resend_verification():
    email=request.form.get("email","").strip().lower(); conn=get_db(); cur=conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE email=%s AND is_verified=0",(email,))
    user=cur.fetchone(); cur.close(); conn.close()
    if user: token=create_token(user["id"],"verify",24); send_verification_email(email,user["name"],token)
    flash("If that email is unverified, a new link has been sent.","info"); return redirect(url_for("login"))

@app.route("/forgot-password", methods=["GET","POST"])
def forgot_password():
    if request.method=="POST":
        email=request.form["email"].strip().lower(); conn=get_db(); cur=conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email=%s AND is_verified=1",(email,))
        user=cur.fetchone(); cur.close(); conn.close()
        if user: token=create_token(user["id"],"reset",1); send_reset_email(email,user["name"],token)
        flash("If that email is registered, a reset link has been sent.","info"); return redirect(url_for("login"))
    return render_template("forgot_password.html")

@app.route("/reset-password/<token>", methods=["GET","POST"])
def reset_password(token):
    conn=get_db(); cur=conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM email_tokens WHERE token=%s AND token_type='reset' AND used=0",(token,))
    rec=cur.fetchone()
    if not rec or datetime.utcnow()>rec["expires_at"]: cur.close(); conn.close(); flash("Invalid or expired link.","danger"); return redirect(url_for("forgot_password"))
    if request.method=="POST":
        pw=request.form["password"]; confirm=request.form["confirm_password"]
        if len(pw)<8 or pw!=confirm:
            flash("Password min 8 chars and must match.","danger"); cur.close(); conn.close(); return render_template("reset_password.html",token=token)
        cur.execute("UPDATE users SET password_hash=%s WHERE id=%s",(generate_password_hash(pw),rec["user_id"]))
        cur.execute("UPDATE email_tokens SET used=1 WHERE id=%s",(rec["id"],))
        conn.commit(); cur.close(); conn.close(); flash("Password reset!","success"); return redirect(url_for("login"))
    cur.close(); conn.close(); return render_template("reset_password.html",token=token)


# ─────────────────────────────────────────────
#  DASHBOARD
# ─────────────────────────────────────────────
@app.route("/")
@app.route("/dashboard")
@login_required
def dashboard():
    uid=session["user_id"]; today=date.today(); m,y=today.month,today.year
    conn=get_db(); cur=conn.cursor(dictionary=True)

    cur.execute("SELECT wallet_balance, currency_code FROM users WHERE id=%s",(uid,))
    user_row = cur.fetchone() or {}
    wallet = float(user_row.get("wallet_balance") or 0)
    currency_code = (user_row.get("currency_code") or "USD").upper()
    currency_symbol = CURRENCY_SYMBOLS.get(currency_code, "$")
    session["currency_code"] = currency_code

    cur.execute("SELECT COALESCE(SUM(amount),0) AS t FROM expenses WHERE user_id=%s AND MONTH(expense_date)=%s AND YEAR(expense_date)=%s",(uid,m,y))
    total=float(cur.fetchone()["t"])
    cur.execute("SELECT COALESCE(SUM(amount),0) AS t FROM income WHERE user_id=%s AND MONTH(income_date)=%s AND YEAR(income_date)=%s",(uid,m,y))
    total_income=float(cur.fetchone()["t"])
    cur.execute("SELECT COALESCE(AVG(ds),0) AS a FROM (SELECT SUM(amount) AS ds FROM expenses WHERE user_id=%s AND MONTH(expense_date)=%s AND YEAR(expense_date)=%s GROUP BY expense_date) x",(uid,m,y))
    avg_daily=round(float(cur.fetchone()["a"]),2)
    cur.execute("SELECT expense_date,COALESCE(SUM(amount),0) AS dt FROM expenses WHERE user_id=%s AND MONTH(expense_date)=%s AND YEAR(expense_date)=%s GROUP BY expense_date ORDER BY dt DESC LIMIT 1",(uid,m,y))
    peak=cur.fetchone(); peak_day=str(peak["expense_date"]) if peak else "—"; peak_total=float(peak["dt"]) if peak else 0
    cur.execute("SELECT COUNT(*) AS c FROM expenses WHERE user_id=%s AND MONTH(expense_date)=%s AND YEAR(expense_date)=%s",(uid,m,y))
    tx_count=cur.fetchone()["c"]

    days_in=calendar.monthrange(y,m)[1]
    cur.execute("SELECT DAY(expense_date) AS d,SUM(amount) AS t FROM expenses WHERE user_id=%s AND MONTH(expense_date)=%s AND YEAR(expense_date)=%s GROUP BY DAY(expense_date)",(uid,m,y))
    dmap={r["d"]:float(r["t"]) for r in cur.fetchall()}
    cur.execute("SELECT DAY(income_date) AS d,SUM(amount) AS t FROM income WHERE user_id=%s AND MONTH(income_date)=%s AND YEAR(income_date)=%s GROUP BY DAY(income_date)",(uid,m,y))
    imap={r["d"]:float(r["t"]) for r in cur.fetchall()}
    daily_labels=list(range(1,days_in+1))
    daily_data=[dmap.get(d,0) for d in daily_labels]
    income_data=[imap.get(d,0) for d in daily_labels]

    cur.execute("SELECT category,COALESCE(SUM(amount),0) AS t FROM expenses WHERE user_id=%s AND MONTH(expense_date)=%s AND YEAR(expense_date)=%s GROUP BY category ORDER BY t DESC",(uid,m,y))
    cat_rows=cur.fetchall(); cat_labels=[r["category"] for r in cat_rows]; cat_data=[float(r["t"]) for r in cat_rows]

    cur.execute("SELECT * FROM budgets WHERE user_id=%s AND month=%s AND year=%s",(uid,m,y))
    budgets={r["category"]:float(r["amount"]) for r in cur.fetchall()}

    cur.execute("SELECT * FROM savings_goals WHERE user_id=%s ORDER BY created_at DESC LIMIT 3",(uid,))
    goals_raw=cur.fetchall()
    goals=[{**g,"pct":round(min(float(g["saved_amount"])/float(g["target_amount"])*100,100),1) if float(g["target_amount"])>0 else 0} for g in goals_raw]

    cur.execute("""(SELECT id,'expense' AS type,title,category,amount,expense_date AS txdate,note FROM expenses WHERE user_id=%s)
        UNION ALL (SELECT id,'income' AS type,title,category,amount,income_date AS txdate,note FROM income WHERE user_id=%s)
        ORDER BY txdate DESC,id DESC LIMIT 6""",(uid,uid))
    recent=cur.fetchall()

    cur.execute("SELECT COALESCE(SUM(amount),0) AS t FROM expenses WHERE user_id=%s AND MONTH(expense_date)=%s AND YEAR(expense_date)=%s",(uid,m,y))
    total_expenses=float(cur.fetchone()["t"])

    cur.close(); conn.close()

    return render_template("dashboard.html",
        wallet_balance=wallet,total_expenses=total_expenses,total_income=total_income,avg_daily=avg_daily,
        peak_day=peak_day,peak_total=peak_total,tx_count=tx_count,
        daily_labels=daily_labels,daily_data=daily_data,income_data=income_data,
        cat_labels=cat_labels,cat_data=cat_data,cat_colors_js=CAT_COLORS,
        budgets=budgets,goals=goals,recent=recent,cat_icons=CAT_ICONS,
        days_in_month=days_in, month_name=today.strftime("%B %Y"),
        currency_code=currency_code, currency_symbol=currency_symbol)

@app.route("/add_money", methods=["GET", "POST"])
@login_required
def add_money():
    uid=session["user_id"]
    if request.method == "POST":
        amount=float(request.form.get("amount",0))
        if amount<=0: flash("Enter a valid amount.","danger"); return redirect(url_for("add_money"))
        conn=get_db(); cur=conn.cursor()
        cur.execute("UPDATE users SET wallet_balance=wallet_balance+%s WHERE id=%s",(amount,uid))
        conn.commit(); cur.close(); conn.close()
        flash(f"${amount:.2f} added to wallet!","success"); return redirect(url_for("dashboard"))
    conn=get_db(); cur=conn.cursor(dictionary=True)
    cur.execute("SELECT wallet_balance FROM users WHERE id=%s",(uid,))
    wallet=float(cur.fetchone()["wallet_balance"] or 0)
    cur.close(); conn.close()
    return render_template("add_money.html", wallet_balance=wallet)


# ─────────────────────────────────────────────
#  EXPENSES  (search & filter)
# ─────────────────────────────────────────────
@app.route("/expenses")
@login_required
def expenses():
    uid=session["user_id"]
    q=request.args.get("q","").strip(); cat_filter=request.args.get("category","")
    date_from=request.args.get("date_from",""); date_to=request.args.get("date_to","")
    sort=request.args.get("sort","date_desc")
    conn=get_db(); cur=conn.cursor(dictionary=True)
    sql="SELECT * FROM expenses WHERE user_id=%s"; params=[uid]
    if q: sql+=" AND (title LIKE %s OR note LIKE %s)"; params+=[f"%{q}%",f"%{q}%"]
    if cat_filter: sql+=" AND category=%s"; params.append(cat_filter)
    if date_from: sql+=" AND expense_date>=%s"; params.append(date_from)
    if date_to:   sql+=" AND expense_date<=%s"; params.append(date_to)
    order={"date_desc":"expense_date DESC,id DESC","date_asc":"expense_date ASC","amount_desc":"amount DESC","amount_asc":"amount ASC"}
    sql+=f" ORDER BY {order.get(sort,'expense_date DESC,id DESC')}"
    cur.execute(sql,params); rows=cur.fetchall(); cur.close(); conn.close()
    return render_template("expenses.html",expenses=rows,categories=CATEGORIES,
        cat_icons=CAT_ICONS,q=q,cat_filter=cat_filter,date_from=date_from,date_to=date_to,sort=sort)

@app.route("/add", methods=["GET","POST"])
@login_required
def add_expense():
    if request.method=="POST":
        uid=session["user_id"]
        conn=get_db(); cur=conn.cursor()
        amount=float(request.form["amount"])
        cur.execute("INSERT INTO expenses (user_id,title,amount,category,expense_date,note) VALUES(%s,%s,%s,%s,%s,%s)",
            (uid,request.form["title"].strip(),amount,request.form["category"],
             request.form["expense_date"],request.form.get("note","").strip()))
        if request.form.get("deduct_wallet"):
            cur.execute("UPDATE users SET wallet_balance=GREATEST(wallet_balance-%s,0) WHERE id=%s",(amount,uid))
        conn.commit(); cur.close(); conn.close()
        flash("Expense added!","success"); return redirect(url_for("expenses"))
    return render_template("add_expense.html",categories=CATEGORIES,cat_icons=CAT_ICONS,today=date.today().isoformat())

@app.route("/add/bill", methods=["POST"])
@login_required
def add_expense_from_bill():
    uid = session["user_id"]
    bill_file = request.files.get("bill_file")
    expense_date = request.form.get("expense_date") or date.today().isoformat()
    deduct_wallet = bool(request.form.get("deduct_wallet"))

    if not bill_file or bill_file.filename == "":
        flash("Please choose a bill image to upload.", "danger")
        return redirect(url_for("add_expense"))
    if not allowed_bill_file(bill_file.filename):
        flash("Unsupported bill format. Use png/jpg/jpeg/webp.", "danger")
        return redirect(url_for("add_expense"))

    os.makedirs(app.config["BILL_UPLOAD_FOLDER"], exist_ok=True)
    ext = bill_file.filename.rsplit(".", 1)[1].lower()
    filename = secure_filename(f"bill_{uid}_{uuid.uuid4().hex[:8]}.{ext}")
    image_path = os.path.join(app.config["BILL_UPLOAD_FOLDER"], filename)
    bill_file.save(image_path)

    text, error = extract_text_from_bill_image(image_path)
    if error:
        flash(error, "warning")
        return redirect(url_for("add_expense"))

    parsed_items = parse_bill_items(text)
    if not parsed_items:
        flash("No expense line items found in this bill. Try a clearer image.", "warning")
        return redirect(url_for("add_expense"))
    if len(parsed_items) > 80:
        parsed_items = parsed_items[:80]
        flash("Large bill detected: showing first 80 parsed items for review.", "info")

    return render_template(
        "review_bill_items.html",
        items=parsed_items,
        expense_date=expense_date,
        deduct_wallet=deduct_wallet,
        categories=CATEGORIES,
        cat_icons=CAT_ICONS,
    )

@app.route("/add/bill/confirm", methods=["POST"])
@login_required
def confirm_bill_items():
    uid = session["user_id"]
    expense_date = request.form.get("expense_date") or date.today().isoformat()
    deduct_wallet = bool(request.form.get("deduct_wallet"))

    selected_indexes = {
        int(idx) for idx in request.form.getlist("include_item") if str(idx).isdigit()
    }
    titles = request.form.getlist("item_title")
    amounts = request.form.getlist("item_amount")
    categories = request.form.getlist("item_category")

    if not titles or not amounts or not categories:
        flash("No bill items provided for confirmation.", "warning")
        return redirect(url_for("add_expense"))

    conn = get_db()
    if not conn:
        flash("Database connection failed.", "danger")
        return redirect(url_for("add_expense"))

    cur = conn.cursor()
    inserted_count = 0
    total_inserted = 0.0

    item_count = min(len(titles), len(amounts), len(categories))
    for i in range(item_count):
        if i not in selected_indexes:
            continue
        title = (titles[i] or "").strip()[:150]
        category = (categories[i] or "Others").strip()
        if category not in CATEGORIES:
            category = "Others"
        try:
            amount = round(float(amounts[i]), 2)
        except ValueError:
            continue
        if not title or amount <= 0:
            continue
        cur.execute(
            "INSERT INTO expenses (user_id,title,amount,category,expense_date,note) VALUES(%s,%s,%s,%s,%s,%s)",
            (uid, title, amount, category, expense_date, "[Auto] Extracted from uploaded bill"),
        )
        inserted_count += 1
        total_inserted += amount

    if inserted_count == 0:
        cur.close()
        conn.close()
        flash("No valid bill items were selected to save.", "warning")
        return redirect(url_for("add_expense"))

    if deduct_wallet:
        cur.execute("UPDATE users SET wallet_balance=GREATEST(wallet_balance-%s,0) WHERE id=%s", (total_inserted, uid))

    conn.commit()
    cur.close()
    conn.close()
    flash(f"Added {inserted_count} expense item(s) from bill.", "success")
    return redirect(url_for("expenses"))

@app.route("/edit/<int:eid>", methods=["GET","POST"])
@login_required
def edit_expense(eid):
    uid=session["user_id"]; conn=get_db(); cur=conn.cursor(dictionary=True)
    if request.method=="POST":
        cur.execute("UPDATE expenses SET title=%s,amount=%s,category=%s,expense_date=%s,note=%s WHERE id=%s AND user_id=%s",
            (request.form["title"].strip(),float(request.form["amount"]),request.form["category"],
             request.form["expense_date"],request.form.get("note","").strip(),eid,uid))
        conn.commit(); cur.close(); conn.close(); flash("Updated!","success"); return redirect(url_for("expenses"))
    cur.execute("SELECT * FROM expenses WHERE id=%s AND user_id=%s",(eid,uid))
    expense=cur.fetchone(); cur.close(); conn.close()
    if not expense: flash("Not found.","danger"); return redirect(url_for("expenses"))
    return render_template("add_expense.html",expense=expense,categories=CATEGORIES,cat_icons=CAT_ICONS,today=date.today().isoformat())

@app.route("/delete/<int:eid>", methods=["POST"])
@login_required
def delete_expense(eid):
    uid=session["user_id"]; conn=get_db(); cur=conn.cursor()
    cur.execute("DELETE FROM expenses WHERE id=%s AND user_id=%s",(eid,uid))
    conn.commit(); cur.close(); conn.close(); flash("Deleted.","info"); return redirect(url_for("expenses"))


# ─────────────────────────────────────────────
#  INCOME
# ─────────────────────────────────────────────
@app.route("/income")
@login_required
def income_list():
    uid=session["user_id"]; conn=get_db(); cur=conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM income WHERE user_id=%s ORDER BY income_date DESC,id DESC",(uid,))
    rows=cur.fetchall(); cur.close(); conn.close()
    return render_template("income.html",income_list=rows,categories=INCOME_CATS)

@app.route("/income/add", methods=["GET","POST"])
@login_required
def add_income():
    if request.method=="POST":
        uid=session["user_id"]; amount=float(request.form["amount"])
        conn=get_db(); cur=conn.cursor()
        cur.execute("INSERT INTO income (user_id,title,amount,category,income_date,note) VALUES(%s,%s,%s,%s,%s,%s)",
            (uid,request.form["title"].strip(),amount,request.form["category"],request.form["income_date"],request.form.get("note","").strip()))
        if request.form.get("add_to_wallet"):
            cur.execute("UPDATE users SET wallet_balance=wallet_balance+%s WHERE id=%s",(amount,uid))
        conn.commit(); cur.close(); conn.close(); flash("Income recorded!","success"); return redirect(url_for("income_list"))
    return render_template("add_income.html",categories=INCOME_CATS,today=date.today().isoformat())

@app.route("/income/delete/<int:iid>", methods=["POST"])
@login_required
def delete_income(iid):
    uid=session["user_id"]; conn=get_db(); cur=conn.cursor()
    cur.execute("DELETE FROM income WHERE id=%s AND user_id=%s",(iid,uid))
    conn.commit(); cur.close(); conn.close(); flash("Deleted.","info"); return redirect(url_for("income_list"))


# ─────────────────────────────────────────────
#  BUDGET PLANNER
# ─────────────────────────────────────────────
@app.route("/budget")
@login_required
def budget():
    uid=session["user_id"]; today=date.today(); m,y=today.month,today.year
    conn=get_db(); cur=conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM budgets WHERE user_id=%s AND month=%s AND year=%s",(uid,m,y))
    budgets={r["category"]:float(r["amount"]) for r in cur.fetchall()}
    cur.execute("SELECT category,COALESCE(SUM(amount),0) AS spent FROM expenses WHERE user_id=%s AND MONTH(expense_date)=%s AND YEAR(expense_date)=%s GROUP BY category",(uid,m,y))
    spent={r["category"]:float(r["spent"]) for r in cur.fetchall()}
    cur.close(); conn.close()
    rows=[{"category":c,"icon":CAT_ICONS[c],"budget":budgets.get(c,0),"spent":spent.get(c,0),
           "pct":round(min(spent.get(c,0)/budgets[c]*100,100),1) if budgets.get(c,0)>0 else 0,
           "over":spent.get(c,0)>budgets.get(c,0)>0} for c in CATEGORIES]
    return render_template("budget.html",rows=rows,categories=CATEGORIES,month_name=today.strftime("%B %Y"),m=m,y=y)

@app.route("/budget/save", methods=["POST"])
@login_required
def save_budget():
    uid=session["user_id"]; today=date.today(); m,y=today.month,today.year
    conn=get_db(); cur=conn.cursor()
    for cat in CATEGORIES:
        val=request.form.get(f"budget_{cat}","").strip()
        if val:
            cur.execute("INSERT INTO budgets (user_id,category,month,year,amount) VALUES(%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE amount=%s",
                        (uid,cat,m,y,float(val),float(val)))
    conn.commit(); cur.close(); conn.close(); flash("Budgets saved!","success"); return redirect(url_for("budget"))


# ─────────────────────────────────────────────
#  SAVINGS GOALS
# ─────────────────────────────────────────────
@app.route("/goals")
@login_required
def goals():
    uid=session["user_id"]; conn=get_db(); cur=conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM savings_goals WHERE user_id=%s ORDER BY created_at DESC",(uid,))
    raw=cur.fetchall(); cur.close(); conn.close()
    data=[{**g,"pct":round(min(float(g["saved_amount"])/float(g["target_amount"])*100,100),1) if float(g["target_amount"])>0 else 0,
            "remaining":max(float(g["target_amount"])-float(g["saved_amount"]),0)} for g in raw]
    return render_template("goals.html",goals=data,goal_icons=GOAL_ICONS)

@app.route("/goals/add", methods=["POST"])
@login_required
def add_goal():
    uid=session["user_id"]; conn=get_db(); cur=conn.cursor()
    cur.execute("INSERT INTO savings_goals (user_id,title,target_amount,deadline,icon) VALUES(%s,%s,%s,%s,%s)",
        (uid,request.form["title"].strip(),float(request.form["target_amount"]),
         request.form.get("deadline") or None,request.form.get("icon","🎯")))
    conn.commit(); cur.close(); conn.close(); flash("Goal created!","success"); return redirect(url_for("goals"))

@app.route("/goals/deposit/<int:gid>", methods=["POST"])
@login_required
def goal_deposit(gid):
    uid=session["user_id"]; amount=float(request.form.get("amount",0))
    conn=get_db(); cur=conn.cursor()
    cur.execute("UPDATE savings_goals SET saved_amount=LEAST(saved_amount+%s,target_amount) WHERE id=%s AND user_id=%s",(amount,gid,uid))
    if request.form.get("deduct_wallet"):
        cur.execute("UPDATE users SET wallet_balance=GREATEST(wallet_balance-%s,0) WHERE id=%s",(amount,uid))
    conn.commit(); cur.close(); conn.close(); flash(f"${amount:.2f} added to goal!","success"); return redirect(url_for("goals"))

@app.route("/goals/delete/<int:gid>", methods=["POST"])
@login_required
def delete_goal(gid):
    uid=session["user_id"]; conn=get_db(); cur=conn.cursor()
    cur.execute("DELETE FROM savings_goals WHERE id=%s AND user_id=%s",(gid,uid))
    conn.commit(); cur.close(); conn.close(); flash("Goal deleted.","info"); return redirect(url_for("goals"))


# ─────────────────────────────────────────────
#  RECURRING EXPENSES
# ─────────────────────────────────────────────
@app.route("/recurring")
@login_required
def recurring():
    uid=session["user_id"]; conn=get_db(); cur=conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM recurring_expenses WHERE user_id=%s ORDER BY day_of_month",(uid,))
    rows=cur.fetchall(); cur.close(); conn.close()
    return render_template("recurring.html",recurring=rows,categories=CATEGORIES,cat_icons=CAT_ICONS)

@app.route("/recurring/add", methods=["POST"])
@login_required
def add_recurring():
    uid=session["user_id"]; conn=get_db(); cur=conn.cursor()
    cur.execute("INSERT INTO recurring_expenses (user_id,title,amount,category,day_of_month,note) VALUES(%s,%s,%s,%s,%s,%s)",
        (uid,request.form["title"].strip(),float(request.form["amount"]),
         request.form["category"],int(request.form["day_of_month"]),request.form.get("note","").strip()))
    conn.commit(); cur.close(); conn.close(); flash("Recurring expense added!","success"); return redirect(url_for("recurring"))

@app.route("/recurring/toggle/<int:rid>", methods=["POST"])
@login_required
def toggle_recurring(rid):
    uid=session["user_id"]; conn=get_db(); cur=conn.cursor()
    cur.execute("UPDATE recurring_expenses SET is_active=NOT is_active WHERE id=%s AND user_id=%s",(rid,uid))
    conn.commit(); cur.close(); conn.close(); return redirect(url_for("recurring"))

@app.route("/recurring/delete/<int:rid>", methods=["POST"])
@login_required
def delete_recurring(rid):
    uid=session["user_id"]; conn=get_db(); cur=conn.cursor()
    cur.execute("DELETE FROM recurring_expenses WHERE id=%s AND user_id=%s",(rid,uid))
    conn.commit(); cur.close(); conn.close(); flash("Removed.","info"); return redirect(url_for("recurring"))


# ─────────────────────────────────────────────
#  EXPORT CSV
# ─────────────────────────────────────────────
@app.route("/export/csv")
@login_required
def export_csv():
    uid=session["user_id"]; date_from=request.args.get("from",""); date_to=request.args.get("to","")
    conn=get_db(); cur=conn.cursor(dictionary=True)
    sql="SELECT title,category,amount,expense_date,note FROM expenses WHERE user_id=%s"; params=[uid]
    if date_from: sql+=" AND expense_date>=%s"; params.append(date_from)
    if date_to:   sql+=" AND expense_date<=%s"; params.append(date_to)
    sql+=" ORDER BY expense_date DESC"
    cur.execute(sql,params); rows=cur.fetchall(); cur.close(); conn.close()
    si=io.StringIO(); w=csv.writer(si)
    w.writerow(["Date","Title","Category","Amount","Note"])
    for r in rows: w.writerow([r["expense_date"],r["title"],r["category"],f"${r['amount']:.2f}",r["note"] or ""])
    return Response(si.getvalue(),mimetype="text/csv",
        headers={"Content-Disposition":f"attachment;filename=expenses_{date.today()}.csv"})

@app.route("/export/income-csv")
@login_required
def export_income_csv():
    uid=session["user_id"]; conn=get_db(); cur=conn.cursor(dictionary=True)
    cur.execute("SELECT title,category,amount,income_date,note FROM income WHERE user_id=%s ORDER BY income_date DESC",(uid,))
    rows=cur.fetchall(); cur.close(); conn.close()
    si=io.StringIO(); w=csv.writer(si)
    w.writerow(["Date","Title","Category","Amount","Note"])
    for r in rows: w.writerow([r["income_date"],r["title"],r["category"],f"${r['amount']:.2f}",r["note"] or ""])
    return Response(si.getvalue(),mimetype="text/csv",
        headers={"Content-Disposition":f"attachment;filename=income_{date.today()}.csv"})


# ─────────────────────────────────────────────
#  API
# ─────────────────────────────────────────────
@app.route("/api/daily")
@login_required
def api_daily():
    uid=session["user_id"]; days=int(request.args.get("days",30))
    today=date.today(); m,y=today.month,today.year
    conn=get_db(); cur=conn.cursor(dictionary=True)
    cur.execute("SELECT DAY(expense_date) AS d,SUM(amount) AS t FROM expenses WHERE user_id=%s AND MONTH(expense_date)=%s AND YEAR(expense_date)=%s AND DAY(expense_date)<=%s GROUP BY DAY(expense_date)",(uid,m,y,days))
    emap={r["d"]:float(r["t"]) for r in cur.fetchall()}
    cur.execute("SELECT DAY(income_date) AS d,SUM(amount) AS t FROM income WHERE user_id=%s AND MONTH(income_date)=%s AND YEAR(income_date)=%s AND DAY(income_date)<=%s GROUP BY DAY(income_date)",(uid,m,y,days))
    imap={r["d"]:float(r["t"]) for r in cur.fetchall()}
    cur.close(); conn.close()
    labels=list(range(1,days+1))
    return jsonify({"labels":labels,"expenses":[emap.get(d,0) for d in labels],"income":[imap.get(d,0) for d in labels]})


# ─────────────────────────────────────────────
#  DEBUG
# ─────────────────────────────────────────────
@app.route("/test-email")
def test_email():
    to=request.args.get("to","")
    if not to: return "Usage: /test-email?to=your@email.com",400
    ok=send_email(to,"Finance App Test","<h2>It works!</h2>")
    return (f"<h3 style='color:green'>Sent to {to}!</h3>" if ok else "<h3 style='color:red'>Failed. Check terminal.</h3>"),200 if ok else 500

@app.route("/debug-verify")
def debug_verify():
    if not app.debug: return "Not available",403
    email=request.args.get("email","").strip().lower()
    if not email: return "Usage: /debug-verify?email=...",400
    conn=get_db()
    if not conn: return "Database connection failed.", 500
    cur=conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE email=%s",(email,))
    user=cur.fetchone()
    if not user: cur.close(); conn.close(); return f"No user: {email}",404
    cur.execute("UPDATE users SET is_verified=1 WHERE id=%s",(user["id"],))
    conn.commit(); cur.close(); conn.close()
    return f"<h3 style='color:green'>{user['name']} verified!</h3><p><a href='/login'>Login</a></p>"


# ─────────────────────────────────────────────
#  SETTINGS & PROFILE
# ─────────────────────────────────────────────

@app.route("/settings")
@login_required
def settings():
    uid = session["user_id"]
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE id=%s", (uid,))
    user = cur.fetchone()
    cur.close(); conn.close()
    if not user: return redirect(url_for('logout'))
    return render_template("settings.html", user=user)

@app.route("/settings/currency", methods=["POST"])
@login_required
def update_currency():
    uid = session["user_id"]
    new_currency_code = request.form.get("currency_code", "USD").strip().upper()

    if new_currency_code not in CURRENCY_CODES:
        flash("Invalid currency selected.", "danger")
        return redirect(url_for("settings"))

    conn = get_db()
    if not conn:
        flash("Database connection failed.", "danger")
        return redirect(url_for("settings"))

    cur = conn.cursor()
    try:
        cur.execute("SELECT currency_code FROM users WHERE id=%s", (uid,))
        row = cur.fetchone()
        old_currency_code = (row[0] if row and row[0] else "USD").upper()

        if old_currency_code == new_currency_code:
            session["currency_code"] = new_currency_code
            flash("Currency is already selected.", "info")
            return redirect(url_for("settings"))

        rate = fetch_conversion_rate(old_currency_code, new_currency_code)
        if not rate:
            flash("Could not fetch live exchange rate right now. Try again.", "danger")
            return redirect(url_for("settings"))

        # Convert all stored monetary values for this user to the new currency.
        cur.execute("UPDATE users SET wallet_balance=ROUND(wallet_balance*%s,2), currency_code=%s WHERE id=%s",
                    (rate, new_currency_code, uid))
        cur.execute("UPDATE expenses SET amount=ROUND(amount*%s,2) WHERE user_id=%s", (rate, uid))
        cur.execute("UPDATE income SET amount=ROUND(amount*%s,2) WHERE user_id=%s", (rate, uid))
        cur.execute("UPDATE budgets SET amount=ROUND(amount*%s,2) WHERE user_id=%s", (rate, uid))
        cur.execute("UPDATE recurring_expenses SET amount=ROUND(amount*%s,2) WHERE user_id=%s", (rate, uid))
        cur.execute(
            "UPDATE savings_goals SET target_amount=ROUND(target_amount*%s,2), saved_amount=ROUND(saved_amount*%s,2) WHERE user_id=%s",
            (rate, rate, uid),
        )

        conn.commit()
        session["currency_code"] = new_currency_code
        flash(f"Currency converted from {old_currency_code} to {new_currency_code}.", "success")
    except Error as e:
        msg = str(e).lower()
        if "unknown column" in msg and "currency_code" in msg:
            flash("Currency column is missing in database. Please run the latest migration.", "warning")
        else:
            flash("Could not update currency right now.", "danger")
            print(f"[Settings currency update] {e}")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("settings"))

@app.route("/profile/update", methods=["POST"])
@login_required
def update_profile():
    uid = session["user_id"]
    name = request.form.get("name", "").strip()
    dob = request.form.get("dob", "").strip()
    
    if not dob: dob = None

    
    if not name:
        flash("Name cannot be empty.", "danger")
        return redirect(url_for('settings'))

    conn = get_db(); cur = conn.cursor()
    
    # Handle Profile Picture Upload
    if 'profile_pic' in request.files:
        file = request.files['profile_pic']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(f"user_{uid}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cur.execute("UPDATE users SET profile_pic=%s WHERE id=%s", (filename, uid))
            session["profile_pic"] = filename

    cur.execute("UPDATE users SET name=%s, dob=%s WHERE id=%s", (name, dob, uid))
    conn.commit()
    cur.close(); conn.close()
    
    session["user_name"] = name
    flash("Profile updated successfully!", "success")
    return redirect(url_for('settings'))

@app.route("/send-mobile-otp", methods=["POST"])
@login_required
def send_mobile_otp():
    mobile = request.form.get("mobile", "").strip()
    if not mobile or len(mobile) < 10:
        flash("Please enter a valid mobile number.", "danger")
        return redirect(url_for("settings"))
        
    otp = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    session["mobile_verification"] = {"mobile": mobile, "otp": otp}
    
    print(f"\n" + "="*50)
    print(f"📱 DEVELOPMENT SMS OTP FOR {mobile}: {otp}")
    print("="*50 + "\n")
    
    flash(f"For testing, your SMS OTP is: {otp} (Check terminal)", "success")
    return redirect(url_for("settings"))

@app.route("/verify-mobile-otp", methods=["POST"])
@login_required
def verify_mobile_otp():
    uid = session["user_id"]
    entered_otp = request.form.get("otp", "").strip()
    verification = session.get("mobile_verification")
    
    if not verification:
        flash("Verification session expired. Please request a new code.", "danger")
        return redirect(url_for("settings"))
        
    if entered_otp == verification["otp"]:
        conn = get_db(); cur = conn.cursor()
        cur.execute("UPDATE users SET mobile=%s, is_mobile_verified=1 WHERE id=%s", (verification["mobile"], uid))
        conn.commit(); cur.close(); conn.close()
        session.pop("mobile_verification", None)
        flash("Mobile number verified successfully!", "success")
    else:
        flash("Invalid OTP. Please try again.", "danger")
        
    return redirect(url_for("settings"))

@app.route("/profile/remove-avatar", methods=["POST"])
@login_required
def remove_avatar():
    uid = session["user_id"]
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE users SET profile_pic=NULL WHERE id=%s", (uid,))
    conn.commit(); cur.close(); conn.close()
    session["profile_pic"] = None
    flash("Profile picture removed.", "info")
    return redirect(url_for('settings'))

@app.route("/account/delete", methods=["POST"])
@login_required
def delete_account():
    uid = session["user_id"]
    conn = get_db(); cur = conn.cursor()
    
    # All related data will be deleted via ON DELETE CASCADE in MySQL
    # (expenses, income, budgets, goals, recurring_expenses, email_tokens)
    cur.execute("DELETE FROM users WHERE id=%s", (uid,))
    conn.commit(); cur.close(); conn.close()
    
    session.clear()
    flash("Your account has been permanently deleted. We're sorry to see you go.", "info")
    return redirect(url_for('login'))

# ─────────────────────────────────────────────
#  API & INTEGRATIONS
# ─────────────────────────────────────────────
@app.route("/api/sync/gpay", methods=["POST"])
@login_required
def sync_gpay():
    uid = session["user_id"]
    data = request.get_json() or {}
    amount = float(data.get("amount", 0))
    title = data.get("title", "GPay Payment")
    
    if amount <= 0:
        return jsonify({"status": "error", "message": "Invalid amount"}), 400
        
    category = infer_category_from_title(title)
    
    conn = get_db()
    if not conn:
        return jsonify({"status": "error", "message": "Database error"}), 500
        
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO expenses (user_id, title, amount, category, expense_date, note) VALUES (%s, %s, %s, %s, %s, %s)",
                    (uid, title, amount, category, date.today().isoformat(), "[Auto] Synced via GPay"))
        cur.execute("UPDATE users SET wallet_balance = GREATEST(wallet_balance - %s, 0) WHERE id = %s", (amount, uid))
        conn.commit()
        return jsonify({"status": "success", "message": f"Automatically added {title} (${amount}) to your tracker."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cur.close()
        conn.close()

# ─────────────────────────────────────────────
#  GMAIL UPI SYNC INTEGRATION
# ─────────────────────────────────────────────
try:
    from upi_gmail_sync import fetch_upi_transactions_from_gmail
except ImportError:
    pass

@app.route("/sync/upi", methods=["GET"])
@login_required
def upi_sync_page():
    return render_template("upi_sync.html")

@app.route("/sync/upi/fetch", methods=["POST"])
@login_required
def upi_sync_fetch():
    """Fetch UPI transactions from Gmail and show review page."""
    days = int(request.form.get("days", 30))
    uid = session["user_id"]

    try:
        transactions = fetch_upi_transactions_from_gmail(days=days)
    except Exception as e:
        flash(f"Could not fetch Gmail transactions: {e}", "danger")
        return redirect(url_for("upi_sync_page"))

    if not transactions:
        flash("No UPI transactions found in Gmail for the selected period.", "info")
        return redirect(url_for("upi_sync_page"))

    # Filter out already-imported (check by upi_ref in expenses notes)
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT note FROM expenses WHERE user_id=%s AND note LIKE 'UPI_REF:%%'", (uid,))
    existing_refs = {row["note"] for row in cur.fetchall() if row["note"]}
    cur.close()
    conn.close()

    new_txns = [t for t in transactions if f"UPI_REF:{t['upi_ref']}" not in existing_refs]

    session["pending_upi_txns"] = new_txns   # store for confirm step
    return render_template("review_upi_transactions.html", transactions=new_txns, days=days)

@app.route("/sync/upi/confirm", methods=["POST"])
@login_required
def upi_sync_confirm():
    """Save selected UPI transactions as expenses."""
    uid = session["user_id"]
    pending = session.pop("pending_upi_txns", [])

    selected_indices = request.form.getlist("selected")
    saved = 0
    conn = get_db()
    cur = conn.cursor()

    for idx_str in selected_indices:
        try:
            idx = int(idx_str)
            txn = pending[idx]
        except (ValueError, IndexError):
            continue

        title    = request.form.get(f"title_{idx}", txn["title"])
        category = request.form.get(f"category_{idx}", txn["category"])
        amount   = request.form.get(f"amount_{idx}", txn["amount"])
        txn_date = request.form.get(f"date_{idx}", txn["date"])

        try:
            amount = float(amount)
        except ValueError:
            continue

        note = f"UPI_REF:{txn['upi_ref']}"

        cur.execute(
            "INSERT INTO expenses (user_id, title, amount, category, expense_date, note) VALUES (%s,%s,%s,%s,%s,%s)",
            (uid, title, amount, category, txn_date, note)
        )
        saved += 1

    conn.commit()
    cur.close()
    conn.close()
    
    flash(f"✅ {saved} UPI transaction(s) imported successfully!", "success")
    return redirect(url_for("expenses"))

if __name__ == "__main__":
    app.run(debug=True)
