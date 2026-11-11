"""Ticket purchase and history routes."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import config
from payments.stripe_client import (
    PaymentError, create_checkout_session, expire_checkout_session, get_checkout_session,
)
from routes.dependencies import get_current_user, require_date
from services import purchases
from services.validation import DOCUMENT_MAX_LENGTH, NAME_MAX_LENGTH

router = APIRouter(tags=["Purchase"])


def to_http_error(error):
    return HTTPException(status_code=error.status_code, detail=error.message)


class PassengerData(BaseModel):
    seat: int = Field(..., ge=1, le=100)
    name: str = Field(..., max_length=NAME_MAX_LENGTH * 2)
    document: str = Field(..., max_length=DOCUMENT_MAX_LENGTH * 2)


class PurchaseRequest(BaseModel):
    schedule_id: int
    date: str = Field(..., max_length=10)
    # one passenger per seat, between 1 and 5
    passengers: list[PassengerData] = Field(..., min_length=1, max_length=purchases.MAX_SEATS_PER_PURCHASE)


@router.get("/schedules/{schedule_id}/seats", summary="Seat map of a departure on a date")
def seat_map(schedule_id: int, date: str):
    """Seat map of a departure on a date (YYYY-MM-DD)."""
    try:
        return purchases.get_seat_map(schedule_id, require_date(date))
    except purchases.PurchaseError as error:
        raise to_http_error(error)


@router.post("/purchases", status_code=201, summary="🔒 Holds the seats for 15 minutes")
def create_purchase(request: PurchaseRequest, user: dict = Depends(get_current_user)):
    """🔒 Holds the seats (one passenger per seat). If the user already had an unpaid
    purchase for this same trip, it is cancelled and replaced by this one."""
    try:
        result = purchases.reserve_seats(
            user["id"],
            request.schedule_id,
            require_date(request.date),
            [passenger.model_dump() for passenger in request.passengers],
        )
    except purchases.PurchaseError as error:
        raise to_http_error(error)
    for session_id in result.pop("replaced_stripe_sessions"):
        expire_checkout_session(session_id)
    return result


@router.post("/purchases/{payment_id}/pay", summary="🔒 Prepares the embedded Stripe payment")
def pay(payment_id: int, user: dict = Depends(get_current_user)):
    """🔒 Returns the client_secret used to draw the Stripe payment inside the page.
    If the purchase already has an open payment, it is reused instead of creating another."""
    try:
        details = purchases.get_payment_details(user["id"], payment_id)
        previous_session_id = details["stripe_session_id"]
        if previous_session_id:
            previous = get_checkout_session(previous_session_id)
            if previous["paid"]:
                return {"status": purchases.mark_as_paid(user["id"], payment_id), "client_secret": None}
            if previous["is_open"] and previous["client_secret"]:
                return {
                    "status": details["status"],
                    "client_secret": previous["client_secret"],
                    "ui_mode": previous["ui_mode"],
                }
        session = create_checkout_session(
            payment_id, details["description"], details["unit_price"], details["quantity"], config.FRONTEND_URL
        )
        status = purchases.mark_as_paying(user["id"], payment_id, session["session_id"])
    except purchases.PurchaseError as error:
        raise to_http_error(error)
    except PaymentError as error:
        print("Stripe error:", error)
        raise HTTPException(status_code=502, detail="No se pudo abrir el pago. Intenta de nuevo.")
    return {"status": status, "client_secret": session["client_secret"], "ui_mode": session["ui_mode"]}


@router.get("/purchases/confirm", summary="🔒 Confirms with Stripe that the payment went through")
def confirm(session_id: str, user: dict = Depends(get_current_user)):
    """🔒 After payment, asks Stripe whether it went through and confirms the tickets.
    We never trust that the user came back to the page: we ask Stripe."""
    try:
        session = get_checkout_session(session_id)
        if not session["paid"]:
            raise HTTPException(status_code=402, detail="El pago todavía no aparece como aprobado")
        status = purchases.mark_as_paid(user["id"], session["payment_id"])
    except purchases.PurchaseError as error:
        raise to_http_error(error)
    except PaymentError as error:
        print("Stripe error:", error)
        raise HTTPException(status_code=502, detail="No se pudo confirmar el pago con Stripe. Intenta de nuevo.")
    return {"payment_id": session["payment_id"], "status": status}


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
