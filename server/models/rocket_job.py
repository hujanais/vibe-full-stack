"""Rocket model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.database import Base
from .enums import RocketState, JobStatus


class Rocket(Base):
    """Rocket model representing a rocket flight job."""
    
    __tablename__ = "rocket_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    state = Column(SQLEnum(RocketState), nullable=False, default=RocketState.PREPARING)
    name = Column(String, nullable=False)
    source = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    location = Column(String, nullable=True)
    estimated_time = Column(Integer, nullable=False)  # seconds
    status = Column(SQLEnum(JobStatus), nullable=False, default=JobStatus.IDLE)
    airflow_dag_run_id = Column(String, nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="jobs")
    history = relationship("JobHistory", back_populates="job", cascade="all, delete-orphan")


