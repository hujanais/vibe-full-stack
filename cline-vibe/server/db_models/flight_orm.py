"""Flight ORM model for flight history."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.database import Base
from db_models.enums import RocketState, JobStatus


class Flight(Base):
    """Flight model representing flight history of a Rocket."""
    
    __tablename__ = "flights"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rocket_id = Column(UUID(as_uuid=True), ForeignKey("rockets.id"), nullable=False, index=True)
    state = Column(SQLEnum(RocketState), nullable=False)
    source = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    location = Column(String, nullable=True)  # JSON string
    estimated_time = Column(Integer, nullable=False)  # seconds
    status = Column(SQLEnum(JobStatus), nullable=False)
    process_id = Column(String, nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    message = Column(String, nullable=True)
    
    # Relationships
    rocket = relationship("Rocket", backref="flights")
    user = relationship("User", backref="flights")

