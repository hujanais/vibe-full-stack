"""Rocket schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
import uuid
from models.enums import RocketState, JobStatus


class RocketCreate(BaseModel):
    """Rocket creation schema."""
    name: str


class RocketUpdate(BaseModel):
    """Rocket update schema."""
    name: Optional[str] = None
    state: Optional[RocketState] = None
    location: Optional[str] = None
    estimated_time: Optional[int] = None
    status: Optional[JobStatus] = None


class RocketResponse(BaseModel):
    """Rocket response schema."""
    id: uuid.UUID
    state: RocketState
    name: str
    source: str
    destination: str
    location: Optional[str]
    estimated_time: int
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class JobHistoryEntry(BaseModel):
    """Job history entry schema."""
    id: uuid.UUID
    rocket_id: uuid.UUID
    timestamp: datetime
    state: RocketState
    message: Optional[str]
    
    class Config:
        from_attributes = True


class RocketHistoryResponse(BaseModel):
    """Job history response schema."""
    history: List[JobHistoryEntry]


