from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, Workspace, RevokedToken
from app.schemas.auth import (
    UserRegister, UserLogin, TokenResponse, OAuth2TokenResponse, UserResponse,
    WorkspaceResponse, WorkspaceMembershipResponse, WorkspaceSelectRequest,
    TokenRefreshRequest, TokenRefreshResponse,
    LogoutRequest, MessageResponse
)
from app.services.auth_service import (
    register_user, authenticate_user, get_or_create_workspace,
    list_user_workspace_memberships, resolve_active_workspace
)
from app.security import (
    create_access_token, create_refresh_token, decode_token,
    get_current_user, oauth2_scheme
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _create_session_tokens(user: User, workspace: Workspace) -> tuple[str, str]:
    """Issues workspace-scoped access and refresh JWTs for an authenticated session."""
    access_token = create_access_token(
        data={"sub": user.id, "role": user.role, "workspace_id": workspace.id}
    )
    refresh_token = create_refresh_token(data={"sub": user.id})
    return access_token, refresh_token


def _build_token_response(user: User, workspace: Workspace) -> TokenResponse:
    """Builds the full JSON auth payload containing session tokens, user, and workspace."""
    access_token, refresh_token = _create_session_tokens(user, workspace)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
        workspace=WorkspaceResponse.model_validate(workspace),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    user, workspace = register_user(db, payload)
    return _build_token_response(user, workspace)

@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user, workspace = authenticate_user(db, payload.email, payload.password)
    return _build_token_response(user, workspace)


@router.post("/token", response_model=OAuth2TokenResponse)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """OAuth2 password-flow login for Swagger UI, treating username as the account email."""
    user, workspace = authenticate_user(db, form_data.username.strip(), form_data.password)
    access_token, refresh_token = _create_session_tokens(user, workspace)
    return OAuth2TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.get("/workspaces", response_model=List[WorkspaceMembershipResponse])
def list_my_workspaces(
    current_user: User = Depends(get_current_user),
    raw_token: str = Depends(oauth2_scheme),
    x_workspace_id: Optional[str] = Header(default=None, alias="X-Workspace-Id"),
    db: Session = Depends(get_db),
):
    """Lists all workspaces the authenticated user belongs to in deterministic order."""
    token_data = decode_token(raw_token)
    active_workspace_id = None
    if x_workspace_id is not None:
        ws, _ = resolve_active_workspace(
            db, current_user, requested_workspace_id=x_workspace_id, token_workspace_id=token_data.get("workspace_id")
        )
        active_workspace_id = ws.id
    elif token_data.get("workspace_id"):
        active_workspace_id = token_data.get("workspace_id")

    memberships = list_user_workspace_memberships(db, current_user)
    if active_workspace_id is None and memberships:
        active_workspace_id = memberships[0][1].id

    return [
        WorkspaceMembershipResponse(
            id=ws.id,
            name=ws.name,
            owner_id=ws.owner_id,
            role_in_workspace=member.role_in_workspace,
            is_active=(ws.id == active_workspace_id),
        )
        for member, ws in memberships
    ]


@router.post("/workspaces/select", response_model=TokenResponse)
def select_active_workspace(
    payload: WorkspaceSelectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Validates workspace membership and issues session tokens scoped to the selected workspace."""
    workspace, _ = resolve_active_workspace(
        db, current_user, requested_workspace_id=payload.workspace_id
    )
    return _build_token_response(current_user, workspace)

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
    new_access_token, new_refresh_token = _create_session_tokens(user, workspace)
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

