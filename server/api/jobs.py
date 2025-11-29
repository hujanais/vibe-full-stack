"""Rocket job management endpoints."""
from typing import List, Optional
from uuid import UUID, uuid4
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from core.database import get_db
from api.dependencies import get_current_user
from models.user import User
from models.rocket_job import Rocket
from models.job_history import JobHistory
from models.enums import RocketState, JobStatus
from schemas.rocket_job import (
    RocketCreate,
    RocketUpdate,
    RocketResponse,
    RocketHistoryResponse,
    JobHistoryEntry
)
from services.airflow_service2 import airflow_service2
from datetime import datetime

router = APIRouter(prefix="/api/v1/job", tags=["jobs"])
rocket_router = APIRouter(prefix="/api/v1/rocket", tags=["rockets"])
flight_router = APIRouter(prefix="/api/v1/flight", tags=["flight"])


@router.post("", response_model=RocketResponse, status_code=status.HTTP_201_CREATED)
async def create_rocket(
    job_data: RocketCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new rocket."""
    # Create new rocket
    new_job = Rocket(
        state=RocketState.PREPARING,
        name=job_data.name,
        source='earth',
        destination='mars',
        location='earth',  # Start at source
        estimated_time=999999,
        status=JobStatus.IDLE,
        user_id=current_user.id
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    # Create initial history entry
    history_entry = JobHistory(
        rocket_id=new_job.id,
        state=RocketState.PREPARING,
        message=f"Job created: {new_job.source} -> {new_job.destination}"
    )
    db.add(history_entry)
    db.commit()
    
    # Trigger rocket process to start state transitions
    airflow_service2.start_rocket_process(
        rocket_id=str(new_job.id),
        source=new_job.source,
        destination=new_job.destination,
        db=db
    )
    
    db.refresh(new_job)
    return new_job


@router.get("", response_model=List[RocketResponse])
async def get_rockets(
    state: Optional[RocketState] = Query(None, description="Filter by rocket state"),
    status_filter: Optional[JobStatus] = Query(None, alias="status", description="Filter by job status"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all rockets with optional filters."""
    query = db.query(Rocket)
    
    # Apply filters
    if state:
        query = query.filter(Rocket.state == state)
    if status_filter:
        query = query.filter(Rocket.status == status_filter)
    if user_id:
        query = query.filter(Rocket.user_id == user_id)
    
    jobs = query.order_by(Rocket.created_at.desc()).all()
    return jobs


@rocket_router.get("/{rocket_id}", response_model=RocketResponse)
async def get_rocket(
    rocket_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get rocket by ID."""
    job = db.query(Rocket).filter(Rocket.id == rocket_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rocket not found"
        )
    return job


@rocket_router.delete("/{rocket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rocket(
    rocket_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete rocket by ID."""
    job = db.query(Rocket).filter(Rocket.id == rocket_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rocket not found"
        )
    
    # Stop the rocket process if it's running
    airflow_service2.stop_rocket_process(rocket_id)
    
    db.delete(job)
    db.commit()
    return None


@router.patch("/{rocket_id}", response_model=RocketResponse)
async def update_job(
    rocket_id: str,
    job_update: RocketUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update job details or state."""
    job = db.query(Rocket).filter(Rocket.id == rocket_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Update fields
    update_data = job_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)
    
    # Create history entry if state changed
    if "state" in update_data:
        history_entry = JobHistory(
            rocket_id=job.id,
            state=update_data["state"],
            message=f"State updated to {update_data['state']}"
        )
        db.add(history_entry)
    
    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    
    return job




@flight_router.get("/history/{rocket_id}", response_model=RocketHistoryResponse)
async def get_flight_history(
    rocket_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the flight history for a given flightID."""
    job = db.query(Rocket).filter(Rocket.id == rocket_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rocket not found"
        )
    
    history = db.query(JobHistory).filter(JobHistory.rocket_id == rocket_id).order_by(JobHistory.timestamp).all()
    return RocketHistoryResponse(history=history)


