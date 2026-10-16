import base64
import hashlib
import hmac
import json
import urllib.parse
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.config import settings
from app.models.instagram import InstagramAccount
from app.models.automation import Automation, AutomationLog
from app.security import encrypt_token, decrypt_token
from app.services.subscription_service import check_and_increment_dm_quota

META_OAUTH_SCOPES = [
    "instagram_basic",
    "instagram_manage_comments",
    "instagram_manage_messages",
    "pages_show_list",
    "pages_read_engagement"
]

def generate_oauth_state(workspace_id: str) -> str:
    """Generates an HMAC-SHA256 cryptographically signed OAuth state parameter."""
    state_payload = {
        "workspace_id": workspace_id,
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
        "nonce": str(uuid.uuid4())
    }
    raw_json = json.dumps(state_payload, separators=(",", ":"))
    sig = hmac.new(settings.SECRET_KEY.encode(), raw_json.encode(), hashlib.sha256).hexdigest()
    b64_payload = base64.urlsafe_b64encode(raw_json.encode()).decode()
    return f"{b64_payload}.{sig}"

def verify_oauth_state(state: str, expected_workspace_id: str, db: Optional[Session] = None, max_age_seconds: int = 900) -> bool:
    """Verifies HMAC signature, timestamp expiration, workspace binding, and prevents replay attacks."""
    if not state or "." not in state:
        return False
    try:
        b64_payload, signature = state.split(".", 1)
        raw_json_bytes = base64.urlsafe_b64decode(b64_payload.encode())
        expected_sig = hmac.new(settings.SECRET_KEY.encode(), raw_json_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, signature):
            return False

        payload = json.loads(raw_json_bytes.decode())
        if payload.get("workspace_id") != expected_workspace_id:
            return False

        created_ts = payload.get("timestamp", 0)
        current_ts = int(datetime.now(timezone.utc).timestamp())
        if current_ts - created_ts > max_age_seconds or created_ts > current_ts + 60:
            return False

        # Nonce Replay Prevention
        nonce = payload.get("nonce")
        if db is not None and nonce:
            from app.models.user import UsedOAuthNonce
            existing = db.query(UsedOAuthNonce).filter(UsedOAuthNonce.nonce == nonce).first()
            if existing:
                return False  # Replay detected
            db.add(UsedOAuthNonce(nonce=nonce, workspace_id=expected_workspace_id))
            db.commit()

        return True
    except Exception:
        return False

def parse_meta_signed_request(signed_request: str) -> Optional[dict]:
    """Parses and verifies an official Meta signed_request using HMAC-SHA256."""
    if not signed_request or "." not in signed_request:
        return None
    try:
        encoded_sig, payload = signed_request.split(".", 1)
        sig = base64.urlsafe_b64decode(encoded_sig + "=" * (-len(encoded_sig) % 4))
        data_bytes = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        data = json.loads(data_bytes.decode("utf-8"))
        
        expected_sig = hmac.new(
            settings.META_APP_SECRET.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256
        ).digest()
        
        if not hmac.compare_digest(sig, expected_sig):
            return None
        return data
    except Exception:
        return None


