"""
helpers/upi_gmail_sync.py
Fetches and parses UPI/GPay transaction emails from Gmail.
Supports: Google Pay, PhonePe, Paytm, HDFC, SBI, ICICI, Axis, Kotak alert formats.
"""

import re
import base64
import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from flask import session


# ── Category keyword mapping ───────────────────────────────────────────────────
CATEGORY_KEYWORDS = {
    "Food": [
        "swiggy", "zomato", "domino", "pizza", "mcdonald", "kfc", "burger",
        "biryani", "restaurant", "cafe", "food", "eat", "canteen", "mess",
        "hotel", "tiffin", "bakery", "juice", "tea", "coffee", "chai"
    ],
    "Transport": [
        "uber", "ola", "rapido", "auto", "cab", "taxi", "bus", "metro",
        "train", "irctc", "petrol", "fuel", "parking", "toll", "namma metro",
        "bmtc", "ksrtc", "flight", "indigo", "spicejet", "air india"
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "ajio", "meesho", "nykaa", "snapdeal",
        "shop", "store", "market", "mall", "decathlon", "reliance", "dmart",
        "bigbasket", "zepto", "blinkit", "instamart", "swiggy instamart"
    ],
    "Entertainment": [
        "bookmyshow", "pvr", "inox", "hotstar", "netflix", "prime", "spotify",
        "youtube", "cinema", "movie", "game", "play", "cricket"
    ],
    "Healthcare": [
        "pharmacy", "medical", "hospital", "clinic", "doctor", "apollo",
        "1mg", "netmeds", "medplus", "lab", "test", "health"
    ],
    "Education": [
        "school", "college", "course", "udemy", "coursera", "fees", "tuition",
        "book", "stationery", "pen", "notebook"
    ],
    "Utilities": [
        "electricity", "water", "gas", "bill", "recharge", "mobile", "jio",
        "airtel", "bsnl", "vi", "broadband", "wifi", "internet", "dth",
        "tatasky", "dish tv"
    ],
    "Rent": ["rent", "pg", "hostel", "accommodation", "flat", "house"],
}


def infer_category(title: str) -> str:
    title_lower = title.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in title_lower for kw in keywords):
            return category
    return "Others"


