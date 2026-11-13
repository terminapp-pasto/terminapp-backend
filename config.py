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

# Test account for the professor (only created when both variables are set)
TEST_ACCOUNT_NAME = os.getenv("TEST_ACCOUNT_NAME", "Profesor")
TEST_ACCOUNT_EMAIL = os.getenv("TEST_ACCOUNT_EMAIL")
TEST_ACCOUNT_PASSWORD = os.getenv("TEST_ACCOUNT_PASSWORD")

# Terminal admin account (only created when both variables are set). Keep this
# password secret: unlike the test account, it can change prices and settings.
ADMIN_ACCOUNT_NAME = os.getenv("ADMIN_ACCOUNT_NAME", "Administrador")
ADMIN_ACCOUNT_EMAIL = os.getenv("ADMIN_ACCOUNT_EMAIL")
ADMIN_ACCOUNT_PASSWORD = os.getenv("ADMIN_ACCOUNT_PASSWORD")
