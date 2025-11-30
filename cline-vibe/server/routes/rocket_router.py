"""Rocket endpoints."""
from typing import Any, List
from fastapi import APIRouter, Depends, status, Path, Body
from sqlalchemy.orm import Session
from core.database import get_db
from api.flight_api import flight_api
from api.rocket_api import rocket_api
from models.rocket import RocketCreate, RocketResponse, UpdateFlight

rocket_router = APIRouter(prefix="/api/v1/rocket", tags=["rockets"])
flight_router = APIRouter(prefix="/api/v1/flights", tags=["flights"])


@rocket_router.get("", response_model=List[RocketResponse])
async def get_all_rockets(db: Session = Depends(get_db)):
    """Get all rockets."""
    return rocket_api.get_rocket(None)


@rocket_router.get("/{rocket_id}", response_model=RocketResponse)
async def get_rocket(
    rocket_id: str = Path(..., description="Rocket ID"),
    db: Session = Depends(get_db)
):
    """Get rocket by ID."""
    return rocket_api.get_rocket(rocket_id)


@rocket_router.post("", response_model=RocketResponse, status_code=status.HTTP_201_CREATED)
async def create_rocket(
    rocket_data: RocketCreate,
    db: Session = Depends(get_db)
):
    """Create a new rocket."""
    return rocket_api.create_rocket(rocket_data.name)


@rocket_router.delete("/{rocket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rocket(
    rocket_id: str = Path(..., description="Rocket ID to delete"),
    db: Session = Depends(get_db)
):
    """Delete rocket and all associated flights in flights table."""
    rocket_api.delete_rocket(rocket_id)
    return None


@flight_router.get("")
async def get_all_flights(db: Session = Depends(get_db)):
    """Get all flights in flights table."""
    return flight_api.get_flights(None)


@flight_router.get("/{rocket_id}")
async def get_flights(
    rocket_id: str = Path(..., description="Rocket ID"),
    db: Session = Depends(get_db)
):
    """Get flights by rocket_id."""
    return flight_api.get_flights(rocket_id)

@flight_router.patch("/trigger_flights/{flight_id}")
async def trigger_flight(
    flight_id: str = Path(..., description="Flight ID to update"),
    flight_data: dict = Body(..., description="Flight update data"),
    db: Session = Depends(get_db)
):
    """Trigger a new flight."""
     # Add flight_id to flight_data if not present
    if "id" not in flight_data and "flight_id" not in flight_data:
        flight_data["flight_id"] = flight_id
    
    flight = UpdateFlight(flight_data)
    flight_api.trigger_flight(flight)


@flight_router.patch("/{flight_id}")
async def update_flight(
    flight_id: str = Path(..., description="Flight ID to update"),
    flight_data: dict = Body(..., description="Flight update data"),
    db: Session = Depends(get_db)
):
    """Update the flight info."""
    # Add flight_id to flight_data if not present
    if "id" not in flight_data and "flight_id" not in flight_data:
        flight_data["flight_id"] = flight_id
    
    flight = UpdateFlight(flight_data)
    return flight_api.update_flight(flight)
