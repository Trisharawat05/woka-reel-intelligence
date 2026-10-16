import uuid
import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    jti = str(uuid.uuid4())
    to_encode.update({"exp": expire, "type": "access", "jti": jti})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())
    to_encode.update({"exp": expire, "type": "refresh", "jti": jti})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Fernet Key Helper: Ensures a 32-byte url-safe base64 key
def get_fernet_cipher() -> Fernet:
    raw_key = settings.TOKEN_ENCRYPTION_KEY.encode()
    # If key is not valid 32 url-safe base64, hash it to sha256 and base64-encode
    try:
        return Fernet(raw_key)
    except Exception:
        derived = base64.urlsafe_b64encode(hashlib.sha256(raw_key).digest())
        return Fernet(derived)

def encrypt_token(plain_token: str) -> str:
    """Encrypts a sensitive OAuth access token using AES-256 Fernet."""
    if not plain_token:
        return ""
    cipher = get_fernet_cipher()
    return cipher.encrypt(plain_token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    """Decrypts an AES-256 Fernet encrypted OAuth token."""
    if not encrypted_token:
        return ""
    cipher = get_fernet_cipher()
    try:
        return cipher.decrypt(encrypted_token.encode()).decode()
    except Exception:
        return ""

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    from app.models.user import User, RevokedToken
    payload = decode_token(token)
    token_type = payload.get("type")
    if token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type: access token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    jti = payload.get("jti")
    if jti:
        revoked = db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
        if revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    return user

def require_roles(allowed_roles: List[str]):
    def role_checker(current_user: Any = Depends(get_current_user)):
        if current_user.role not in allowed_roles and current_user.role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of {allowed_roles}"
            )
        return current_user
    return role_checker


# ==============================================================================
# Sliding Window Rate Limiting Dependency
# ==============================================================================

import time
from collections import defaultdict
from fastapi import Request

_rate_limit_records = defaultdict(list)

def rate_limit(max_requests: int = 30, window_seconds: int = 60, key_func=None):
    """
    Dependency for sliding-window rate limiting per client IP or authenticated entity.
    Returns HTTP 429 Too Many Requests if threshold is exceeded within the rolling window.
    """
    def limiter(request: Request):
        now = time.time()
        client_ip = request.client.host if request.client else "127.0.0.1"
        ident = key_func(request) if key_func else client_ip
        scope_key = f"{request.url.path}:{ident}"

        # Evict timestamps older than rolling window
        history = _rate_limit_records[scope_key]
        _rate_limit_records[scope_key] = [ts for ts in history if now - ts < window_seconds]

        if len(_rate_limit_records[scope_key]) >= max_requests:
            oldest = _rate_limit_records[scope_key][0]
            retry_after = max(1, int(window_seconds - (now - oldest)))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds}s.",
                headers={"Retry-After": str(retry_after)}
            )
        _rate_limit_records[scope_key].append(now)
        return True

    return limiter


def reset_rate_limits():
    """Helper for testing to reset rate limit tracking."""
    _rate_limit_records.clear()

