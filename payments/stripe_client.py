"""Connection to Stripe (test mode).

This is the only file that talks to Stripe. It calls the REST API directly with
urllib, like ai/gemini.py, to avoid extra libraries. The secret key
(sk_test_...) lives only in .env and on Render; the frontend never sees it.

Payment is "embedded": Stripe draws the card form inside the TerminAPP page,
so the user never leaves the site.
"""

import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request

import config

SESSION_LIFETIME_MINUTES = 30   # the minimum Stripe allows before a payment session expires
REQUEST_TIMEOUT_SECONDS = 20
ERROR_DETAIL_MAX_LENGTH = 500
TEST_KEY_PREFIX = "sk_test_"
SESSION_ID_PREFIX = "cs_"
# Stripe renamed the embedded mode; we try the new name first and, if the account
# uses an older API version, the old one.
EMBEDDED_UI_MODES = ("embedded_page", "embedded")
SESSION_OPEN = "open"
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
    """Creates the embedded payment session and returns {"session_id", "client_secret", "ui_mode"}."""
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
        "expires_at": str(int(time.time()) + SESSION_LIFETIME_MINUTES * 60 + 60),
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
        return {"session_id": session["id"], "client_secret": session["client_secret"], "ui_mode": ui_mode}
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
    }


def expire_checkout_session(session_id):
    """Closes an open payment session so it can no longer be paid (does nothing if already closed)."""
    try:
        _send_request("POST", "/checkout/sessions/" + _check_session_id(session_id) + "/expire")
    except PaymentError:
        pass  # it was already expired or paid
