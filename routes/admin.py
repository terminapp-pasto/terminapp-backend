"""Admin panel routes: the terminal admin manages everything; a company user manages
only its own company. Changes use POST because the API only allows GET and POST."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ai.admin_assistant import generate_admin_reply
from ai.gemini import AIError
from routes.chat import ChatRequest
from routes.dependencies import company_scope, limit_chat, require_admin, require_date, require_staff
from services import admin
from payments.stripe_client import PaymentError, expire_checkout_session, refund_session
from services import settings
from services.catalog import list_document_types
from services.dates import today_in_colombia

router = APIRouter(tags=["Admin"])

NAME_FIELD = Field(..., max_length=80)


def to_http_error(error):
    return HTTPException(status_code=error.status_code, detail=error.message)


def run(action, *args, **kwargs):
    """Runs a service function and turns its AdminError into an HTTP answer."""
    try:
        return action(*args, **kwargs)
    except admin.AdminError as error:
        raise to_http_error(error)


class CompanyRequest(BaseModel):
    name: str = NAME_FIELD
    max_seats_per_purchase: int = admin.MAX_SEATS_PER_PURCHASE
    reservation_minutes: int = admin.DEFAULT_RESERVATION_MINUTES


class CompanySettingsRequest(BaseModel):
    max_seats_per_purchase: int | None = None
    reservation_minutes: int | None = None


class BusRequest(BaseModel):
    company_id: int
    plate: str = Field(..., max_length=10)
    capacity: int


class RouteRequest(BaseModel):
    company_id: int
    destination: str = Field(..., max_length=60)
    duration_min: int


class DepartureRequest(BaseModel):
    route_id: int
    departure_time: str = Field(..., max_length=5)
    price: int
    bus_id: int


class DepartureChangeRequest(BaseModel):
    price: int | None = None
    bus_id: int | None = None
    active: bool | None = None
    departure_time: str | None = Field(None, max_length=5)


class PriceRequest(BaseModel):
    price: int


class DocumentTypeRequest(BaseModel):
    code: str = Field(..., max_length=2)
    name: str = NAME_FIELD
    min_length: int
    max_length: int
    allows_letters: bool = False


class ActiveRequest(BaseModel):
    active: bool


class RoleRequest(BaseModel):
    role: str = Field(..., max_length=10)
    company_id: int | None = None


# ---------------- Public ----------------

@router.get("/document-types", summary="Document types accepted for travel", tags=["Purchase"])
def document_types():
    return list_document_types()


# ---------------- Admin and companies ----------------

@router.get("/admin/companies", summary="🔒 Companies with their settings (a company only sees itself)")
def companies(user: dict = Depends(require_staff)):
    return admin.list_companies(company_scope(user))


@router.post("/admin/companies", status_code=201, summary="🔒 Admin: adds a bus company")
def create_company(request: CompanyRequest, _user: dict = Depends(require_admin)):
    return run(admin.create_company, request.name, request.max_seats_per_purchase, request.reservation_minutes)


@router.post("/admin/companies/{company_id}/settings", summary="🔒 Seats per purchase and minutes to pay")
def company_settings(company_id: int, request: CompanySettingsRequest, user: dict = Depends(require_staff)):
    return run(admin.update_company_settings, company_scope(user), company_id,
               request.max_seats_per_purchase, request.reservation_minutes)


@router.get("/admin/buses", summary="🔒 Buses and their capacity")
def buses(user: dict = Depends(require_staff)):
    return admin.list_buses(company_scope(user))


@router.post("/admin/buses", status_code=201, summary="🔒 Adds a bus and its seats")
def create_bus(request: BusRequest, user: dict = Depends(require_staff)):
    return run(admin.create_bus, company_scope(user), request.company_id, request.plate, request.capacity)


@router.get("/admin/destinations", summary="🔒 Every destination of the terminal")
def destinations(_user: dict = Depends(require_staff)):
    return admin.list_destinations()


@router.get("/admin/routes", summary="🔒 Routes with their departures, prices and buses")
def routes(user: dict = Depends(require_staff)):
    return admin.list_routes(company_scope(user))


@router.post("/admin/routes", status_code=201, summary="🔒 Adds a route from Pasto")
def create_route(request: RouteRequest, user: dict = Depends(require_staff)):
    return run(admin.create_route, company_scope(user), request.company_id, request.destination, request.duration_min)


@router.post("/admin/routes/{route_id}/price", summary="🔒 Same price for every departure of a route")
def route_price(route_id: int, request: PriceRequest, user: dict = Depends(require_staff)):
    return run(admin.set_route_price, company_scope(user), route_id, request.price)


@router.post("/admin/departures", status_code=201, summary="🔒 Adds a departure to a route")
def create_departure(request: DepartureRequest, user: dict = Depends(require_staff)):
    return run(admin.create_departure, company_scope(user), request.route_id, request.departure_time,
               request.price, request.bus_id)


@router.post("/admin/departures/{schedule_id}", summary="🔒 Changes a departure's price, bus or sale status")
def change_departure(schedule_id: int, request: DepartureChangeRequest, user: dict = Depends(require_staff)):
    """Price, bus, sale status and/or hour of a departure."""
    scope = company_scope(user)
    result = None
    if request.departure_time is not None:
        result = run(admin.change_departure_time, scope, schedule_id, request.departure_time)
    if request.price is not None or request.bus_id is not None or request.active is not None:
        result = run(admin.update_departure, scope, schedule_id, request.price, request.bus_id, request.active)
    if result is None:
        raise HTTPException(status_code=400, detail="No hay nada que cambiar")
    return result


@router.get("/admin/occupancy", summary="🔒 How full each bus is on a day")
def occupancy(date: str = Query("", max_length=10), user: dict = Depends(require_staff)):
    travel_date = require_date(date) if date else today_in_colombia()
    return admin.occupancy(company_scope(user), travel_date)


@router.post(
    "/admin/assistant",
    summary="🔒 AI assistant of the panel: looks things up and prepares changes to confirm",
    dependencies=[Depends(limit_chat)],
)
def assistant(request: ChatRequest, user: dict = Depends(require_staff)):
    """The AI never changes anything: it returns `actions` (summary, path and body). The panel
    shows each one with a Confirmar button, which calls that admin route."""
    try:
        return generate_admin_reply([m.model_dump() for m in request.messages], user, company_scope(user))
    except AIError as error:
        print("AI error:", error)
        raise HTTPException(
            status_code=502,
            detail="El asistente no está disponible en este momento. Intenta de nuevo en unos segundos.",
        )


# ---------------- Admin only ----------------

@router.get("/admin/document-types", summary="🔒 Admin: every document type, active or not")
def all_document_types(_user: dict = Depends(require_admin)):
    return admin.list_document_types()


@router.post("/admin/document-types", status_code=201, summary="🔒 Admin: adds a document type")
def create_document_type(request: DocumentTypeRequest, _user: dict = Depends(require_admin)):
    return run(admin.create_document_type, request.code, request.name, request.min_length, request.max_length,
               request.allows_letters)


@router.post("/admin/document-types/{code}/active", summary="🔒 Admin: turns a document type on or off")
def document_type_active(code: str, request: ActiveRequest, _user: dict = Depends(require_admin)):
    return run(admin.set_document_type_active, code.upper()[:2], request.active)


@router.get("/admin/users", summary="🔒 Admin: finds users by name or email")
def users(q: str = Query("", max_length=100), _user: dict = Depends(require_admin)):
    return admin.find_users(q)


@router.post("/admin/users/{user_id}/role", summary="🔒 Admin: makes a user a traveller, a company or an admin")
def user_role(user_id: int, request: RoleRequest, user: dict = Depends(require_admin)):
    return run(admin.set_user_role, user["id"], user_id, request.role, request.company_id)



# ---------------- Editing what already exists ----------------

class NameRequest(BaseModel):
    name: str = NAME_FIELD


class BusChangeRequest(BaseModel):
    plate: str | None = Field(None, max_length=10)
    capacity: int | None = None


class RouteChangeRequest(BaseModel):
    duration_min: int


class DocumentTypeChangeRequest(BaseModel):
    name: str | None = Field(None, max_length=80)
    min_length: int | None = None
    max_length: int | None = None
    allows_letters: bool | None = None


@router.post("/admin/companies/{company_id}", summary="🔒 Admin: renames a company")
def rename_company(company_id: int, request: NameRequest, _user: dict = Depends(require_admin)):
    return run(admin.rename_company, company_id, request.name)


@router.post("/admin/destinations/{destination_id}", summary="🔒 Admin: renames a town everywhere")
def rename_destination(destination_id: int, request: NameRequest, _user: dict = Depends(require_admin)):
    return run(admin.rename_destination, destination_id, request.name)


@router.post("/admin/buses/{bus_id}", summary="🔒 Changes a bus's plate or capacity")
def change_bus(bus_id: int, request: BusChangeRequest, user: dict = Depends(require_staff)):
    return run(admin.update_bus, company_scope(user), bus_id, request.plate, request.capacity)


@router.post("/admin/routes/{route_id}", summary="🔒 Changes how long a route takes")
def change_route(route_id: int, request: RouteChangeRequest, user: dict = Depends(require_staff)):
    return run(admin.update_route, company_scope(user), route_id, request.duration_min)


@router.post("/admin/document-types/{code}", summary="🔒 Admin: edits a document type")
def change_document_type(code: str, request: DocumentTypeChangeRequest, _user: dict = Depends(require_admin)):
    return run(admin.update_document_type, code.upper()[:2], request.name, request.min_length, request.max_length,
               request.allows_letters)


# ---------------- Texts and general rules ----------------

@router.get("/settings", summary="Texts and rules the admin set (home page, footer, notice, sales window)",
            tags=["System"])
def public_settings():
    return settings.public_settings()


@router.get("/admin/settings", summary="🔒 Admin: every text and general rule, with its limits")
def all_settings(_user: dict = Depends(require_admin)):
    return settings.describe_settings()


@router.post("/admin/settings", summary="🔒 Admin: changes texts and general rules ({key: value})")
def change_settings(request: dict[str, str | int], _user: dict = Depends(require_admin)):
    try:
        return settings.update_settings(request)
    except settings.SettingError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)


# ---------------- Purchases ----------------

@router.get("/admin/purchases", summary="🔒 Finds purchases by booking code, email, name or document")
def purchases_list(q: str = Query("", max_length=100), date: str = Query("", max_length=10),
                   user: dict = Depends(require_staff)):
    travel_date = require_date(date) if date else None
    return admin.find_purchases(company_scope(user), q, travel_date)


@router.post("/admin/purchases/{payment_id}/cancel", summary="🔒 Cancels an unpaid purchase and frees its seats")
def purchase_cancel(payment_id: int, user: dict = Depends(require_staff)):
    stripe_session_id = run(admin.cancel_purchase_as_staff, company_scope(user), payment_id)
    if stripe_session_id:
        expire_checkout_session(stripe_session_id)
    return {"payment_id": payment_id, "status": "CANCELLED"}


@router.post("/admin/purchases/{payment_id}/refund", summary="🔒 Gives the money of a paid purchase back")
def purchase_refund(payment_id: int, user: dict = Depends(require_staff)):
    try:
        return run(admin.refund_purchase_as_staff, company_scope(user), payment_id, refund_session)
    except PaymentError as error:
        print("Stripe error:", error)
        raise HTTPException(status_code=502, detail="Stripe no pudo hacer la devolución. Intenta de nuevo.")
