import urllib.parse
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, Response, HTTPException, status, Query
from fastapi.responses import RedirectResponse
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
    extract_payload_from_signed_state,
    process_incoming_webhook_event,
    parse_meta_signed_request,
    connect_or_update_account_from_oauth,
    sync_connected_account_insights,
    disconnect_instagram_account,
    get_instagram_connection_status,
    refresh_workspace_instagram_token
)
from app.models.instagram import InstagramAccount, InstagramDataDeletionRequest
from app.security import get_current_user, rate_limit

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

@router.get("/media")
def get_instagram_media(
    limit: int = Query(10, ge=1, le=50),
    fields: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _limiter: bool = Depends(rate_limit(max_requests=20, window_seconds=60))
):
    """
    Directly queries media items for the workspace's connected Instagram account.
    Translates the verified Instagram Graph API media cURL command into an authenticated, tenant-isolated API.
    Defaults to verified cURL fields: id,caption,media_type,media_url,permalink,timestamp.
    """
    workspace = get_or_create_workspace(db, current_user)
    account = get_connected_account(db, workspace.id)
    if not account or not account.is_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No connected Instagram account found for this workspace."
        )

    if account.is_sandbox:
        return {
            "data": [
                {
                    "id": f"sandbox_media_{account.ig_user_id}_1",
                    "caption": "Sandbox Reel: 3 Hook Mistakes That Kill Your Retention",
                    "media_type": "VIDEO",
                    "media_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
                    "permalink": f"https://www.instagram.com/reel/C_demo_{account.ig_user_id}_1/",
                    "timestamp": "2026-10-12T14:30:00+0000"
                },
                {
                    "id": f"sandbox_media_{account.ig_user_id}_2",
                    "caption": "Sandbox Reel: The 140 WPM Sweet Spot for Spoken Pacing",
                    "media_type": "VIDEO",
                    "media_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
                    "permalink": f"https://www.instagram.com/reel/C_demo_{account.ig_user_id}_2/",
                    "timestamp": "2026-10-10T18:15:00+0000"
                }
            ],
            "is_sandbox": True
        }

    from app.security import decrypt_token
    from app.services.instagram_service import (
        fetch_instagram_media_list,
        MetaTokenExpiredError,
        MetaPermissionError,
        MetaRateLimitError,
        MetaAPIError
    )

    plain_token = decrypt_token(account.encrypted_access_token)
    if not plain_token:
        account.is_connected = False
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Stored Instagram access token corrupted or missing. Reauthorization required.")

    try:
        items = fetch_instagram_media_list(
            access_token=plain_token,
            user_id=account.ig_user_id,
            fields=fields,
            limit=limit
        )
        return {"data": items, "is_sandbox": False, "count": len(items)}
    except MetaTokenExpiredError as e:
        account.is_connected = False
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except MetaPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except MetaRateLimitError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except MetaAPIError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Meta Graph API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Unexpected error querying Meta Graph API: {str(e)}")

@router.get("/oauth-url", response_model=InstagramOAuthURLResponse)
def get_oauth_url(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _limiter: bool = Depends(rate_limit(max_requests=15, window_seconds=60))
):
    workspace = get_or_create_workspace(db, current_user)
    data = get_oauth_authorization_url(workspace.id)
    return InstagramOAuthURLResponse(**data)

@router.get("/callback")
def oauth_get_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_reason: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _limiter: bool = Depends(rate_limit(max_requests=10, window_seconds=60))
):
    """
    Standard browser redirect callback from Meta OAuth authorization dialog.
    Extracts workspace_id exclusively from the cryptographic HMAC-signed state.
    Redirects user browser to frontend dashboard with status parameters.
    """
    if error:
        err_msg = error_description or error_reason or error
        redirect_url = f"{settings.FRONTEND_URL}/dashboard/instagram?error={urllib.parse.quote(err_msg)}"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    if not code or not state:
        redirect_url = f"{settings.FRONTEND_URL}/dashboard/instagram?error={urllib.parse.quote('Missing required code or state parameter from Meta redirect.')}"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    payload = extract_payload_from_signed_state(state)
    if not payload or not payload.get("workspace_id"):
        redirect_url = f"{settings.FRONTEND_URL}/dashboard/instagram?error={urllib.parse.quote('Invalid or tampered OAuth state parameter (CSRF protection failed).')}"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    workspace_id = payload["workspace_id"]

    try:
        account = connect_or_update_account_from_oauth(db, workspace_id, code, state)
        redirect_url = f"{settings.FRONTEND_URL}/dashboard/instagram?connected=true&username={urllib.parse.quote(account.username)}"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    except HTTPException as exc:
        redirect_url = f"{settings.FRONTEND_URL}/dashboard/instagram?error={urllib.parse.quote(str(exc.detail))}"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    except Exception as exc:
        redirect_url = f"{settings.FRONTEND_URL}/dashboard/instagram?error={urllib.parse.quote(str(exc))}"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

