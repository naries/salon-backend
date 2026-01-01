from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from jose import JWTError, jwt
from app.core.database import get_db
from app.core.security import authenticate_user, create_access_token, create_refresh_token, get_password_hash
from app.core.config import settings
from app.schemas.schemas import Token, LoginRequest, RefreshTokenRequest, UserCreate, UserResponse
from app.models.models import User, ActivityLog

router = APIRouter()


@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Login endpoint for salon admins and superadmins"""
    user = authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Log login activity
    log = ActivityLog(
        user_id=user.id,
        salon_id=user.salon_id,
        action="login",
        entity_type="user",
        entity_id=user.id,
        description=f"{user.email} logged in",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.email,
            "salon_id": user.salon_id,
            "is_superadmin": user.is_superadmin
        },
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={
            "sub": user.email,
            "salon_id": user.salon_id,
            "is_superadmin": user.is_superadmin
        }
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_admin(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    """Register a new salon admin or superadmin"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    db_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        salon_id=user_data.salon_id,
        is_admin=1,
        is_superadmin=user_data.is_superadmin or 0
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Log user registration
    log = ActivityLog(
        user_id=db_user.id,
        salon_id=db_user.salon_id,
        action="created",
        entity_type="user",
        entity_id=db_user.id,
        description=f"Registered new user {db_user.email}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return db_user


@router.post("/refresh", response_model=Token)
def refresh_token(token_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Refresh access token using refresh token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token_data.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if email is None or token_type != "refresh":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    # Create new access token and refresh token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={
            "sub": user.email,
            "salon_id": user.salon_id,
            "is_superadmin": user.is_superadmin
        },
        expires_delta=access_token_expires
    )
    new_refresh_token = create_refresh_token(
        data={
            "sub": user.email,
            "salon_id": user.salon_id,
            "is_superadmin": user.is_superadmin
        }
    )
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "user": user
    }
