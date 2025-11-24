"""Rocket job management endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from core.database import get_db
from api.dependencies import get_current_user
from models.user import User
from models.rocket_job import RocketJob
from models.job_history import JobHistory
from models.enums import RocketState, JobStatus
from schemas.rocket_job import (
    RocketJobCreate,
    RocketJobUpdate,
    RocketJobResponse,
    RocketJobHistoryResponse,
    JobHistoryEntry
)
from services.airflow_service import airflow_service
from datetime import datetime

router = APIRouter(prefix="/api/v1/job", tags=["jobs"])


@router.post("", response_model=RocketJobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: RocketJobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new rocket job and trigger Airflow DAG."""
    # Create rocket job
    new_job = RocketJob(
        state=RocketState.PREPARING,
        source=job_data.source,
        destination=job_data.destination,
        location=job_data.source,  # Start at source
        estimated_time=job_data.estimated_time,
        status=JobStatus.PENDING,
        user_id=current_user.id
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    # Create initial history entry
    history_entry = JobHistory(
        job_id=new_job.id,
        state=RocketState.PREPARING,
        message=f"Job created: {job_data.source} -> {job_data.destination}"
    )
    db.add(history_entry)
    
    # Trigger Airflow DAG
    dag_id = "rocket_flight_dag"  # This should match your Airflow DAG ID
    dag_run_id = airflow_service.trigger_dag(
        dag_id=dag_id,
        job_id=new_job.id,
        conf={"job_id": str(new_job.id)}
    )
    
    if dag_run_id:
        new_job.airflow_dag_run_id = dag_run_id
        new_job.status = JobStatus.RUNNING
    
    db.commit()
    db.refresh(new_job)
    
    return new_job


@router.get("", response_model=List[RocketJobResponse])
async def get_jobs(
    state: Optional[RocketState] = Query(None, description="Filter by rocket state"),
    status_filter: Optional[JobStatus] = Query(None, alias="status", description="Filter by job status"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all jobs with optional filters."""
    query = db.query(RocketJob)
    
    # Apply filters
    if state:
        query = query.filter(RocketJob.state == state)
    if status_filter:
        query = query.filter(RocketJob.status == status_filter)
    if user_id:
        query = query.filter(RocketJob.user_id == user_id)
    
    jobs = query.order_by(RocketJob.created_at.desc()).all()
    return jobs


@router.get("/{job_id}", response_model=RocketJobResponse)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get job by ID."""
    job = db.query(RocketJob).filter(RocketJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete job by ID."""
    job = db.query(RocketJob).filter(RocketJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    db.delete(job)
    db.commit()
    return None


@router.patch("/{job_id}", response_model=RocketJobResponse)
async def update_job(
    job_id: str,
    job_update: RocketJobUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update job details or state."""
    job = db.query(RocketJob).filter(RocketJob.id == job_id).first()
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
            job_id=job.id,
            state=update_data["state"],
            message=f"State updated to {update_data['state']}"
        )
        db.add(history_entry)
    
    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    
    return job


@router.post("/{job_id}/trigger")
async def trigger_job_dag(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually trigger or retrigger the Airflow DAG for the job."""
    job = db.query(RocketJob).filter(RocketJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    dag_id = "rocket_flight_dag"
    dag_run_id = airflow_service.trigger_dag(
        dag_id=dag_id,
        job_id=job.id,
        conf={"job_id": str(job.id)}
    )
    
    if dag_run_id:
        job.airflow_dag_run_id = dag_run_id
        job.status = JobStatus.RUNNING
        db.commit()
        return {"dag_run_id": dag_run_id, "message": "DAG triggered successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger DAG"
        )


@router.get("/{job_id}/history", response_model=RocketJobHistoryResponse)
async def get_job_history(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get job state transition history/log."""
    job = db.query(RocketJob).filter(RocketJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    history = db.query(JobHistory).filter(JobHistory.job_id == job_id).order_by(JobHistory.timestamp).all()
    return RocketJobHistoryResponse(history=history)


