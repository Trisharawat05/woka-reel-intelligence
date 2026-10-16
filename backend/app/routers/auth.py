from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, RevokedToken
from app.schemas.auth import (
    UserRegister, UserLogin, TokenResponse, UserResponse,
    WorkspaceResponse, TokenRefreshRequest, TokenRefreshResponse,
    LogoutRequest, MessageResponse
)
from app.services.auth_service import register_user, authenticate_user, get_or_create_workspace
from app.security import (
    create_access_token, create_refresh_token, decode_token,
    get_current_user, oauth2_scheme
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    user, workspace = register_user(db, payload)
    access_token = create_access_token(data={"sub": user.id, "role": user.role, "workspace_id": workspace.id})
    refresh_token = create_refresh_token(data={"sub": user.id})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
        workspace=WorkspaceResponse.model_validate(workspace)
    )

@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user, workspace = authenticate_user(db, payload.email, payload.password)
    access_token = create_access_token(data={"sub": user.id, "role": user.role, "workspace_id": workspace.id})
    refresh_token = create_refresh_token(data={"sub": user.id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
        workspace=WorkspaceResponse.model_validate(workspace)
    )

@router.get("/me", response_model=TokenResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    access_token = create_access_token(data={"sub": current_user.id, "role": current_user.role, "workspace_id": workspace.id})
    refresh_token = create_refresh_token(data={"sub": current_user.id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(current_user),
        workspace=WorkspaceResponse.model_validate(workspace)
    )

@router.post("/refresh", response_model=TokenRefreshResponse)
def refresh_token(payload: TokenRefreshRequest, db: Session = Depends(get_db)):
    token_data = decode_token(payload.refresh_token)
    if token_data.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type: refresh token required"
        )
    
    jti = token_data.get("jti")
    if jti:
        revoked = db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
        if revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked"
            )

    user_id = token_data.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer active or valid"
        )

    # Invalidate the used refresh token (refresh token rotation)
    if jti:
        exp_ts = token_data.get("exp")
        expires_at = datetime.fromtimestamp(exp_ts, timezone.utc) if exp_ts else datetime.now(timezone.utc) + timedelta(days=30)
        db.add(RevokedToken(jti=jti, token_type="refresh", user_id=user.id, expires_at=expires_at))

    workspace = get_or_create_workspace(db, user)
    new_access_token = create_access_token(data={"sub": user.id, "role": user.role, "workspace_id": workspace.id})
    new_refresh_token = create_refresh_token(data={"sub": user.id})
    db.commit()

    return TokenRefreshResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token
    )

@router.post("/logout", response_model=MessageResponse)
def logout(
    payload: LogoutRequest = LogoutRequest(),
    raw_token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Revoke current access token
    try:
        access_data = decode_token(raw_token)
        access_jti = access_data.get("jti")
        if access_jti:
            exp_ts = access_data.get("exp")
            expires_at = datetime.fromtimestamp(exp_ts, timezone.utc) if exp_ts else datetime.now(timezone.utc) + timedelta(hours=1)
            existing = db.query(RevokedToken).filter(RevokedToken.jti == access_jti).first()
            if not existing:
                db.add(RevokedToken(jti=access_jti, token_type="access", user_id=current_user.id, expires_at=expires_at))
    except Exception:
        pass

    # Revoke provided refresh token if passed
    if payload.refresh_token:
        try:
            refresh_data = decode_token(payload.refresh_token)
            refresh_jti = refresh_data.get("jti")
            if refresh_jti:
                exp_ts = refresh_data.get("exp")
                expires_at = datetime.fromtimestamp(exp_ts, timezone.utc) if exp_ts else datetime.now(timezone.utc) + timedelta(days=30)
                existing = db.query(RevokedToken).filter(RevokedToken.jti == refresh_jti).first()
                if not existing:
                    db.add(RevokedToken(jti=refresh_jti, token_type="refresh", user_id=current_user.id, expires_at=expires_at))
        except Exception:
            pass

    db.commit()
    return MessageResponse(message="Successfully logged out and revoked tokens")

