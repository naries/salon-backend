from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.models import User
from app.schemas.schemas import TokenData

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")
customer_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/customer-auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict):
    """Create a JWT refresh token (valid for 7 days)"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def authenticate_user(db: Session, email: str, password: str):
    """Authenticate a user by email and password"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        salon_id: int = payload.get("salon_id")
        is_superadmin: int = payload.get("is_superadmin", 0)
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email, salon_id=salon_id, is_superadmin=is_superadmin)
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure the current user is an admin"""
    if current_user.is_admin != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_current_superadmin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure the current user is a superadmin"""
    if current_user.is_superadmin != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required"
        )
    return current_user


# Customer authentication functions
def authenticate_customer(db: Session, email: str, password: str):
    """Authenticate a customer by email and password"""
    from app.models.models import Customer
    customer = db.query(Customer).filter(Customer.email == email).first()
    if not customer:
        return False
    if not customer.hashed_password:
        return False
    if not verify_password(password, customer.hashed_password):
        return False
    return customer


async def get_current_customer(
    token: str = Depends(customer_oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Get the current authenticated customer from JWT token"""
    from app.models.models import Customer
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"get_current_customer called with token: {token[:20]}...")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        customer_id: int = payload.get("customer_id")
        uuid_str: str = payload.get("sub")  # UUID is now in the "sub" claim
        logger.info(f"Token decoded - customer_id: {customer_id}, uuid: {uuid_str}")
        if uuid_str is None or customer_id is None:
            logger.warning("Missing uuid or customer_id in token payload")
            raise credentials_exception
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise credentials_exception
    
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.uuid == uuid_str).first()
    if customer is None:
        logger.warning(f"Customer not found in database: id={customer_id}, uuid={uuid_str}")
        raise credentials_exception
    
    logger.info(f"Customer authenticated successfully: {customer.email}")
    return customer


async def get_current_customer_optional(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get the current authenticated customer if token is provided, otherwise return None.
    Useful for endpoints that work for both authenticated and guest users.
    """
    from app.models.models import Customer
    from fastapi import Request
    
    # Get authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        customer_id: int = payload.get("customer_id")
        uuid_str: str = payload.get("sub")  # UUID is now in "sub" claim
        token_type: str = payload.get("type")
        
        # Verify this is a customer token
        if token_type != "customer" or uuid_str is None or customer_id is None:
            return None
            
    except JWTError:
        return None
    
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.uuid == uuid_str).first()
    return customer
