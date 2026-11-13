"""Ticket purchase and history routes."""

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

import config
from payments.stripe_client import (
    PaymentError, create_checkout_session, expire_checkout_session, get_checkout_session, read_webhook_event,
    refund_session,
)
from routes.dependencies import get_current_user, limit_payments, limit_purchases, require_date
from services import purchases
from services.dates import COLOMBIA_TIMEZONE
from services.validation import DEFAULT_DOCUMENT_TYPE, DOCUMENT_MAX_LENGTH, NAME_MAX_LENGTH

router = APIRouter(tags=["Purchase"])


def to_http_error(error):
    return HTTPException(status_code=error.status_code, detail=error.message)


class PassengerData(BaseModel):
    seat: int = Field(..., ge=1, le=100)
    name: str = Field(..., max_length=NAME_MAX_LENGTH * 2)
    document_type: str = Field(DEFAULT_DOCUMENT_TYPE, max_length=2, description="CC, TI, CE or PA")
    document: str = Field(..., max_length=DOCUMENT_MAX_LENGTH * 2)
    checked_bags: int = Field(0, ge=0, le=purchases.MAX_CHECKED_BAGS, description="Bags in the hold, 0 to 2")


class PurchaseRequest(BaseModel):
    schedule_id: int
    date: str = Field(..., max_length=10)
    # one passenger per seat; each company sets its own maximum (up to 10)
    passengers: list[PassengerData] = Field(..., min_length=1, max_length=purchases.SEATS_PER_PURCHASE_LIMIT)
    contact_phone: str | None = Field(None, max_length=20, description="Colombian mobile, for example 3001234567")


@router.get("/schedules/{schedule_id}/seats", summary="Seat map of a departure on a date")
def seat_map(schedule_id: int, date: str):
    """Seat map of a departure on a date (YYYY-MM-DD)."""
    try:
        return purchases.get_seat_map(schedule_id, require_date(date))
    except purchases.PurchaseError as error:
        raise to_http_error(error)


@router.post(
    "/purchases",
    status_code=201,
    summary="🔒 Holds the seats for 15 minutes",
    dependencies=[Depends(limit_purchases)],
)
def create_purchase(request: PurchaseRequest, user: dict = Depends(get_current_user)):
    """🔒 Holds the seats (one passenger per seat) for the minutes the bus company chose.
    If the user already had an unpaid purchase for this same trip, it is cancelled and
    replaced by this one."""
    try:
        result = purchases.reserve_seats(
            user["id"],
            request.schedule_id,
            require_date(request.date),
            [passenger.model_dump() for passenger in request.passengers],
            request.contact_phone,
        )
    except purchases.PurchaseError as error:
        raise to_http_error(error)
    for session_id in result.pop("replaced_stripe_sessions"):
        expire_checkout_session(session_id)
    return result


LOST_SEATS_MESSAGE = (
    "Tu pago llegó cuando la reserva ya había vencido y los asientos se vendieron a otra persona. "
    "Te devolvimos el dinero completo."
)
PAYMENT_TIME_OVER_MESSAGE = "Se acabó el tiempo para pagar esta compra. Vuelve a elegir tus asientos."


def utc_from_timestamp(seconds):
    return datetime.fromtimestamp(seconds, tz=timezone.utc)


def confirm_or_refund(payment_id, user_id=None):
    """Confirms a payment Stripe already approved. If the seats were sold meanwhile,
    refunds the customer and raises a 409 that explains it."""
    try:
        return purchases.confirm_payment(payment_id, user_id)
    except purchases.SeatsLostError as error:
        refund_session(error.stripe_session_id)
        purchases.mark_as_refunded(payment_id)
        raise HTTPException(status_code=409, detail=LOST_SEATS_MESSAGE)