@router.post("/connect", response_model=InstagramAccountResponse)
def connect_account(payload: InstagramConnectRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Exchanges Meta authorization code and binds Instagram account to workspace."""
    workspace = get_or_create_workspace(db, current_user)
    account = connect_or_update_account_from_oauth(db, workspace.id, payload.code, payload.state, redirect_uri=payload.redirect_uri)
    return InstagramAccountResponse.model_validate(account)

@router.post("/callback", response_model=InstagramAccountResponse)
def oauth_callback(payload: InstagramConnectRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Alternative callback handler for OAuth authorization code exchange."""
    workspace = get_or_create_workspace(db, current_user)
    account = connect_or_update_account_from_oauth(db, workspace.id, payload.code, payload.state, redirect_uri=payload.redirect_uri)
    return InstagramAccountResponse.model_validate(account)

@router.post("/sync-insights", response_model=InstagramSyncInsightsResponse)
def sync_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _limiter: bool = Depends(rate_limit(max_requests=10, window_seconds=60))
):
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
    """
    Receives Meta signed_request when user requests data deletion via Instagram settings.
    Validates HMAC signature, provides idempotent retries, creates persistent records,
    purges Instagram-derived credentials and active automations without deleting unrelated workspace data.
    """
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
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing user_id in signed_request payload")

    str_user_id = str(user_id)

    # Idempotent Retries: check if a deletion request already exists for this ig_user_id
    existing_req = db.query(InstagramDataDeletionRequest).filter(
        InstagramDataDeletionRequest.ig_user_id == str_user_id
    ).order_by(InstagramDataDeletionRequest.created_at.desc()).first()

    if existing_req and existing_req.status == "COMPLETED":
        return {
            "url": f"{settings.FRONTEND_URL}/deletion-status?code={existing_req.confirmation_code}",
            "confirmation_code": existing_req.confirmation_code
        }

    import uuid
    confirmation_code = existing_req.confirmation_code if existing_req else f"woka_del_{uuid.uuid4().hex[:12]}"
    deletion_req = existing_req or InstagramDataDeletionRequest(
        confirmation_code=confirmation_code,
        ig_user_id=str_user_id,
        status="PENDING"
    )
    if not existing_req:
        db.add(deletion_req)
    db.flush()

    try:
        # Comprehensive deletion of applicable Instagram-derived data (without deleting unrelated workspace data)
        from app.models.automation import Automation, AutomationLog
        from app.models.analytics import CreatorAnalytics
        from app.models.reel_intelligence import ReelAnalysisJob, ReelMetricSnapshot, ReelReport
        from app.models.profile import CreatorProfile

        accounts = db.query(InstagramAccount).filter(InstagramAccount.ig_user_id == str_user_id).all()
        for account in accounts:
            account.is_connected = False
            account.encrypted_access_token = ""
            account.token_expires_at = None
            account.profile_pic_url = None
            account.granted_permissions = ""
            account.followers_count = 0
            account.media_count = 0

            # 1. Automations & logs tied to this Instagram account
            automations = db.query(Automation).filter(Automation.ig_account_id == account.id).all()
            automation_ids = [a.id for a in automations]
            if automation_ids:
                db.query(AutomationLog).filter(AutomationLog.automation_id.in_(automation_ids)).delete(synchronize_session=False)

            # Deactivate automations and clear post targets
            db.query(Automation).filter(Automation.ig_account_id == account.id).update(
                {"is_active": False, "target_post_id": None, "target_post_preview_url": None},
                synchronize_session=False
            )

            # 2. CreatorAnalytics: purge audience insights and top posts derived from Instagram
            analytics_records = db.query(CreatorAnalytics).filter(
                CreatorAnalytics.workspace_id == account.workspace_id
            ).all()
            for ar in analytics_records:
                ar.demographics_json = None
                ar.top_posts_json = None
                ar.reach_30d = 0
                ar.impressions_30d = 0
                ar.avg_engagement_rate = 0.0
                ar.followers_count = 0
                ar.media_count = 0

            # 3. Connected Reel Intelligence: purge private Meta Graph API metrics
            connected_jobs = db.query(ReelAnalysisJob).filter(
                ReelAnalysisJob.workspace_id == account.workspace_id,
                ReelAnalysisJob.analysis_mode == "CONNECTED_ACCOUNT"
            ).all()
            for cj in connected_jobs:
                db.query(ReelMetricSnapshot).filter(ReelMetricSnapshot.job_id == cj.id).delete(synchronize_session=False)
                cj.source_media_id = None
                reports = db.query(ReelReport).filter((ReelReport.job_id == cj.id) | (ReelReport.id == cj.report_id)).all()
                for rep in reports:
                    rep.caption = None
                    rep.calculated_metrics_json = "{}"






            # 4. CreatorProfile: clear avatar if synchronized from Instagram CDN
            profile = db.query(CreatorProfile).filter(CreatorProfile.workspace_id == account.workspace_id).first()
            if profile and profile.avatar_url and ("cdninstagram" in profile.avatar_url or "fbcdn" in profile.avatar_url):
                profile.avatar_url = None

        # Also purge any dangling AutomationLogs referencing this recipient_ig_id
        db.query(AutomationLog).filter(AutomationLog.recipient_ig_id == str_user_id).delete(synchronize_session=False)

        deletion_req.status = "COMPLETED"
        deletion_req.completed_at = datetime.now(timezone.utc)
        deletion_req.details = (
            f"Purged Instagram access tokens, cached profile data, audience demographics, "
            f"top posts, automation logs, and connected reel private metrics for ig_user_id {str_user_id}."
        )
        db.commit()
    except Exception as e:
        db.rollback()
        deletion_req.status = "FAILED"
        deletion_req.details = f"Data deletion failed: {str(e)}"
        db.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process user data deletion request")

    return {
        "url": f"{settings.FRONTEND_URL}/deletion-status?code={confirmation_code}",
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




@router.get("/endpoints-info")
def get_endpoints_info():
    """Returns the resolved public webhook and callback URLs for Meta Developer Portal configuration."""
    return {
        "backend_public_url": settings.BACKEND_PUBLIC_URL or "http://localhost:8000",
        "oauth_callback_url": settings.public_oauth_callback_url,
        "webhook_url": settings.public_webhook_url,
        "deauthorize_url": settings.public_deauthorize_url,
        "data_deletion_url": settings.public_data_deletion_url,
        "cors_origins": settings.CORS_ORIGINS,
        "environment": settings.ENVIRONMENT
    }


@router.get("/deletion-status")
def get_deletion_status(
    code: str = Query(..., description="Data deletion confirmation code"),
    db: Session = Depends(get_db)
):
    """
    Verifies the status of a user data deletion request.
    Returns honest PENDING, COMPLETED, or FAILED status from persistent records.
    Rejects unknown codes with 404 (no false COMPLETED response).
    """
    record = db.query(InstagramDataDeletionRequest).filter(
        InstagramDataDeletionRequest.confirmation_code == code
    ).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data deletion confirmation code '{code}' not found."
        )

    if record.details:
        message = record.details
    elif record.status == "COMPLETED":
        message = "User data deletion request has been processed. Access tokens and profile associations have been purged."
    elif record.status == "FAILED":
        message = "User data deletion request failed to process."
    else:
        message = "Data deletion request is currently pending processing."

    return {
        "confirmation_code": record.confirmation_code,
        "status": record.status,
        "message": message,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "completed_at": record.completed_at.isoformat() if record.completed_at else None
    }
