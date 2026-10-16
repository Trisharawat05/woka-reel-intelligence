from fastapi import APIRouter, Depends, Request, Response, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.config import settings
from app.models.user import User
from app.schemas.instagram import (
    InstagramAccountResponse,
    InstagramOAuthURLResponse,
    InstagramConnectRequest,
    InstagramStatusResponse,
    InstagramSyncInsightsResponse,
    InstagramDisconnectResponse,
    InstagramRefreshTokenResponse,
    InstagramSandboxToggleRequest
)
from app.services.auth_service import get_or_create_workspace
from app.services.instagram_service import (
    get_oauth_authorization_url,
    get_connected_account,
    toggle_sandbox_account,
    verify_meta_webhook_signature,
    verify_oauth_state,
    process_incoming_webhook_event,
    parse_meta_signed_request,
    connect_or_update_account_from_oauth,
    sync_connected_account_insights,
    disconnect_instagram_account,
    get_instagram_connection_status,
    refresh_workspace_instagram_token
)
from app.models.instagram import InstagramAccount
from app.security import get_current_user

router = APIRouter(prefix="/instagram", tags=["Instagram Integration"])

@router.get("/status", response_model=InstagramStatusResponse)
def get_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retrieves the connected Instagram account status, token health, and permissions."""
    workspace = get_or_create_workspace(db, current_user)
    status_data = get_instagram_connection_status(db, workspace.id)
    return status_data

@router.get("/account", response_model=Optional[InstagramAccountResponse])
def get_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    account = get_connected_account(db, workspace.id)
    if not account:
        return None
    return InstagramAccountResponse.model_validate(account)

@router.get("/oauth-url", response_model=InstagramOAuthURLResponse)
def get_oauth_url(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    data = get_oauth_authorization_url(workspace.id)
    return InstagramOAuthURLResponse(**data)

@router.post("/connect", response_model=InstagramAccountResponse)
def connect_account(payload: InstagramConnectRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Exchanges Meta authorization code and binds Instagram account to workspace."""
    workspace = get_or_create_workspace(db, current_user)
    account = connect_or_update_account_from_oauth(db, workspace.id, payload.code, payload.state)
    return InstagramAccountResponse.model_validate(account)

@router.post("/callback", response_model=InstagramAccountResponse)
def oauth_callback(payload: InstagramConnectRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Alternative callback handler for OAuth authorization code exchange."""
    workspace = get_or_create_workspace(db, current_user)
    account = connect_or_update_account_from_oauth(db, workspace.id, payload.code, payload.state)
    return InstagramAccountResponse.model_validate(account)

@router.post("/sync-insights", response_model=InstagramSyncInsightsResponse)
def sync_insights(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Synchronizes live Reel insights from Meta Graph API without data fabrication."""
    workspace = get_or_create_workspace(db, current_user)
    result = sync_connected_account_insights(db, workspace.id)
    return result

@router.post("/disconnect", response_model=InstagramDisconnectResponse)
def disconnect_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Disconnects Instagram account, wipes tokens, and revokes access."""
    workspace = get_or_create_workspace(db, current_user)
    result = disconnect_instagram_account(db, workspace.id)
    return result

@router.post("/refresh-token", response_model=InstagramRefreshTokenResponse)
def refresh_token(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Refreshes long-lived 60-day Instagram access token."""
    workspace = get_or_create_workspace(db, current_user)
    result = refresh_workspace_instagram_token(db, workspace.id)
    return result

@router.post("/sandbox/toggle", response_model=InstagramAccountResponse)
def toggle_sandbox(payload: InstagramSandboxToggleRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    account = toggle_sandbox_account(
        db,
        workspace.id,
        enabled=payload.enabled,
        username=payload.username or "creator_woka_demo",
        followers_count=payload.followers_count or 48500
    )
    return InstagramAccountResponse.model_validate(account)

# Official Meta Deauthorize Callback
@router.post("/deauthorize")
async def meta_deauthorize_callback(request: Request, db: Session = Depends(get_db)):
    """Receives Meta signed_request when user removes app permissions via Instagram settings."""
    form_data = await request.form()
    signed_request = form_data.get("signed_request")
    if not signed_request:
        body_bytes = await request.body()
        try:
            import json
            json_body = json.loads(body_bytes.decode())
            signed_request = json_body.get("signed_request")
        except Exception:
            pass

    if not signed_request:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing signed_request parameter")

    payload = parse_meta_signed_request(signed_request)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signed_request signature")

    user_id = payload.get("user_id")
    if user_id:
        account = db.query(InstagramAccount).filter(InstagramAccount.ig_user_id == str(user_id)).first()
        if account:
            account.is_connected = False
            account.encrypted_access_token = ""
            db.commit()

    return {"status": "DEAUTHORIZED"}

# Official Meta User Data Deletion Callback
@router.post("/data-deletion")
async def meta_data_deletion_callback(request: Request, db: Session = Depends(get_db)):
    """Receives Meta signed_request when user requests data deletion via Instagram settings."""
    form_data = await request.form()
    signed_request = form_data.get("signed_request")
    if not signed_request:
        body_bytes = await request.body()
        try:
            import json
            json_body = json.loads(body_bytes.decode())
            signed_request = json_body.get("signed_request")
        except Exception:
            pass

    if not signed_request:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing signed_request parameter")

    payload = parse_meta_signed_request(signed_request)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signed_request signature")

    import uuid
    confirmation_code = f"woka_del_{uuid.uuid4().hex[:12]}"
    user_id = payload.get("user_id")
    if user_id:
        account = db.query(InstagramAccount).filter(InstagramAccount.ig_user_id == str(user_id)).first()
        if account:
            account.is_connected = False
            account.encrypted_access_token = ""
            db.commit()

    return {
        "url": f"https://app.woka.io/deletion-status?code={confirmation_code}",
        "confirmation_code": confirmation_code
    }

# Official Meta Webhook Endpoints
@router.get("/webhook")
def meta_webhook_verification(
    request: Request,
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """Meta Webhook Challenge Verification."""
    if hub_mode == "subscribe" and hub_verify_token == settings.META_VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification token mismatch")

@router.post("/webhook")
async def meta_webhook_receiver(request: Request, db: Session = Depends(get_db)):
    """Inbound Meta Webhook processor for Instagram comments and messages."""
    body_bytes = await request.body()
    sig_header = request.headers.get("X-Hub-Signature-256")
    
    # In production, enforce strict signature verification
    if settings.ENVIRONMENT != "development" or sig_header:
        if not verify_meta_webhook_signature(body_bytes, sig_header):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    try:
        import json
        event_data = json.loads(body_bytes.decode())
    except Exception:
        event_data = {}

    result = process_incoming_webhook_event(db, event_data)
    return result


