"""Rutas de búsqueda de salidas."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from ai.tools import ORIGIN, list_destinations, parse_time_to_minutes
from routes.dependencies import require_travel_date
from services.search import SORT_BY_TIME, search_departures

PLACE_MAX_LENGTH = 40

router = APIRouter(tags=["Búsqueda"])


@router.get("/search", summary="Busca salidas de un día desde una hora, con cupos libres reales")
def search(
    destination: str = Query(..., max_length=PLACE_MAX_LENGTH),
    origin: str = Query(ORIGIN, max_length=PLACE_MAX_LENGTH),
    from_time: str = Query("00:00", max_length=5),
    sort_by: Literal["time", "price"] = SORT_BY_TIME,
    date: str = Query("", max_length=10),
):
    travel_date = require_travel_date(date)
    try:
        start_minutes = parse_time_to_minutes(from_time)
    except ValueError:
        raise HTTPException(status_code=400, detail="La hora debe tener el formato HH:MM")

    departures = search_departures(origin, destination, start_minutes, sort_by, travel_date)
    if departures is None:
        raise HTTPException(status_code=404, detail="No conocemos ese origen o ese destino")

    destination_name = departures[0]["destination"] if departures else destination
    return {
        "origin": origin,
        "destination": destination_name,
        "date": travel_date.isoformat(),
        "count": len(departures),
        "departures": departures,
    }


@router.get("/destinations", summary="Lista los destinos con rutas desde Pasto")
def destinations():
    return list_destinations()