# ── Email body decoder ─────────────────────────────────────────────────────────
def _decode_body(payload) -> str:
    """Recursively extract plain text from Gmail message payload."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    if payload.get("mimeType") == "text/html":
        data = payload.get("body", {}).get("data", "")
        if data:
            import html as html_lib
            html = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
            # Strip HTML tags and unescape entities for clean plain text parsing
            text = re.sub(r"<[^>]+>", " ", html)
            return html_lib.unescape(text)
    for part in payload.get("parts", []):
        result = _decode_body(part)
        if result:
            return result
    return ""


# ── UPI Reference extractor ────────────────────────────────────────────────────
def _extract_upi_ref(text: str) -> str:
    patterns = [
        r"UPI\s*(?:Ref|Reference|Txn|Transaction|ID)[:\s#]*(\w{8,20})",
        r"Ref\s*No[:\s]*(\w{8,20})",
        r"Transaction\s*ID[:\s]*(\w{8,20})",
        r"\b(\d{12})\b",   # 12-digit UPI ref
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return ""


# ── Amount extractor ───────────────────────────────────────────────────────────
def _extract_amount(text: str):
    patterns = [
        r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)",
        r"([\d,]+(?:\.\d{1,2})?)\s*(?:INR|₹)",
        r"(?:debited|deducted|paid|sent|transferred)\s+(?:by|of|with|for)?\s*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{1,2})?)",
        r"Amount[:\s]+(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{1,2})?)",
        r"transaction of\s*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{1,2})?)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                pass
    return None


# ── Merchant / payee extractor ─────────────────────────────────────────────────
def _extract_merchant(text: str, subject: str) -> str:
    patterns = [
        r"(?:paid|sent|transferred|debited)\s+(?:to|for)\s+([A-Za-z0-9 &'.\-]{3,40}?)(?:\s+via|\s+on|\s+for|\.|,|$)",
        r"(?:to|payee)[:\s]+([A-Za-z0-9 &'.\-]{3,40}?)(?:\s+via|\s+on|\.|,|$)",
        r"Merchant[:\s]+([A-Za-z0-9 &'.\-]{3,40}?)(?:\.|,|\n|$)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            if len(name) > 2 and not re.match(r"^\d+$", name):
                return name
    # Fallback: clean up subject line
    subject = re.sub(r"(Google Pay|PhonePe|Paytm|UPI|Alert|Notification|Transaction)", "", subject, flags=re.IGNORECASE)
    subject = re.sub(r"[^A-Za-z0-9 ]", " ", subject).strip()
    return subject[:40] if subject else "UPI Payment"


# ── Date extractor ─────────────────────────────────────────────────────────────
def _parse_email_date(date_str: str) -> str:
    """Convert Gmail date header to YYYY-MM-DD."""
    try:
        # Gmail dates like: "Thu, 17 Apr 2026 14:38:54 +0000"
        for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%d %b %Y %H:%M:%S %z"]:
            try:
                dt = datetime.datetime.strptime(date_str.strip(), fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
    except Exception:
        pass
    return datetime.date.today().isoformat()


# ── Gmail search queries that catch UPI/payment alerts ────────────────────────
GMAIL_QUERIES = [
    'subject:"Google Pay" (sent OR paid OR debited)',
    'subject:UPI (debited OR debit OR paid)',
    'from:alerts@hdfcbank.net',
    'from:alerts@icicibank.com',
    'from:alerts@axisbank.com',
    'from:alerts@sbi.co.in',
    'from:notify@kotak.com',
    '(subject:"debited" OR subject:"UPI payment") (Rs OR INR)',
    'from:noreply@phonepe.com',
    'from:no-reply@paytm.com',
]


# ── Main function ──────────────────────────────────────────────────────────────
def fetch_upi_transactions_from_gmail(days: int = 30) -> list[dict]:
    """
    Returns a list of parsed UPI transactions from Gmail.
    Each item: { title, amount, category, date, upi_ref, source_email }
    """
    # Build Gmail service using stored OAuth token
    creds_data = session.get("google_credentials")
    if not creds_data:
        raise ValueError("Google account not connected. Please link your Google account in Settings.")

    creds = Credentials(
        token=creds_data.get("token"),
        refresh_token=creds_data.get("refresh_token"),
        token_uri=creds_data.get("token_uri"),
        client_id=creds_data.get("client_id"),
        client_secret=creds_data.get("client_secret"),
        scopes=creds_data.get("scopes"),
    )
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    since_date = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%Y/%m/%d")
    seen_ids = set()
    transactions = []

    for query in GMAIL_QUERIES:
        full_query = f"{query} after:{since_date}"
        try:
            result = service.users().messages().list(
                userId="me", q=full_query, maxResults=50
            ).execute()
        except Exception:
            continue

        messages = result.get("messages", [])
        for msg_ref in messages:
            msg_id = msg_ref["id"]
            if msg_id in seen_ids:
                continue
            seen_ids.add(msg_id)

            try:
                msg = service.users().messages().get(
                    userId="me", id=msg_id, format="full"
                ).execute()
            except Exception:
                continue

            headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
            subject = headers.get("Subject", "")
            date_str = headers.get("Date", "")

            body = _decode_body(msg["payload"])
            full_text = subject + " " + body

            amount = _extract_amount(full_text)
            if not amount or amount <= 0:
                continue

            upi_ref = _extract_upi_ref(full_text) or msg_id
            merchant = _extract_merchant(body, subject)
            category = infer_category(merchant)
            txn_date = _parse_email_date(date_str)

            transactions.append({
                "title": merchant,
                "amount": round(amount, 2),
                "category": category,
                "date": txn_date,
                "upi_ref": upi_ref,
                "source_email": subject,
            })

    # Sort newest first
    transactions.sort(key=lambda x: x["date"], reverse=True)
    return transactions
