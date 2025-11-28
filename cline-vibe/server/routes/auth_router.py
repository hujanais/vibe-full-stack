"""Authentication endpoints."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from core.database import get_db
from api.auth_api import register_user, authenticate_user
from models.auth import LoginRequest, Token, UserCreate, UserResponse

router = APIRouter(prefix="/api/v1", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    return register_user(user_data, db)


@router.post("/login", response_model=Token)
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Login and get JWT token."""
    return authenticate_user(credentials, db)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    """Logout (client-side token removal)."""
    # JWT tokens are stateless, so logout is handled client-side
    # In a production system, you might want to maintain a token blacklist
    return None


