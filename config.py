"""Configuración del backend.

Todos los valores salen de variables de entorno (archivo .env en local, panel
de Render en producción). Este es el único archivo que lee el entorno: el resto
del código importa de aquí, así nada queda quemado en el código.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# Base de datos (Neon PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL")

# Inteligencia artificial (Gemini)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_API_URL = os.getenv(
    "GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

# Secreto para firmar los tokens de sesión
TOKEN_SECRET = os.getenv("TOKEN_SECRET")

# Pagos (Stripe en modo prueba)
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_API_URL = os.getenv("STRIPE_API_URL", "https://api.stripe.com/v1")
STRIPE_CURRENCY = os.getenv("STRIPE_CURRENCY", "cop")

# A dónde vuelve el usuario después de pagar, y quién puede llamar a la API
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://terminapp-frontend.vercel.app").rstrip("/")
ALLOWED_ORIGINS_PATTERN = os.getenv(
    "ALLOWED_ORIGINS_PATTERN", r"https://terminapp-frontend.*\.vercel\.app|http://localhost:5173"
)

# Cuenta de prueba para el profesor (solo se crea si están las dos variables)
TEST_ACCOUNT_NAME = os.getenv("TEST_ACCOUNT_NAME", "Profesor")
TEST_ACCOUNT_EMAIL = os.getenv("TEST_ACCOUNT_EMAIL")
TEST_ACCOUNT_PASSWORD = os.getenv("TEST_ACCOUNT_PASSWORD")
