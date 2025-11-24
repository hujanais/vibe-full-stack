"""RocketJob schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
import uuid
from models.enums import RocketState, JobStatus


class RocketJobCreate(BaseModel):
    """RocketJob creation schema."""
    source: str
    destination: str
    estimated_time: int  # seconds


class RocketJobUpdate(BaseModel):
    """RocketJob update schema."""
    state: Optional[RocketState] = None
    location: Optional[str] = None
    estimated_time: Optional[int] = None
    status: Optional[JobStatus] = None


class RocketJobResponse(BaseModel):
    """RocketJob response schema."""
    id: uuid.UUID
    state: RocketState
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
    timestamp: datetime
    state: RocketState
    message: Optional[str]
    
    class Config:
        from_attributes = True


class RocketJobHistoryResponse(BaseModel):
    """Job history response schema."""
    history: List[JobHistoryEntry]


