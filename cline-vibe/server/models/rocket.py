"""Rocket schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
import uuid
from db_models.enums import RocketState, JobStatus


class RocketCreate(BaseModel):
    """Rocket creation schema."""
    name: str


class RocketUpdate(BaseModel):
    """Rocket update schema."""
    name: Optional[str] = None
    state: Optional[RocketState] = None


class RocketResponse(BaseModel):
    """Rocket response schema."""
    id: uuid.UUID
    state: RocketState
    name: str
    
    class Config:
        from_attributes = True


class FlightBase(BaseModel):
    """Shared Flight attributes."""
    rocket_id: uuid.UUID
    state: RocketState
    source: str
    destination: str
    location: Optional[str] = None  # serialized JSON
    estimated_time: int  # seconds
    status: JobStatus
    process_id: Optional[str] = None
    user_id: uuid.UUID
    message: Optional[str] = None


class FlightCreate(FlightBase):
    """Flight creation payload."""
    pass


class UpdateFlight(BaseModel):
    """Flight update payload."""
    id: Optional[uuid.UUID] = None
    rocket_id: Optional[uuid.UUID] = None
    state: Optional[RocketState] = None
    source: Optional[str] = None
    destination: Optional[str] = None
    location: Optional[str] = None
    estimated_time: Optional[int] = None
    status: Optional[JobStatus] = None
    process_id: Optional[str] = None
    user_id: Optional[uuid.UUID] = None
    message: Optional[str] = None


class Flight(FlightBase):
    """Flight response schema."""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FlightHistoryResponse(BaseModel):
    """Flight history response schema."""
    history: List[Flight]
