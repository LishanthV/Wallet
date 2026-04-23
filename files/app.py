import os, secrets, smtplib, csv, io
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from datetime             import datetime, date, timedelta
from functools            import wraps

from flask import (Flask, render_template, request, redirect,
                   url_for, jsonify, flash, session, Response)
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error
import calendar

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "finance_super_secret_2025")

DB_CONFIG = {
    "host":     os.environ.get("DB_HOST",     "localhost"),
    "user":     os.environ.get("DB_USER",     "root"),
    "password": os.environ.get("DB_PASSWORD", "your_password"),
    "database": os.environ.get("DB_NAME",     "finance_db"),
}
SMTP_CONFIG = {
    "host":     os.environ.get("SMTP_HOST",     "smtp.gmail.com"),
    "port":     int(os.environ.get("SMTP_PORT", "587")),
    "user":     os.environ.get("SMTP_USER",     "your_gmail@gmail.com"),
    "password": os.environ.get("SMTP_PASSWORD", "your_app_password"),
    "from":     os.environ.get("SMTP_FROM",     "Finance App <your_gmail@gmail.com>"),
}
APP_URL     = os.environ.get("APP_URL", "http://127.0.0.1:5000")
CATEGORIES  = ["Food","Rent","Transport","Shopping","Bills","Entertainment","Health","Others"]
INCOME_CATS = ["Salary","Freelance","Business","Investment","Gift","Other"]
CAT_ICONS   = {"Food":"🛒","Rent":"🏠","Transport":"🚗","Shopping":"🛍️",
               "Bills":"🌐","Entertainment":"🎬","Health":"💊","Others":"💳"}
CAT_COLORS  = ["#7F77DD","#AFA9EC","#CECBF6","#534AB7","#888780","#D3D1C7","#3C3489","#B4B2A9"]
GOAL_ICONS  = ["🎯","🏖️","🚗","🏠","💻","✈️","🎓","💍","📱","💰"]


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────
def get_db():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        print(f"[DB] {e}"); return None

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
    cur.execute("""
        SELECT * FROM recurring_expenses
        WHERE user_id=%s AND is_active=1 AND day_of_month<=%s
          AND (last_applied IS NULL OR last_applied < DATE_FORMAT(%s,'%%Y-%%m-01'))
    """, (user_id, today.day, today))
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

def send_verification_email(email, name, token):
    link = f"{APP_URL}/verify-email/{token}"
    html = f"""<div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px;background:#f5f4f8;border-radius:16px">
      <div style="background:#7F77DD;border-radius:12px;padding:24px;text-align:center;margin-bottom:24px">
        <h2 style="color:#fff;margin:0">Finance Dashboard</h2></div>
      <h3 style="color:#1a1a2e">Hi {name},</h3>
      <p style="color:#6b6a75;line-height:1.7">Thanks for signing up! Verify your email — link expires in <strong>24 hours</strong>.</p>
      <div style="text-align:center;margin:28px 0">
        <a href="{link}" style="background:#7F77DD;color:#fff;padding:13px 36px;border-radius:8px;text-decoration:none;font-weight:600">Verify Email</a></div>
      <p style="color:#9f9ea8;font-size:12px;text-align:center">Or copy: <a href="{link}">{link}</a></p></div>"""
    return send_email(email, "Verify your Finance Dashboard account", html)

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
        pw=request.form["password"]; confirm=request.form["confirm_password"]
        if len(name)<2:  flash("Name too short.","danger");        return render_template("register.html")
        if len(pw)<8:    flash("Password min 8 chars.","danger");  return render_template("register.html")
        if pw!=confirm:  flash("Passwords don't match.","danger"); return render_template("register.html")
        conn=get_db(); cur=conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM users WHERE email=%s",(email,))
        if cur.fetchone():
            flash("Email already registered.","danger"); cur.close(); conn.close()
            return render_template("register.html")
        cur.execute("INSERT INTO users (name,email,password_hash) VALUES(%s,%s,%s)",
                    (name,email,generate_password_hash(pw)))
        conn.commit(); uid=cur.lastrowid; cur.close(); conn.close()
        token=create_token(uid,"verify",24); sent=send_verification_email(email,name,token)
        flash("Account created! Check your email." if sent
              else "Account created but email failed. Use Resend below.","success" if sent else "warning")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if "user_id" in session: return redirect(url_for("dashboard"))
    if request.method == "POST":
        email=request.form["email"].strip().lower(); pw=request.form["password"]
        conn=get_db(); cur=conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email=%s",(email,))
        user=cur.fetchone(); cur.close(); conn.close()
        if not user or not check_password_hash(user["password_hash"],pw):
            flash("Invalid email or password.","danger"); return render_template("login.html")
        if not user["is_verified"]:
            flash("Please verify your email first.","warning")
            return render_template("login.html",unverified=True,unverified_email=email)
        session.update({"user_id":user["id"],"user_name":user["name"],"user_email":user["email"]})
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

    cur.execute("SELECT wallet_balance FROM users WHERE id=%s",(uid,))
    wallet=float(cur.fetchone()["wallet_balance"] or 0)

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
    cur.close(); conn.close()

    return render_template("dashboard.html",
        wallet=wallet,total=total,total_income=total_income,avg_daily=avg_daily,
        peak_day=peak_day,peak_total=peak_total,tx_count=tx_count,
        daily_labels=daily_labels,daily_data=daily_data,income_data=income_data,
        cat_labels=cat_labels,cat_data=cat_data,cat_colors=CAT_COLORS,
        budgets=budgets,goals=goals,recent=recent,cat_icons=CAT_ICONS,
        month_name=today.strftime("%B %Y"))

@app.route("/wallet/topup", methods=["POST"])
@login_required
def wallet_topup():
    amount=float(request.form.get("amount",0))
    if amount<=0: flash("Enter a valid amount.","danger"); return redirect(url_for("dashboard"))
    conn=get_db(); cur=conn.cursor()
    cur.execute("UPDATE users SET wallet_balance=wallet_balance+%s WHERE id=%s",(amount,session["user_id"]))
    conn.commit(); cur.close(); conn.close()
    flash(f"${amount:.2f} added to wallet!","success"); return redirect(url_for("dashboard"))


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
    return render_template("add_expense.html",categories=CATEGORIES,today=date.today().isoformat())

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
    return render_template("add_expense.html",expense=expense,categories=CATEGORIES,today=date.today().isoformat())

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
    conn=get_db(); cur=conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE email=%s",(email,))
    user=cur.fetchone()
    if not user: cur.close(); conn.close(); return f"No user: {email}",404
    cur.execute("UPDATE users SET is_verified=1 WHERE id=%s",(user["id"],))
    conn.commit(); cur.close(); conn.close()
    return f"<h3 style='color:green'>{user['name']} verified!</h3><p><a href='/login'>Login</a></p>"


if __name__ == "__main__":
    app.run(debug=True)
