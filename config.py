"""Backend configuration.

Every value comes from environment variables (.env file locally, the Render
dashboard in production). This is the only file that reads the environment:
the rest of the code imports from here, so nothing is hardcoded.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# Database (Neon PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL")

# Artificial intelligence (Gemini)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_API_URL = os.getenv(
    "GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

# Secret used to sign session tokens
TOKEN_SECRET = os.getenv("TOKEN_SECRET")

# Payments (Stripe in test mode)
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_API_URL = os.getenv("STRIPE_API_URL", "https://api.stripe.com/v1")
STRIPE_CURRENCY = os.getenv("STRIPE_CURRENCY", "cop")
# Signing secret of the Stripe webhook (whsec_...). Without it the webhook route is disabled.
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Where the user returns after paying, and who may call the API
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://terminapp-frontend.vercel.app").rstrip("/")
ALLOWED_ORIGINS_PATTERN = os.getenv(
    "ALLOWED_ORIGINS_PATTERN", r"https://terminapp-frontend\.vercel\.app|http://localhost:5173"
)

# Test account for the professor (only created when both variables are set). It is an admin,
# so with this one login the professor can try the whole app, including the admin panel.
TEST_ACCOUNT_NAME = os.getenv("TEST_ACCOUNT_NAME", "Profesor")
TEST_ACCOUNT_EMAIL = os.getenv("TEST_ACCOUNT_EMAIL")
TEST_ACCOUNT_PASSWORD = os.getenv("TEST_ACCOUNT_PASSWORD")


def _test_email(prefix):
    """"profe@terminapp.co" -> "empresa.profe@terminapp.co": the other test accounts reuse the
    professor's email with a prefix, so no new variables are needed in Render or Vercel."""
    return f"{prefix}.{TEST_ACCOUNT_EMAIL}" if TEST_ACCOUNT_EMAIL else None


# The other two roles, with the same password as the professor's account. Their emails
# can be changed with these variables; the company account manages TEST_COMPANY_NAME.
TEST_COMPANY_ACCOUNT_EMAIL = os.getenv("TEST_COMPANY_ACCOUNT_EMAIL") or _test_email("empresa")
TEST_COMPANY_NAME = os.getenv("TEST_COMPANY_NAME", "EXPRESO BOLIVARIANO")
TEST_TRAVELER_ACCOUNT_EMAIL = os.getenv("TEST_TRAVELER_ACCOUNT_EMAIL") or _test_email("viajero")

# Optional extra admin account (only created when both variables are set).
ADMIN_ACCOUNT_NAME = os.getenv("ADMIN_ACCOUNT_NAME", "Administrador")
ADMIN_ACCOUNT_EMAIL = os.getenv("ADMIN_ACCOUNT_EMAIL")
ADMIN_ACCOUNT_PASSWORD = os.getenv("ADMIN_ACCOUNT_PASSWORD")
