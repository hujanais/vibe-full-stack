"""Authentication business logic."""
from datetime import timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from core.security import verify_password, get_password_hash, create_access_token
from core.config import settings
from db_models.user_orm import User
from models.auth import LoginRequest, Token, UserCreate, UserResponse


def register_user(user_data: UserCreate, db: Session) -> UserResponse:
    """
    Register a new user.
    
    Args:
        user_data: User creation data
        db: Database session
        
    Returns:
        UserResponse: Created user data
        
    Raises:
        HTTPException: If username already exists
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        password_hash=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


def authenticate_user(credentials: LoginRequest, db: Session) -> Token:
    """
    Authenticate user and generate access token.
    
    Args:
        credentials: Login credentials
        db: Database session
        
    Returns:
        Token: Access token response
        
    Raises:
        HTTPException: If credentials are invalid or user is inactive
    """
    user = db.query(User).filter(User.username == credentials.username).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