@router.post(
    "/purchases/{payment_id}/pay",
    summary="🔒 Prepares the embedded Stripe payment",
    dependencies=[Depends(limit_payments)],
)
def pay(payment_id: int, user: dict = Depends(get_current_user)):
    """🔒 Returns the client_secret used to draw the Stripe payment inside the page.
    If the purchase already has an open payment, it is reused instead of creating another.
    The purchase keeps the deadline set when the seats were reserved; when it passes,
    the Stripe session is closed so it can no longer be paid."""
    try:
        details = purchases.get_payment_details(user["id"], payment_id)
        if details["stripe_session_id"]:
            previous = get_checkout_session(details["stripe_session_id"])
            if previous["paid"]:
                return {"status": confirm_or_refund(payment_id, user["id"]), "client_secret": None}
            if previous["is_open"] and previous["client_secret"]:
                return {
                    "status": details["status"],
                    "client_secret": previous["client_secret"],
                    "ui_mode": previous["ui_mode"],
                    "expires_at": details["expires_at"],
                }
            # the Stripe session closed without payment: the purchase cannot be paid any more
            raise HTTPException(status_code=409, detail=PAYMENT_TIME_OVER_MESSAGE)
        session = create_checkout_session(
            payment_id, details["description"], details["unit_price"], details["quantity"], config.FRONTEND_URL
        )
        expires_at = utc_from_timestamp(session["expires_at"])
        status = purchases.mark_as_paying(user["id"], payment_id, session["session_id"], expires_at)
    except purchases.PurchaseError as error:
        raise to_http_error(error)
    except PaymentError as error:
        print("Stripe error:", error)
        raise HTTPException(status_code=502, detail="No se pudo abrir el pago. Intenta de nuevo.")
    return {
        "status": status,
        "client_secret": session["client_secret"],
        "ui_mode": session["ui_mode"],
        "expires_at": details["expires_at"] or expires_at.astimezone(COLOMBIA_TIMEZONE).isoformat(),
    }


@router.get("/purchases/confirm", summary="🔒 Confirms with Stripe that the payment went through")
def confirm(session_id: str, user: dict = Depends(get_current_user)):
    """🔒 After payment, asks Stripe whether it went through and confirms the tickets.
    We never trust that the user came back to the page: we ask Stripe."""
    try:
        session = get_checkout_session(session_id)
        if not session["paid"]:
            raise HTTPException(status_code=402, detail="El pago todavía no aparece como aprobado")
        status = confirm_or_refund(session["payment_id"], user["id"])
    except purchases.PurchaseError as error:
        raise to_http_error(error)
    except PaymentError as error:
        print("Stripe error:", error)
        raise HTTPException(status_code=502, detail="No se pudo confirmar el pago con Stripe. Intenta de nuevo.")
    return {"payment_id": session["payment_id"], "status": status}


@router.post("/stripe/webhook", summary="Stripe tells the backend that a payment was completed")
async def stripe_webhook(request: Request):
    """Stripe calls this route when a payment finishes, even if the user closed the page.
    The signature is checked with STRIPE_WEBHOOK_SECRET, so nobody else can fake a payment."""
    payload = await request.body()
    try:
        event = read_webhook_event(payload, request.headers.get("stripe-signature"))
    except PaymentError as error:
        print("Rejected webhook:", error)
        raise HTTPException(status_code=400, detail="Invalid webhook")

    session = event.get("data", {}).get("object", {})
    completed = event.get("type") in ("checkout.session.completed", "checkout.session.async_payment_succeeded")
    if completed and session.get("payment_status") == "paid":
        payment_id = int(session.get("metadata", {}).get("payment_id", 0))
        try:
            confirm_or_refund(payment_id)
        except (purchases.PurchaseError, HTTPException) as error:
            print(f"Webhook for payment {payment_id}:", getattr(error, "detail", error))
    return {"received": True}


@router.post("/purchases/{payment_id}/cancel", summary="🔒 Cancels an unpaid purchase")
def cancel(payment_id: int, user: dict = Depends(get_current_user)):
    """🔒 Cancels a purchase that has not been paid yet and frees its seats."""
    try:
        status, stripe_session_id = purchases.cancel_purchase(user["id"], payment_id)
    except purchases.PurchaseError as error:
        raise to_http_error(error)
    if stripe_session_id:
        expire_checkout_session(stripe_session_id)
    return {"payment_id": payment_id, "status": status}


@router.get("/my-tickets", summary="🔒 The user's purchase history")
def my_tickets(order: Literal["newest", "oldest"] = purchases.NEWEST_FIRST, user: dict = Depends(get_current_user)):
    """🔒 The user's purchase history (doubly linked list)."""
    return purchases.get_my_tickets(user["id"], order)