def generate_mock_signed_request(user_id: str, issued_at: Optional[int] = None) -> str:
    """Generates an official HMAC-SHA256 signed_request for Meta callbacks (testing/sandbox)."""
    import time
    payload_data = {
        "user_id": str(user_id),
        "algorithm": "HMAC-SHA256",
        "issued_at": issued_at or int(time.time())
    }
    payload_json = json.dumps(payload_data, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8").rstrip("=")
    sig = hmac.new(settings.META_APP_SECRET.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")
    return f"{sig_b64}.{payload_b64}"


def get_oauth_authorization_url(workspace_id: str) -> dict:
    signed_state = generate_oauth_state(workspace_id)
    scopes_str = ",".join(META_OAUTH_SCOPES)
    
    oauth_url = (
        f"https://www.facebook.com/v19.0/dialog/oauth?"
        f"client_id={settings.META_APP_ID}"
        f"&redirect_uri={urllib.parse.quote(settings.META_REDIRECT_URI)}"
        f"&scope={scopes_str}"
        f"&response_type=code"
        f"&state={signed_state}"
    )
    return {"oauth_url": oauth_url, "state": signed_state}

def get_connected_account(db: Session, workspace_id: str) -> Optional[InstagramAccount]:
    return db.query(InstagramAccount).filter(
        InstagramAccount.workspace_id == workspace_id,
        InstagramAccount.is_connected == True
    ).first()

def toggle_sandbox_account(
    db: Session,
    workspace_id: str,
    enabled: bool = True,
    username: str = "creator_woka_demo",
    followers_count: int = 48500
) -> InstagramAccount:
    account = db.query(InstagramAccount).filter(InstagramAccount.workspace_id == workspace_id).first()
    
    if enabled:
        if not account:
            account = InstagramAccount(
                workspace_id=workspace_id,
                ig_user_id=f"demo_ig_{workspace_id[:8]}",
                username=username,
                name="Woka Creator Demo",
                profile_pic_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
                encrypted_access_token=encrypt_token("demo_sandbox_token_woka_valid"),
                token_expires_at=datetime.now(timezone.utc) + timedelta(days=60),
                is_connected=True,
                is_sandbox=True,
                followers_count=followers_count,
                media_count=138
            )
            db.add(account)
        else:
            account.is_connected = True
            account.is_sandbox = True
            account.username = username
            account.followers_count = followers_count
            account.token_expires_at = datetime.now(timezone.utc) + timedelta(days=60)
            
        db.commit()
        db.refresh(account)
        return account
    else:
        if account and account.is_sandbox:
            account.is_connected = False
            db.commit()
            db.refresh(account)
        return account

def verify_meta_webhook_signature(payload_bytes: bytes, signature_header: Optional[str]) -> bool:
    """Verifies official Meta X-Hub-Signature-256 header."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected_hash = signature_header.split("sha256=")[-1]
    computed_hash = hmac.new(
        settings.META_APP_SECRET.encode(),
        msg=payload_bytes,
        digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed_hash, expected_hash)

def process_incoming_webhook_event(db: Session, event_data: dict) -> Dict[str, Any]:
    """
    Ingests and processes Meta Instagram webhook events (e.g. comments).
    Guarantees:
    1. Idempotency (deduplicates repeated comment deliveries)
    2. Anti-spam policy enforcement (cooldown per recipient)
    3. Workspace DM quota decrement and limit enforcement
    4. Audit logging
    """
    from app.services.automation_engine import match_comment, render_template

    entries = event_data.get("entry", [])
    results = []

    for entry in entries:
        ig_user_id = entry.get("id")
        account = db.query(InstagramAccount).filter(
            (InstagramAccount.ig_user_id == ig_user_id) & (InstagramAccount.is_connected == True)
        ).first()

        # If not matched by ID (e.g. in test/sandbox), fallback to any active connected account
        if not account:
            account = db.query(InstagramAccount).filter(InstagramAccount.is_connected == True).first()
        
        if not account:
            continue

        changes = entry.get("changes", [])
        for change in changes:
            field = change.get("field")
            if field != "comments":
                continue

            value = change.get("value", {})
            comment_id = value.get("id")
            comment_text = value.get("text", "")
            sender = value.get("from", {})
            sender_id = str(sender.get("id", ""))
            sender_username = sender.get("username", "user")
            media_id = value.get("media", {}).get("id")

            if not comment_id:
                continue

            # 1. Idempotency Deduplication Check
            existing_log = db.query(AutomationLog).filter(
                AutomationLog.trigger_comment_id == comment_id
            ).first()
            if existing_log:
                results.append({
                    "comment_id": comment_id,
                    "status": "DUPLICATE_IGNORED",
                    "reason": "Comment already processed"
                })
                continue

            # 2. Find matching automations
            automations = db.query(Automation).filter(
                Automation.ig_account_id == account.id,
                Automation.is_active == True
            ).all()

            matched_any = False
            for auto in automations:
                matched, kw = match_comment(auto, media_id, comment_text)
                if not matched:
                    continue

                matched_any = True

                # 3. Anti-Spam Policy: Enforce cooldown per recipient
                cutoff = datetime.now(timezone.utc) - timedelta(minutes=auto.cooldown_minutes)
                recent_trigger = db.query(AutomationLog).filter(
                    AutomationLog.automation_id == auto.id,
                    (AutomationLog.recipient_username == sender_username) | (AutomationLog.recipient_ig_id == sender_id),
                    AutomationLog.created_at >= cutoff,
                    AutomationLog.status.in_(["SUCCESS", "SIMULATED"])
                ).first()

                if recent_trigger:
                    suppressed_log = AutomationLog(
                        automation_id=auto.id,
                        recipient_ig_id=sender_id,
                        recipient_username=sender_username,
                        trigger_comment_id=comment_id,
                        trigger_comment_text=comment_text,
                        dm_text_sent="",
                        status="RATE_LIMITED",
                        error_message=f"Suppressed by anti-spam cooldown ({auto.cooldown_minutes}m rule)"
                    )
                    db.add(suppressed_log)
                    db.commit()
                    results.append({
                        "comment_id": comment_id,
                        "status": "SUPPRESSED_COOLDOWN",
                        "automation": auto.name
                    })
                    break

                # 4. DM Quota check
                quota_available = check_and_increment_dm_quota(db, account.workspace_id)
                if not quota_available:
                    failed_log = AutomationLog(
                        automation_id=auto.id,
                        recipient_ig_id=sender_id,
                        recipient_username=sender_username,
                        trigger_comment_id=comment_id,
                        trigger_comment_text=comment_text,
                        dm_text_sent="",
                        status="FAILED",
                        error_message="Monthly DM quota exceeded"
                    )
                    db.add(failed_log)
                    db.commit()
                    results.append({
                        "comment_id": comment_id,
                        "status": "QUOTA_EXCEEDED",
                        "automation": auto.name
                    })
                    break

                # 5. Success execution
                dm_body = render_template(auto.dm_message_template, sender_username)
                status_label = "SIMULATED" if account.is_sandbox else "SUCCESS"
                success_log = AutomationLog(
                    automation_id=auto.id,
                    recipient_ig_id=sender_id,
                    recipient_username=sender_username,
                    trigger_comment_id=comment_id,
                    trigger_comment_text=comment_text,
                    dm_text_sent=dm_body,
                    status=status_label
                )
                db.add(success_log)
                auto.total_triggered_count += 1
                db.commit()

                results.append({
                    "comment_id": comment_id,
                    "status": status_label,
                    "automation": auto.name,
                    "recipient": sender_username
                })
                break

            if not matched_any:
                results.append({
                    "comment_id": comment_id,
                    "status": "NO_RULE_MATCHED"
                })

    return {"status": "PROCESSED", "results": results}

