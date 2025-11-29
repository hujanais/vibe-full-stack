"""JobHistory model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.database import Base
from .enums import RocketState


class JobHistory(Base):
    """JobHistory model for tracking state transitions."""
    
    __tablename__ = "job_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rocket_id = Column(UUID(as_uuid=True), ForeignKey("rocket_jobs.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    state = Column(SQLEnum(RocketState), nullable=False)
    message = Column(Text, nullable=True)
    
    # Relationships
    job = relationship("Rocket", back_populates="history")


