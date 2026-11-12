"""Connection to Stripe (test mode).

This is the only file that talks to Stripe. It calls the REST API directly with
urllib, like ai/gemini.py, to avoid extra libraries. The secret key
(sk_test_...) lives only in .env and on Render; the frontend never sees it.

Payment is "embedded": Stripe draws the card form inside the TerminAPP page,
so the user never leaves the site.
"""

import base64
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request

import config

SESSION_LIFETIME_MINUTES = 31   # Stripe requires at least 30 minutes; one more as a margin
REQUEST_TIMEOUT_SECONDS = 20
ERROR_DETAIL_MAX_LENGTH = 500
TEST_KEY_PREFIX = "sk_test_"
SESSION_ID_PREFIX = "cs_"
# Stripe renamed the embedded mode; we try the new name first and, if the account
# uses an older API version, the old one.
EMBEDDED_UI_MODES = ("embedded_page", "embedded")
SESSION_OPEN = "open"
WEBHOOK_TOLERANCE_SECONDS = 300   # Stripe's recommended tolerance for webhook timestamps
SESSION_COMPLETE = "complete"
PAYMENT_STATUS_PAID = "paid"


class PaymentError(Exception):
    """Stripe did not answer or rejected the request."""


def _secret_key():
    key = config.STRIPE_SECRET_KEY
    if not key:
        raise PaymentError("Missing environment variable STRIPE_SECRET_KEY")
    if not key.startswith(TEST_KEY_PREFIX):
        raise PaymentError("Use a Stripe test key (it starts with sk_test_)")
    return key


def _send_request(method, path, data=None):
    credentials = base64.b64encode(f"{_secret_key()}:".encode()).decode()
    body = urllib.parse.urlencode(data).encode() if data else None
    request = urllib.request.Request(
        config.STRIPE_API_URL + path,
        data=body,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:ERROR_DETAIL_MAX_LENGTH]
        raise PaymentError(f"Stripe answered with status {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise PaymentError(f"Could not connect to Stripe: {error.reason}") from error


def _check_session_id(session_id):
    if not str(session_id).startswith(SESSION_ID_PREFIX):
        raise PaymentError("Invalid payment session id")
    return urllib.parse.quote(session_id)


def create_checkout_session(payment_id, description, unit_price, quantity, frontend_url):
    """Creates the embedded payment session and returns
    {"session_id", "client_secret", "ui_mode", "expires_at"} (expires_at as a UTC timestamp)."""
    expires_at = int(time.time()) + SESSION_LIFETIME_MINUTES * 60
    data = {
        "mode": "payment",
        "client_reference_id": str(payment_id),
        "metadata[payment_id]": str(payment_id),
        "line_items[0][quantity]": str(quantity),
        "line_items[0][price_data][currency]": config.STRIPE_CURRENCY,
        # Stripe handles pesos with two decimals: $61,000 is sent as 6100000
        "line_items[0][price_data][unit_amount]": str(unit_price * 100),
        "line_items[0][price_data][product_data][name]": description,
        "return_url": f"{frontend_url}/?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
        "expires_at": str(expires_at),
    }
    last_error = None
    for ui_mode in EMBEDDED_UI_MODES:
        try:
            session = _send_request("POST", "/checkout/sessions", {**data, "ui_mode": ui_mode})
        except PaymentError as error:
            if "ui_mode" not in str(error):
                raise
            last_error = error
            continue
        return {
            "session_id": session["id"],
            "client_secret": session["client_secret"],
            "ui_mode": ui_mode,
            "expires_at": session.get("expires_at", expires_at),
        }
    raise last_error


def get_checkout_session(session_id):
    """Returns a session's state: payment_id, whether it is paid, whether it is still open, and its client_secret."""
    session = _send_request("GET", "/checkout/sessions/" + _check_session_id(session_id))
    return {
        "payment_id": int(session.get("metadata", {}).get("payment_id", 0)),
        "paid": session.get("payment_status") == PAYMENT_STATUS_PAID,
        "is_open": session.get("status") == SESSION_OPEN,
        "client_secret": session.get("client_secret"),
        "ui_mode": session.get("ui_mode"),
        "payment_intent": session.get("payment_intent"),
    }


def expire_checkout_session(session_id):
    """Closes an open payment session so it can no longer be paid (does nothing if already closed)."""
    try:
        _send_request("POST", "/checkout/sessions/" + _check_session_id(session_id) + "/expire")
    except PaymentError:
        pass  # it was already expired or paid


def close_session_and_check(session_id):
    """Closes a payment session so it can no longer be paid, then says whether it was paid:
    "paid", "not_paid" or "unknown" (Stripe did not answer)."""
    expire_checkout_session(session_id)
    try:
        session = get_checkout_session(session_id)
    except PaymentError:
        return "unknown"
    return "paid" if session["paid"] else "not_paid"


def refund_session(session_id):
    """Gives the whole payment of a session back to the customer."""
    session = get_checkout_session(session_id)
    if not session["payment_intent"]:
        raise PaymentError("The session has no payment to refund")
    _send_request("POST", "/refunds", {"payment_intent": session["payment_intent"]})


def read_webhook_event(payload, signature_header):
    """Checks that a webhook really comes from Stripe (HMAC-SHA256 signature with the
    webhook secret) and returns the event. Raises PaymentError if the signature is wrong."""
    if not config.STRIPE_WEBHOOK_SECRET:
        raise PaymentError("Missing environment variable STRIPE_WEBHOOK_SECRET")
    timestamp, signatures = None, []
    for part in (signature_header or "").split(","):
        key, _, value = part.strip().partition("=")
        if key == "t":
            timestamp = value
        elif key == "v1":
            signatures.append(value)
    if not timestamp or not signatures:
        raise PaymentError("Missing webhook signature")
    try:
        age = abs(time.time() - int(timestamp))
    except ValueError:
        raise PaymentError("Invalid webhook timestamp")
    if age > WEBHOOK_TOLERANCE_SECONDS:
        raise PaymentError("Webhook timestamp is too old")

    signed_content = timestamp.encode() + b"." + payload
    expected = hmac.new(config.STRIPE_WEBHOOK_SECRET.encode(), signed_content, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, signature) for signature in signatures):
        raise PaymentError("Invalid webhook signature")
    return json.loads(payload)
