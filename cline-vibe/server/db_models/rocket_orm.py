"""Rocket ORM model."""
import uuid
from sqlalchemy import Column, String, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base
from db_models.enums import RocketState


class Rocket(Base):
    """Rocket model representing a rocket in the inventory."""
    
    __tablename__ = "rockets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    state = Column(SQLEnum(RocketState), nullable=False, default=RocketState.PREPARING)
    name = Column(String, unique=True, nullable=False, index=True)

