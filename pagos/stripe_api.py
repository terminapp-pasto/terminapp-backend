"""Conexión con Stripe (modo prueba).

Es el único archivo que habla con Stripe. Usa la API REST directamente con
urllib, igual que ia/gemini.py, para no agregar librerías. La clave secreta
(sk_test_...) vive solo en el .env y en Render; el frontend nunca la ve.
"""

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

URL_STRIPE = "https://api.stripe.com/v1"
MINUTOS_SESION = 30  # el mínimo que permite Stripe para que venza una sesión de pago


class ErrorPago(Exception):
    """Stripe no respondió o rechazó la petición."""


def _clave():
    clave = os.getenv("STRIPE_SECRET_KEY")
    if not clave:
        raise ErrorPago("Falta la variable de entorno STRIPE_SECRET_KEY")
    if not clave.startswith("sk_test_"):
        raise ErrorPago("Usa una clave de prueba de Stripe (empieza con sk_test_)")
    return clave


def _peticion(metodo, ruta, datos=None):
    credencial = base64.b64encode(f"{_clave()}:".encode()).decode()
    cuerpo = urllib.parse.urlencode(datos).encode() if datos else None
    peticion = urllib.request.Request(
        URL_STRIPE + ruta,
        data=cuerpo,
        headers={
            "Authorization": f"Basic {credencial}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method=metodo,
    )
    try:
        with urllib.request.urlopen(peticion, timeout=20) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detalle = error.read().decode("utf-8", errors="replace")[:500]
        raise ErrorPago(f"Stripe respondió con el código {error.code}: {detalle}") from error
    except urllib.error.URLError as error:
        raise ErrorPago(f"No se pudo conectar con Stripe: {error.reason}") from error


def crear_sesion_de_pago(pago_id, descripcion, precio, cantidad, url_frontend):
    """Crea la página de pago de Stripe y devuelve (id_de_sesion, url_para_redirigir)."""
    datos = {
        "mode": "payment",
        "client_reference_id": str(pago_id),
        "metadata[pago_id]": str(pago_id),
        "line_items[0][quantity]": str(cantidad),
        "line_items[0][price_data][currency]": "cop",
        # Stripe maneja los pesos con dos decimales: $61.000 se envía como 6100000
        "line_items[0][price_data][unit_amount]": str(precio * 100),
        "line_items[0][price_data][product_data][name]": descripcion,
        "success_url": f"{url_frontend}/?pago=exito&session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{url_frontend}/?pago=cancelado&pago_id={pago_id}",
        "expires_at": str(int(time.time()) + MINUTOS_SESION * 60 + 60),
    }
    sesion = _peticion("POST", "/checkout/sessions", datos)
    return sesion["id"], sesion["url"]


def consultar_sesion(session_id):
    """Devuelve (pago_id, pagado) de una sesión de Stripe."""
    if not session_id.startswith("cs_"):
        raise ErrorPago("El identificador de la sesión de pago no es válido")
    sesion = _peticion("GET", "/checkout/sessions/" + urllib.parse.quote(session_id))
    pago_id = int(sesion.get("metadata", {}).get("pago_id", 0))
    return pago_id, sesion.get("payment_status") == "paid"
