"""Conexión con Stripe (modo prueba).

Es el único archivo que habla con Stripe. Usa la API REST directamente con
urllib, igual que ai/gemini.py, para no agregar librerías. La clave secreta
(sk_test_...) vive solo en el .env y en Render; el frontend nunca la ve.

El pago es "embebido": Stripe dibuja el formulario de la tarjeta dentro de la
página de TerminAPP, así el usuario nunca sale del sitio.
"""

import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request

import config

SESSION_LIFETIME_MINUTES = 30   # el mínimo que permite Stripe para que venza una sesión de pago
REQUEST_TIMEOUT_SECONDS = 20
ERROR_DETAIL_MAX_LENGTH = 500
TEST_KEY_PREFIX = "sk_test_"
SESSION_ID_PREFIX = "cs_"
# Stripe cambió el nombre del modo embebido; se prueba el nuevo y, si la cuenta usa
# una versión anterior de la API, el anterior.
EMBEDDED_UI_MODES = ("embedded_page", "embedded")
SESSION_OPEN = "open"
SESSION_COMPLETE = "complete"
PAYMENT_STATUS_PAID = "paid"


class PaymentError(Exception):
    """Stripe no respondió o rechazó la petición."""


def _secret_key():
    key = config.STRIPE_SECRET_KEY
    if not key:
        raise PaymentError("Falta la variable de entorno STRIPE_SECRET_KEY")
    if not key.startswith(TEST_KEY_PREFIX):
        raise PaymentError("Usa una clave de prueba de Stripe (empieza con sk_test_)")
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
        raise PaymentError(f"Stripe respondió con el código {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise PaymentError(f"No se pudo conectar con Stripe: {error.reason}") from error


def _check_session_id(session_id):
    if not str(session_id).startswith(SESSION_ID_PREFIX):
        raise PaymentError("El identificador de la sesión de pago no es válido")
    return urllib.parse.quote(session_id)


def create_checkout_session(payment_id, description, unit_price, quantity, frontend_url):
    """Crea la sesión de pago embebida y devuelve {"session_id", "client_secret", "ui_mode"}."""
    data = {
        "mode": "payment",
        "client_reference_id": str(payment_id),
        "metadata[payment_id]": str(payment_id),
        "line_items[0][quantity]": str(quantity),
        "line_items[0][price_data][currency]": config.STRIPE_CURRENCY,
        # Stripe maneja los pesos con dos decimales: $61.000 se envía como 6100000
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
    """Devuelve el estado de una sesión: payment_id, si está pagada, si sigue abierta y su client_secret."""
    session = _send_request("GET", "/checkout/sessions/" + _check_session_id(session_id))
    return {
        "payment_id": int(session.get("metadata", {}).get("payment_id", 0)),
        "paid": session.get("payment_status") == PAYMENT_STATUS_PAID,
        "is_open": session.get("status") == SESSION_OPEN,
        "client_secret": session.get("client_secret"),
        "ui_mode": session.get("ui_mode"),
    }


def expire_checkout_session(session_id):
    """Cierra una sesión de pago abierta para que ya no se pueda pagar (si ya cerró, no pasa nada)."""
    try:
        _send_request("POST", "/checkout/sessions/" + _check_session_id(session_id) + "/expire")
    except PaymentError:
        pass  # ya estaba vencida o pagada
