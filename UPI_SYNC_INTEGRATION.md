# GPay / UPI Gmail Sync — Integration Guide

## Files to add to your project

### 1. helpers/upi_gmail_sync.py
→ Copy from helpers/upi_gmail_sync.py

### 2. templates/upi_sync.html
→ Copy from templates/upi_sync.html

### 3. templates/review_upi_transactions.html
→ Copy from templates/review_upi_transactions.html

### 4. Add to app.py (from upi_sync_route.py)

```python
# Add import
from helpers.upi_gmail_sync import fetch_upi_transactions_from_gmail

# Add 3 routes (see upi_sync_route.py)
```

---

## Add to your Jinja2 base template — enumerate filter

In app.py, register this filter so the review template works:

```python
@app.template_filter('enumerate')
def jinja_enumerate(iterable, start=0):
    return enumerate(iterable, start)
```

---

## Add navigation link

In your sidebar/navbar, add:

```html
<a href="{{ url_for('upi_sync_page') }}">📲 Sync UPI</a>
```

---

## How transactions are de-duplicated

Each imported transaction is stored with `note = "UPI_REF:<ref_id>"`.
On every sync, existing refs are fetched and filtered out — so you never import the same transaction twice.

---

## Gmail OAuth Note

This module uses `session["google_credentials"]` which must contain your
Google OAuth token. If your app already has Google login (for the user),
reuse those credentials. If not, you need to add a Gmail OAuth flow.

### Simple OAuth setup (if not already done):

```python
pip install google-auth google-auth-oauthlib google-api-python-client
```

Add to app.py:
```python
from google_auth_oauthlib.flow import Flow

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "openid", "email", "profile"
]
```

Create a Google Cloud project → Enable Gmail API → Download credentials.json
→ Set redirect URI: http://localhost:5000/auth/google/callback

---

## What emails are scanned

The sync searches these Gmail queries:
- Google Pay sent/paid notifications
- Bank UPI debit alerts (HDFC, ICICI, SBI, Axis, Kotak)
- PhonePe and Paytm alerts

---

## Flow summary

1. User visits /sync/upi
2. Selects time range → clicks Scan Gmail
3. Gmail is searched for UPI alert emails
4. Already-imported refs are filtered out
5. Parsed transactions shown in editable review table
6. User edits title/category/amount if needed
7. Clicks Save → only selected transactions are saved
8. Flash message confirms how many were imported
