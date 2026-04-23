"""
Add these routes to your app.py
Also add: from helpers.upi_gmail_sync import fetch_upi_transactions_from_gmail
"""

# ── Add to imports in app.py ──────────────────────────────────────────────────
# from helpers.upi_gmail_sync import fetch_upi_transactions_from_gmail

# ── Add these routes to app.py ────────────────────────────────────────────────

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
    db = get_db()
    existing_refs = {
        row["note"]
        for row in db.execute(
            "SELECT note FROM expenses WHERE user_id=? AND note LIKE 'UPI_REF:%'",
            (uid,)
        ).fetchall()
    }
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
    db = get_db()

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

        db.execute(
            "INSERT INTO expenses (user_id, title, amount, category, date, note) VALUES (?,?,?,?,?,?)",
            (uid, title, amount, category, txn_date, note)
        )
        saved += 1

    db.commit()
    flash(f"✅ {saved} UPI transaction(s) imported successfully!", "success")
    return redirect(url_for("expenses"))
