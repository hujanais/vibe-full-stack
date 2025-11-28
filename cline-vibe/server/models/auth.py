"""Authentication schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import uuid


class LoginRequest(BaseModel):
    """Login request schema."""
    username: str
    password: str


class Token(BaseModel):
    """Token response schema."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token data schema."""
    username: Optional[str] = None


class UserCreate(BaseModel):
    """User creation schema."""
    username: str
    password: str


class UserResponse(BaseModel):
    """User response schema."""
    id: uuid.UUID
    username: str
    created_at: datetime
    
    class Config:
        from_attributes = True


