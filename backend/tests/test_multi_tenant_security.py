import hmac
import hashlib
import json
import os
import shutil
import pytest
from app.config import settings
from app.models.automation import Automation, AutomationLog
from app.models.instagram import InstagramAccount
from app.models.notification import Notification
from app.models.profile import CreatorProfile
from app.models.subscription import Subscription
from app.models.user import User, Workspace, WorkspaceMember
from app.security import (
    create_access_token,
    create_thumbnail_signature_token,
    encrypt_token,
    get_password_hash,
)
from app.services.subscription_service import get_workspace_subscription


def _create_user_with_workspace(db_session, email: str, role: str, full_name: str, ig_user_id: str | None = None, is_sandbox: bool = True):
    user = User(
        email=email,
        hashed_password=get_password_hash("Password123!"),
        full_name=full_name,
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    ws = Workspace(name=f"{full_name}'s Workspace", owner_id=user.id)
    db_session.add(ws)
    db_session.flush()

    db_session.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role_in_workspace="OWNER"))
    db_session.add(Subscription(workspace_id=ws.id, plan_tier="FREE", status="ACTIVE"))
    db_session.add(CreatorProfile(
        workspace_id=ws.id,
        slug=email.split("@")[0].replace(".", "_"),
        display_name=full_name,
        bio="Creator bio",
        niches='["Tech"]',
        is_public=True,
    ))

    if ig_user_id:
        db_session.add(InstagramAccount(
            workspace_id=ws.id,
            ig_user_id=ig_user_id,
            username=f"{email.split('@')[0]}_ig",
            name=full_name,
            encrypted_access_token=encrypt_token("valid_plain_ig_token"),
            is_connected=True,
            is_sandbox=is_sandbox,
        ))

    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(ws)
    token = create_access_token(data={"sub": user.id, "role": user.role, "workspace_id": ws.id})
    headers = {"Authorization": f"Bearer {token}"}
    return user, ws, headers


# ==============================================================================
# 1. Active Workspace Resolution & Role Permissions
# ==============================================================================

def test_single_workspace_session_restoration_and_listing(client, test_creator_user, auth_headers):
    user, ws = test_creator_user

    # Existing /auth/me restoration returns user profile without tokens
    me_res = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_res.status_code == 200
    assert me_res.json()["id"] == user.id
    assert "access_token" not in me_res.json()

    # Listing workspaces returns deterministic single workspace
    ws_res = client.get("/api/v1/auth/workspaces", headers=auth_headers)
    assert ws_res.status_code == 200
    items = ws_res.json()
    assert len(items) == 1
    assert items[0]["id"] == ws.id
    assert items[0]["role_in_workspace"] == "OWNER"
    assert items[0]["is_active"] is True

    # Ordinary read route operates within single workspace seamlessly
    auto_res = client.get("/api/v1/automations", headers=auth_headers)
    assert auto_res.status_code == 200


def test_multi_workspace_deterministic_default_and_explicit_selection(client, db_session):
    user_b, ws_b, _ = _create_user_with_workspace(db_session, "owner_b@woka.io", "CREATOR", "Owner B")
    # Create user_a AFTER ws_b, and add user_a as MEMBER in ws_b BEFORE or alongside owned ws_a
    user_a, ws_a, _ = _create_user_with_workspace(db_session, "owner_a@woka.io", "CREATOR", "Owner A")
    _, ws_c, _ = _create_user_with_workspace(db_session, "owner_c@woka.io", "CREATOR", "Owner C")

    from datetime import datetime, timezone, timedelta
    invited_membership = WorkspaceMember(
        workspace_id=ws_b.id,
        user_id=user_a.id,
        role_in_workspace="ADMIN",
        created_at=datetime.now(timezone.utc) - timedelta(days=30),
    )
    db_session.add(invited_membership)
    db_session.commit()

    # Token without workspace_id deterministically resolves user_a's owned ws_a
    bare_token = create_access_token(data={"sub": user_a.id, "role": user_a.role})
    bare_headers = {"Authorization": f"Bearer {bare_token}"}

    # Seed distinct invoice per workspace to observe active workspace resolution
    inv_a = client.post("/api/v1/invoices", json={
        "client_name": "Workspace A Client",
        "client_email": "a@client.io",
        "due_date": "2026-12-01",
        "line_items": [{"description": "A", "quantity": 1, "unit_price": 100, "total": 100}],
    }, headers={**bare_headers, "X-Workspace-Id": ws_a.id})
    assert inv_a.status_code == 201

    inv_b = client.post("/api/v1/invoices", json={
        "client_name": "Workspace B Client",
        "client_email": "b@client.io",
        "due_date": "2026-12-01",
        "line_items": [{"description": "B", "quantity": 1, "unit_price": 200, "total": 200}],
    }, headers={**bare_headers, "X-Workspace-Id": ws_b.id})
    assert inv_b.status_code == 201

    # Default without header deterministically selects owned ws_a
    default_list = client.get("/api/v1/invoices", headers=bare_headers)
    assert default_list.status_code == 200
    assert [i["client_name"] for i in default_list.json()] == ["Workspace A Client"]

    # Explicit valid header selects ws_b
    ws_b_list = client.get("/api/v1/invoices", headers={**bare_headers, "X-Workspace-Id": ws_b.id})
    assert ws_b_list.status_code == 200
    assert [i["client_name"] for i in ws_b_list.json()] == ["Workspace B Client"]

    # Workspace selection endpoint issues scoped token for ws_b
    select_res = client.post("/api/v1/auth/workspaces/select", json={"workspace_id": ws_b.id}, headers=bare_headers)
    assert select_res.status_code == 200
    ws_b_token = select_res.json()["access_token"]
    assert select_res.json()["workspace"]["id"] == ws_b.id
    switched_list = client.get("/api/v1/invoices", headers={"Authorization": f"Bearer {ws_b_token}"})
    assert switched_list.status_code == 200
    assert [i["client_name"] for i in switched_list.json()] == ["Workspace B Client"]

    # Invalid workspace IDs or another user's workspace -> 403 Forbidden
    for bad_ws_id in ["", "nonexistent-ws-id", ws_c.id]:
        bad_res = client.get("/api/v1/invoices", headers={**bare_headers, "X-Workspace-Id": bad_ws_id})
        assert bad_res.status_code == 403

    bad_select = client.post("/api/v1/auth/workspaces/select", json={"workspace_id": ws_c.id}, headers=bare_headers)
    assert bad_select.status_code == 403


def test_workspace_membership_removal_and_role_permissions(client, db_session):
    owner, ws, owner_headers = _create_user_with_workspace(
        db_session, "ws_owner@woka.io", "CREATOR", "WS Owner", ig_user_id="ig_ws_owner"
    )
    member_user, own_ws, _ = _create_user_with_workspace(
        db_session, "ws_member@woka.io", "CREATOR", "WS Member"
    )
    admin_user, _, _ = _create_user_with_workspace(
        db_session, "ws_admin@woka.io", "CREATOR", "WS Admin"
    )

    member_link = WorkspaceMember(workspace_id=ws.id, user_id=member_user.id, role_in_workspace="MEMBER")
    admin_link = WorkspaceMember(workspace_id=ws.id, user_id=admin_user.id, role_in_workspace="ADMIN")
    db_session.add_all([member_link, admin_link])
    db_session.commit()

    # Member selects ws -> gets ws-scoped token
    member_own_headers = {"Authorization": f"Bearer {create_access_token(data={'sub': member_user.id, 'role': member_user.role, 'workspace_id': own_ws.id})}"}
    select_member = client.post("/api/v1/auth/workspaces/select", json={"workspace_id": ws.id}, headers=member_own_headers)
    assert select_member.status_code == 200
    member_ws_headers = {"Authorization": f"Bearer {select_member.json()['access_token']}"}

    # MEMBER can read subscription and automations
    assert client.get("/api/v1/subscriptions/current", headers=member_ws_headers).status_code == 200
    assert client.get("/api/v1/automations", headers=member_ws_headers).status_code == 200

    # MEMBER cannot upgrade plan or modify Instagram integration -> 403 Forbidden
    assert client.post("/api/v1/subscriptions/upgrade", json={"target_tier": "PRO"}, headers=member_ws_headers).status_code == 403
    assert client.post("/api/v1/instagram/disconnect", headers=member_ws_headers).status_code == 403
    assert client.post("/api/v1/instagram/sandbox/toggle", json={"enabled": True}, headers=member_ws_headers).status_code == 403
    assert client.get("/api/v1/instagram/oauth-url", headers=member_ws_headers).status_code == 403

    # ADMIN can upgrade plan and manage Instagram integration
    admin_ws_headers = {
        "Authorization": f"Bearer {create_access_token(data={'sub': admin_user.id, 'role': admin_user.role, 'workspace_id': ws.id})}"
    }
    assert client.post("/api/v1/subscriptions/upgrade", json={"target_tier": "PRO"}, headers=admin_ws_headers).status_code == 200
    assert client.get("/api/v1/instagram/oauth-url", headers=admin_ws_headers).status_code == 200
    assert client.post("/api/v1/instagram/sandbox/toggle", json={"enabled": True}, headers=admin_ws_headers).status_code == 200

    # Remove member_user's membership from ws
    db_session.delete(member_link)
    db_session.commit()

    # Existing ws-scoped token AND explicit X-Workspace-Id header are immediately denied (403)
    assert client.get("/api/v1/automations", headers=member_ws_headers).status_code == 403
    assert client.get("/api/v1/automations", headers={**member_own_headers, "X-Workspace-Id": ws.id}).status_code == 403

    # Verify ordinary requests with zero memberships do NOT silently create a workspace
    no_ws_user = User(
        email="orphaned@woka.io",
        hashed_password=get_password_hash("Password123!"),
        full_name="Orphaned User",
        role="CREATOR",
        is_active=True,
    )
    db_session.add(no_ws_user)
    db_session.commit()
    orphan_headers = {"Authorization": f"Bearer {create_access_token(data={'sub': no_ws_user.id, 'role': 'CREATOR'})}"}
    ws_count_before = db_session.query(Workspace).count()
    assert client.get("/api/v1/automations", headers=orphan_headers).status_code == 403
    assert db_session.query(Workspace).count() == ws_count_before


# ==============================================================================
# 2. Media Kit Privacy
# ==============================================================================

def test_media_kit_privacy_inquiry_and_notifications(client, db_session, test_creator_user, auth_headers):
    user, ws = test_creator_user
    inquiry_payload = {
        "brand_name": "Acme Co",
        "contact_email": "deals@acme.com",
        "project_scope": "1x Reel Sponsorship",
        "budget": "$1500",
        "message": "Interested in a Q4 launch Reel.",
    }

    # 1. Public profile accepts inquiry and creates notification
    pub_res = client.post("/api/v1/media-kit/public/testcreator/inquire", json=inquiry_payload)
    assert pub_res.status_code == 200
    assert pub_res.json()["status"] == "SUCCESS"
    notifs = db_session.query(Notification).filter(Notification.user_id == user.id).all()
    assert len(notifs) == 1

    # 2. Toggle profile to private
    upd_res = client.put("/api/v1/media-kit/my-profile", json={"is_public": False}, headers=auth_headers)
    assert upd_res.status_code == 200
    assert upd_res.json()["is_public"] is False

    # Owner can still read own private profile
    owner_read = client.get("/api/v1/media-kit/my-profile", headers=auth_headers)
    assert owner_read.status_code == 200
    assert owner_read.json()["is_public"] is False

    # Public fetch and inquiry on private profile return 404 identical to nonexistent slug
    priv_get = client.get("/api/v1/media-kit/public/testcreator")
    priv_inq = client.post("/api/v1/media-kit/public/testcreator/inquire", json=inquiry_payload)
    miss_get = client.get("/api/v1/media-kit/public/no_such_slug_999")
    miss_inq = client.post("/api/v1/media-kit/public/no_such_slug_999/inquire", json=inquiry_payload)

    assert priv_get.status_code == 404
    assert priv_inq.status_code == 404
    assert miss_get.status_code == 404
    assert miss_inq.status_code == 404
    assert priv_inq.json()["detail"] == miss_inq.json()["detail"]

    # Ensure no additional notifications were created for blocked private/missing inquiries
    notifs_after = db_session.query(Notification).filter(Notification.user_id == user.id).all()
    assert len(notifs_after) == 1


# ==============================================================================
# 3. Reel Thumbnail Authorization
# ==============================================================================

def test_reel_thumbnail_authorization_and_path_traversal(client, db_session, test_creator_user, auth_headers):
    import app.services.reel_intelligence_service as ris

    _, ws_a = test_creator_user
    _, ws_b, headers_b = _create_user_with_workspace(db_session, "thumb_other@woka.io", "CREATOR", "Thumb Other")

    thumb_dir_a = os.path.join(ris.STORAGE_BASE_DIR, ws_a.id, "thumbnails")
    os.makedirs(thumb_dir_a, exist_ok=True)
    thumb_name = "thumb_secure_test.jpg"
    thumb_path_a = os.path.join(thumb_dir_a, thumb_name)
    jpeg_stub = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"

    try:
        with open(thumb_path_a, "wb") as f:
            f.write(jpeg_stub)

        # 1. Unauthenticated request -> 401
        unauth = client.get(f"/api/v1/reel-intelligence/thumbnails/{thumb_name}")
        assert unauth.status_code == 401

        # 2. Authorized owning workspace request -> 200 OK
        auth_ok = client.get(f"/api/v1/reel-intelligence/thumbnails/{thumb_name}", headers=auth_headers)
        assert auth_ok.status_code == 200
        assert auth_ok.content == jpeg_stub

        # 3. Signed URL works strictly for its scoped workspace + filename
        valid_sig = create_thumbnail_signature_token(ws_a.id, thumb_name, expires_seconds=60)
        sig_ok = client.get(f"/api/v1/reel-intelligence/thumbnails/{thumb_name}?token={valid_sig}")
        assert sig_ok.status_code == 200
        assert sig_ok.content == jpeg_stub

        # Signed URL cannot be reused for another filename or when expired/tampered
        assert client.get(f"/api/v1/reel-intelligence/thumbnails/other.jpg?token={valid_sig}").status_code == 401
        expired_sig = create_thumbnail_signature_token(ws_a.id, thumb_name, expires_seconds=-10)
        assert client.get(f"/api/v1/reel-intelligence/thumbnails/{thumb_name}?token={expired_sig}").status_code == 401
        assert client.get(f"/api/v1/reel-intelligence/thumbnails/{thumb_name}?token=tampered").status_code == 401

        # 4. Cross-workspace access even with known filename -> 404 Not Found
        cross_res = client.get(f"/api/v1/reel-intelligence/thumbnails/{thumb_name}", headers=headers_b)
        assert cross_res.status_code == 404

        # 5. Nonexistent file -> 404 Not Found
        missing_res = client.get("/api/v1/reel-intelligence/thumbnails/missing_thumb.jpg", headers=auth_headers)
        assert missing_res.status_code == 404

        # 6. Path traversal attempts -> rejected (400 or 404)
        for traversal in ["../woka.db", "..%2F..%2Fwoka.db", "..\\..\\woka.db", "sub/file.jpg"]:
            trav_res = client.get(f"/api/v1/reel-intelligence/thumbnails/{traversal}", headers=auth_headers)
            assert trav_res.status_code in (400, 404), f"Unexpected status for {traversal}: {trav_res.status_code}"
    finally:
        shutil.rmtree(os.path.join(ris.STORAGE_BASE_DIR, ws_a.id), ignore_errors=True)
        shutil.rmtree(os.path.join(ris.STORAGE_BASE_DIR, ws_b.id), ignore_errors=True)


# ==============================================================================
# 4. Connected Instagram Reel Validation
# ==============================================================================

def test_connected_reel_ownership_type_and_quota_validation(client, db_session, test_creator_user, auth_headers, monkeypatch):
    _, ws_a = test_creator_user
    _, ws_b, headers_b = _create_user_with_workspace(
        db_session, "reel_other@woka.io", "CREATOR", "Reel Other", ig_user_id="ig_other_user_id"
    )

    sub_a = get_workspace_subscription(db_session, ws_a.id)
    initial_quota = sub_a.ai_used_monthly

    # 1. Valid media ID ignores client-supplied untrusted media_url
    spoof_url = "http://127.0.0.1:8080/internal-ssrf.mp4"
    ok_res = client.post(
        "/api/v1/reel-intelligence/jobs/connected",
        json={
            "media_id": "ig_reel_ig_test_user_id_101",
            "title": "Spoofed Title",
            "media_url": spoof_url,
            "thumbnail_url": "http://169.254.169.254/latest/meta-data/",
        },
        headers=auth_headers,
    )
    assert ok_res.status_code == 202
    job_data = ok_res.json()
    assert job_data["source_media_id"] == "ig_reel_ig_test_user_id_101"
    assert job_data["source_url"] != spoof_url
    assert "commondatastorage.googleapis.com" in job_data["source_url"]

    db_session.refresh(sub_a)
    assert sub_a.ai_used_monthly == initial_quota + 1

    # Idempotency preserves job without extra quota burn
    idem_res = client.post(
        "/api/v1/reel-intelligence/jobs/connected",
        json={"media_id": "ig_reel_ig_test_user_id_101"},
        headers=auth_headers,
    )
    assert idem_res.status_code == 202
    assert idem_res.json()["id"] == job_data["id"]
    db_session.refresh(sub_a)
    assert sub_a.ai_used_monthly == initial_quota + 1

    # 2. Nonexistent media ID -> 404, consumes zero quota
    missing_res = client.post(
        "/api/v1/reel-intelligence/jobs/connected",
        json={"media_id": "nonexistent_media_999"},
        headers=auth_headers,
    )
    assert missing_res.status_code == 404
    db_session.refresh(sub_a)
    assert sub_a.ai_used_monthly == initial_quota + 1

    # 3. Media belonging to another workspace's IG account -> 404, consumes zero quota
    foreign_res = client.post(
        "/api/v1/reel-intelligence/jobs/connected",
        json={"media_id": "ig_reel_ig_other_user_id_101"},
        headers=auth_headers,
    )
    assert foreign_res.status_code == 404

    # 4. Invalid media type (IMAGE instead of VIDEO/REELS) -> 422, consumes zero quota
    img_res = client.post(
        "/api/v1/reel-intelligence/jobs/connected",
        json={"media_id": "ig_image_ig_test_user_id_201"},
        headers=auth_headers,
    )
    assert img_res.status_code == 422
    db_session.refresh(sub_a)
    assert sub_a.ai_used_monthly == initial_quota + 1

    # 5. Live (non-sandbox) mocked Instagram media validation rejects invalid types & unknown IDs
    acc_b = db_session.query(InstagramAccount).filter(InstagramAccount.workspace_id == ws_b.id).first()
    acc_b.is_sandbox = False
    db_session.commit()

    import app.services.instagram_service as ig_svc
    monkeypatch.setattr(
        ig_svc,
        "fetch_instagram_media_list",
        lambda *args, **kwargs: [
            {"id": "live_img_1", "media_type": "IMAGE", "media_url": "https://cdn.example.com/img.jpg"},
            {
                "id": "live_reel_ok",
                "media_type": "VIDEO",
                "media_product_type": "REELS",
                "media_url": "https://video.cdninstagram.com/reel_auth.mp4",
            },
        ],
    )
    monkeypatch.setattr(
        ig_svc,
        "fetch_instagram_media_by_id",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        ig_svc,
        "fetch_media_insights",
        lambda *args, **kwargs: {"reach": 5000, "saved": 100, "shares": 50, "total_interactions": 400},
    )
    live_ok_res = client.post(
        "/api/v1/reel-intelligence/jobs/connected",
        json={"media_id": "live_reel_ok", "media_url": "http://127.0.0.1/evil.mp4"},
        headers=headers_b,
    )
    assert live_ok_res.status_code == 202
    assert live_ok_res.json()["source_url"] == "https://video.cdninstagram.com/reel_auth.mp4"

    live_img_res = client.post(
        "/api/v1/reel-intelligence/jobs/connected",
        json={"media_id": "live_img_1"},
        headers=headers_b,
    )
    assert live_img_res.status_code == 422
    live_foreign_res = client.post(
        "/api/v1/reel-intelligence/jobs/connected",
        json={"media_id": "live_not_owned_99"},
        headers=headers_b,
    )
    assert live_foreign_res.status_code == 404

    # 6. Disconnected account -> 400
    acc_b.is_connected = False
    db_session.commit()
    disconn_res = client.post(
        "/api/v1/reel-intelligence/jobs/connected",
        json={"media_id": "ig_reel_ig_other_user_id_101"},
        headers=headers_b,
    )
    assert disconn_res.status_code == 400


# ==============================================================================
# 5. Campaign Authorization Matrix
# ==============================================================================

def test_campaign_role_and_workspace_authorization_matrix(client, db_session):
    _, brand_ws, brand_headers = _create_user_with_workspace(db_session, "camp_brand1@woka.io", "BRAND", "Brand One")
    _, other_brand_ws, other_brand_headers = _create_user_with_workspace(db_session, "camp_brand2@woka.io", "BRAND", "Brand Two")
    creator_user, creator_ws, creator_headers = _create_user_with_workspace(db_session, "camp_creator1@woka.io", "CREATOR", "Creator One")
    _, other_creator_ws, other_creator_headers = _create_user_with_workspace(db_session, "camp_creator2@woka.io", "CREATOR", "Creator Two")
    _, agency_ws, agency_headers = _create_user_with_workspace(db_session, "camp_agency@woka.io", "AGENCY", "Agency One")
    _, admin_ws, admin_headers = _create_user_with_workspace(db_session, "camp_admin@woka.io", "ADMIN", "Admin One")

    # Add creator_user to brand_ws as MEMBER to confirm route role check still blocks CREATOR from brand status updates
    db_session.add(WorkspaceMember(workspace_id=brand_ws.id, user_id=creator_user.id, role_in_workspace="MEMBER"))
    db_session.commit()

    camp_payload = {
        "title": "Authorization Matrix Campaign",
        "description": "Testing strict brand/creator/agency/admin rules",
        "niche": "Tech",
        "budget_min": 500,
        "budget_max": 1200,
        "required_deliverables": ["1x Reel"],
        "submission_deadline": "2026-12-31T00:00:00Z",
    }

    # Brand creates campaign; Creator applies
    camp_id = client.post("/api/v1/campaigns", json=camp_payload, headers=brand_headers).json()["id"]
    app_id = client.post(
        f"/api/v1/campaigns/{camp_id}/apply",
        json={"pitch_text": "Ready to deliver high retention Reel", "proposed_rate": 800},
        headers=creator_headers,
    ).json()["id"]

    # Application status update denials:
    # 1. CREATOR (even with X-Workspace-Id of brand_ws) -> 403
    assert client.put(
        f"/api/v1/campaigns/applications/{app_id}/status?new_status=ACCEPTED",
        headers={**creator_headers, "X-Workspace-Id": brand_ws.id},
    ).status_code == 403
    # 2. Wrong BRAND workspace -> 403
    assert client.put(
        f"/api/v1/campaigns/applications/{app_id}/status?new_status=ACCEPTED",
        headers=other_brand_headers,
    ).status_code == 403
    # 3. Other AGENCY / CREATOR without brand ownership -> 403
    assert client.put(
        f"/api/v1/campaigns/applications/{app_id}/status?new_status=ACCEPTED",
        headers=agency_headers,
    ).status_code == 403
    # 4. Owning BRAND -> 200
    assert client.put(
        f"/api/v1/campaigns/applications/{app_id}/status?new_status=ACCEPTED",
        headers=brand_headers,
    ).status_code == 200

    # Deliverable submission checks:
    deliv_payload = {"deliverable_type": "REEL", "live_url": "https://instagram.com/reel/abc123"}
    # 1. BRAND role -> 403 (even if using own workspace)
    assert client.post(
        f"/api/v1/campaigns/applications/{app_id}/deliverables",
        json=deliv_payload,
        headers=brand_headers,
    ).status_code == 403
    # 2. Different CREATOR workspace -> 403
    assert client.post(
        f"/api/v1/campaigns/applications/{app_id}/deliverables",
        json=deliv_payload,
        headers=other_creator_headers,
    ).status_code == 403
    # 3. Applying CREATOR -> 200
    assert client.post(
        f"/api/v1/campaigns/applications/{app_id}/deliverables",
        json=deliv_payload,
        headers=creator_headers,
    ).status_code == 200

    # Verify AGENCY and ADMIN brand/creator workflows still succeed cleanly
    agency_camp_id = client.post("/api/v1/campaigns", json=camp_payload, headers=agency_headers).json()["id"]
    admin_app_id = client.post(
        f"/api/v1/campaigns/{agency_camp_id}/apply",
        json={"pitch_text": "Admin partner creator pitch", "proposed_rate": 900},
        headers=admin_headers,
    ).json()["id"]
    assert client.put(
        f"/api/v1/campaigns/applications/{admin_app_id}/status?new_status=ACCEPTED",
        headers=agency_headers,
    ).status_code == 200
    assert client.post(
        f"/api/v1/campaigns/applications/{admin_app_id}/deliverables",
        json=deliv_payload,
        headers=admin_headers,
    ).status_code == 200

    admin_camp_id = client.post("/api/v1/campaigns", json=camp_payload, headers=admin_headers).json()["id"]
    agency_app_id = client.post(
        f"/api/v1/campaigns/{admin_camp_id}/apply",
        json={"pitch_text": "Agency creator pitch", "proposed_rate": 950},
        headers=agency_headers,
    ).json()["id"]
    assert client.put(
        f"/api/v1/campaigns/applications/{agency_app_id}/status?new_status=ACCEPTED",
        headers=admin_headers,
    ).status_code == 200
    assert client.post(
        f"/api/v1/campaigns/applications/{agency_app_id}/deliverables",
        json=deliv_payload,
        headers=agency_headers,
    ).status_code == 200


# ==============================================================================
# 6. Automation Validation, Simulation & Isolation
# ==============================================================================

def test_automation_validation_simulation_and_isolation(client, db_session, test_creator_user, auth_headers):
    _, ws_a = test_creator_user
    _, ws_b, headers_b = _create_user_with_workspace(
        db_session, "auto_other@woka.io", "CREATOR", "Auto Other", ig_user_id="ig_auto_other_777"
    )

    base_auto = {
        "name": "Target Validation Rule",
        "trigger_type": "COMMENT",
        "target_post_type": "SPECIFIC_POST",
        "target_post_id": "ig_reel_ig_test_user_id_101",
        "match_type": "CONTAINS_ANY",
        "trigger_keywords": ["guide", "link"],
        "dm_message_template": "Hi {{username}}, check this out!",
        "is_active": True,
        "cooldown_minutes": 60,
    }

    # 1. Cross-workspace or invalid target_post_id rejected
    assert client.post(
        "/api/v1/automations",
        json={**base_auto, "target_post_id": "ig_reel_ig_auto_other_777_101"},
        headers=auth_headers,
    ).status_code == 404
    assert client.post(
        "/api/v1/automations",
        json={**base_auto, "target_post_id": "missing_post_id"},
        headers=auth_headers,
    ).status_code == 404
    assert client.post(
        "/api/v1/automations",
        json={**base_auto, "target_post_id": ""},
        headers=auth_headers,
    ).status_code == 422

    # 2. Keyword validation per match_type
    for match_t in ["EXACT_MATCH", "CONTAINS_ANY", "CONTAINS_ALL"]:
        bad_kw = client.post(
            "/api/v1/automations",
            json={**base_auto, "match_type": match_t, "trigger_keywords": ["", "   "]},
            headers=auth_headers,
        )
        assert bad_kw.status_code == 422

    # ANY_COMMENT allows empty keywords
    any_res = client.post(
        "/api/v1/automations",
        json={**base_auto, "target_post_type": "ALL_POSTS", "target_post_id": None, "match_type": "ANY_COMMENT", "trigger_keywords": []},
        headers=auth_headers,
    )
    assert any_res.status_code == 201
    any_id = any_res.json()["id"]

    # Updating ANY_COMMENT -> CONTAINS_ALL without keywords must fail 422
    bad_upd = client.put(f"/api/v1/automations/{any_id}", json={"match_type": "CONTAINS_ALL"}, headers=auth_headers)
    assert bad_upd.status_code == 422

    # Updating with another workspace's target_post_id fails 404
    bad_target_upd = client.put(
        f"/api/v1/automations/{any_id}",
        json={"target_post_type": "SPECIFIC_POST", "target_post_id": "ig_reel_ig_auto_other_777_101"},
        headers=auth_headers,
    )
    assert bad_target_upd.status_code == 404

    # 3. Valid SPECIFIC_POST automation creation & exact post_id matching
    valid_res = client.post("/api/v1/automations", json=base_auto, headers=auth_headers)
    assert valid_res.status_code == 201
    auto_id = valid_res.json()["id"]

    # Disable ANY_COMMENT rule so simulation specifically tests `auto_id`
    client.put(f"/api/v1/automations/{any_id}", json={"is_active": False}, headers=auth_headers)

    # Simulation on wrong post_id -> NO_MATCH
    wrong_post_sim = client.post(
        "/api/v1/automations/simulate",
        json={
            "automation_id": auto_id,
            "post_id": "ig_reel_ig_test_user_id_102",
            "comment_text": "Please send the guide",
            "comment_author": "fan_one",
        },
        headers=auth_headers,
    )
    assert wrong_post_sim.status_code == 200
    assert wrong_post_sim.json()["matched"] is False

    # Simulation on exact post_id -> clear simulation wording, status SIMULATED, zero live count inflation
    sim_ok = client.post(
        "/api/v1/automations/simulate",
        json={
            "automation_id": auto_id,
            "post_id": "ig_reel_ig_test_user_id_101",
            "comment_text": "Please send the guide",
            "comment_author": "fan_one",
        },
        headers=auth_headers,
    )
    assert sim_ok.status_code == 200
    sim_data = sim_ok.json()
    assert sim_data["matched"] is True
    assert sim_data["status"] == "SIMULATION_SUCCESS"
    assert "no dm was sent to instagram" in sim_data["explanation"].lower()

    auto_after_sim = client.get(f"/api/v1/automations/{auto_id}", headers=auth_headers).json()
    assert auto_after_sim["total_triggered_count"] == 0

    # Repeated simulation for same recipient triggers per-automation cooldown
    sim_cooldown = client.post(
        "/api/v1/automations/simulate",
        json={
            "automation_id": auto_id,
            "post_id": "ig_reel_ig_test_user_id_101",
            "comment_text": "Guide again please",
            "comment_author": "fan_one",
        },
        headers=auth_headers,
    )
    assert sim_cooldown.status_code == 200
    assert sim_cooldown.json()["status"] == "SUPPRESSED_COOLDOWN"

    # Real incoming webhook for same fan is NOT suppressed by dry-run simulator preview
    webhook_payload = {
        "object": "instagram",
        "entry": [{
            "id": "ig_test_user_id",
            "changes": [{
                "field": "comments",
                "value": {
                    "id": "live_comment_after_sim_1",
                    "text": "Send guide!",
                    "from": {"id": "fan_one_ig_id", "username": "fan_one"},
                    "media": {"id": "ig_reel_ig_test_user_id_101"},
                },
            }],
        }],
    }
    raw_wh = json.dumps(webhook_payload).encode()
    sig_wh = "sha256=" + hmac.new(settings.META_APP_SECRET.encode(), raw_wh, hashlib.sha256).hexdigest()
    wh_res = client.post("/api/v1/instagram/webhook", content=raw_wh, headers={"X-Hub-Signature-256": sig_wh})
    assert wh_res.status_code == 200
    assert wh_res.json()["results"][0]["status"] in ("SIMULATED", "SUCCESS")

    # Webhook targeting unknown ig_user_id must NOT fall back to any workspace's connected account
    unknown_wh = {
        "object": "instagram",
        "entry": [{
            "id": "ig_unregistered_account_999",
            "changes": [{
                "field": "comments",
                "value": {
                    "id": "unknown_acc_comment_1",
                    "text": "Send guide!",
                    "from": {"id": "fan_two_ig_id", "username": "fan_two"},
                    "media": {"id": "ig_reel_ig_test_user_id_101"},
                },
            }],
        }],
    }
    raw_unk = json.dumps(unknown_wh).encode()
    sig_unk = "sha256=" + hmac.new(settings.META_APP_SECRET.encode(), raw_unk, hashlib.sha256).hexdigest()
    unk_res = client.post("/api/v1/instagram/webhook", content=raw_unk, headers={"X-Hub-Signature-256": sig_unk})
    assert unk_res.status_code == 200
    assert unk_res.json()["results"] == []

    # 4. Log isolation: Workspace B sees zero logs from Workspace A
    logs_a = client.get("/api/v1/automations/logs", headers=auth_headers).json()
    logs_b = client.get("/api/v1/automations/logs", headers=headers_b).json()
    assert len(logs_a) >= 2
    assert logs_b == []


# ==============================================================================
# 7. Staging Post-Hardening Verification Checks
# ==============================================================================

def test_jwt_workspace_claim_tampering_rejected(client, db_session, test_creator_user):
    from jose import jwt

    user_a, ws_a = test_creator_user
    _, ws_b, _ = _create_user_with_workspace(db_session, "jwt_victim@woka.io", "CREATOR", "JWT Victim")

    # 1. Token claiming workspace_id=ws_b.id even if validly signed is rejected by DB membership verification
    cross_claim_tok = create_access_token(data={"sub": user_a.id, "role": user_a.role, "workspace_id": ws_b.id})
    cross_res = client.get("/api/v1/automations", headers={"Authorization": f"Bearer {cross_claim_tok}"})
    assert cross_res.status_code == 403

    # 2. Tampered / unsigned JWT claim modification rejected at authentication -> 401
    forged_tok = jwt.encode(
        {"sub": user_a.id, "role": user_a.role, "workspace_id": ws_b.id, "type": "access"},
        "wrong-signing-secret",
        algorithm=settings.ALGORITHM,
    )
    forged_res = client.get("/api/v1/automations", headers={"Authorization": f"Bearer {forged_tok}"})
    assert forged_res.status_code == 401


def test_targeted_media_lookup_beyond_150_and_ownership_distinctions(client, db_session, monkeypatch):
    import app.services.instagram_service as ig_svc

    user, ws, headers = _create_user_with_workspace(
        db_session,
        "targeted_ig@woka.io",
        "CREATOR",
        "Targeted IG Creator",
        ig_user_id="ig_owner_150_plus",
        is_sandbox=False,
    )
    account = db_session.query(InstagramAccount).filter(InstagramAccount.workspace_id == ws.id).first()
    sub = get_workspace_subscription(db_session, ws.id)
    start_quota = sub.ai_used_monthly

    # Simulate 150 recent items not containing the older target reel
    monkeypatch.setattr(
        ig_svc,
        "fetch_instagram_media_list",
        lambda *args, **kwargs: [
            {"id": f"recent_item_{i}", "media_type": "VIDEO", "media_url": "https://cdn.example.com/v.mp4"}
            for i in range(150)
        ],
    )
    monkeypatch.setattr(
        ig_svc,
        "fetch_media_insights",
        lambda *args, **kwargs: {"reach": 4200, "saved": 90, "shares": 25, "total_interactions": 310},
    )

    # 1. Targeted lookup confirms ownership via owner.id for >150-item older REEL -> 202
    monkeypatch.setattr(
        ig_svc,
        "fetch_instagram_media_by_id",
        lambda token, mid: {
            "id": mid,
            "media_type": "VIDEO",
            "media_product_type": "REELS",
            "media_url": "https://video.cdninstagram.com/older_reel.mp4",
            "owner": {"id": account.ig_user_id},
            "username": account.username,
        },
    )
    ok_res = client.post(
        "/api/v1/reel-intelligence/jobs/connected",
        json={"media_id": "older_reel_151"},
        headers=headers,
    )
    assert ok_res.status_code == 202
    assert ok_res.json()["source_url"] == "https://video.cdninstagram.com/older_reel.mp4"
    db_session.refresh(sub)
    assert sub.ai_used_monthly == start_quota + 1

    # 2. Confirmed ownership mismatch (belongs to a different IG user) -> 403, zero quota burn
    monkeypatch.setattr(
        ig_svc,
        "fetch_instagram_media_by_id",
        lambda token, mid: {
            "id": mid,
            "media_type": "VIDEO",
            "media_product_type": "REELS",
            "media_url": "https://video.cdninstagram.com/foreign.mp4",
            "owner": {"id": "ig_foreign_account_999"},
            "username": "someone_else",
        },
    )
    mismatch_res = client.post(
        "/api/v1/reel-intelligence/jobs/connected",
        json={"media_id": "foreign_reel_555"},
        headers=headers,
    )
    assert mismatch_res.status_code == 403
    assert "different instagram account" in mismatch_res.json()["detail"].lower()

    # 3. Targeted lookup without verifiable owner proof -> 403 (prevents false acceptance)
    monkeypatch.setattr(
        ig_svc,
        "fetch_instagram_media_by_id",
        lambda token, mid: {
            "id": mid,
            "media_type": "VIDEO",
            "media_product_type": "REELS",
            "media_url": "https://video.cdninstagram.com/unverified.mp4",
        },
    )
    unverified_res = client.post(
        "/api/v1/reel-intelligence/jobs/connected",
        json={"media_id": "unverified_owner_reel"},
        headers=headers,
    )
    assert unverified_res.status_code == 403

    # 4. Inaccessible media (MetaPermissionError) -> 403 distinct from nonexistent (404)
    def raise_perm_err(*args, **kwargs):
        raise ig_svc.MetaPermissionError("OAuth permission denied for target media", code=200)

    monkeypatch.setattr(ig_svc, "fetch_instagram_media_by_id", raise_perm_err)
    perm_res = client.post(
        "/api/v1/reel-intelligence/jobs/connected",
        json={"media_id": "inaccessible_media_77"},
        headers=headers,
    )
    assert perm_res.status_code == 403

    # 5. Path injection attempt in media_id -> 422
    inj_res = client.post(
        "/api/v1/reel-intelligence/jobs/connected",
        json={"media_id": "123/insights?foo=bar"},
        headers=headers,
    )
    assert inj_res.status_code == 422

    # Confirm zero extra quota consumed by all rejected attempts
    db_session.refresh(sub)
    assert sub.ai_used_monthly == start_quota + 1


def test_thumbnail_cache_referrer_and_cross_workspace_token_isolation(client, db_session, test_creator_user, auth_headers):
    import app.services.reel_intelligence_service as ris
    from app.models.reel_intelligence import ReelAnalysisJob, ReelReport

    _, ws_a = test_creator_user
    _, ws_b, headers_b = _create_user_with_workspace(db_session, "thumb_b2@woka.io", "CREATOR", "Thumb B2")

    thumb_dir_a = os.path.join(ris.STORAGE_BASE_DIR, ws_a.id, "thumbnails")
    thumb_dir_b = os.path.join(ris.STORAGE_BASE_DIR, ws_b.id, "thumbnails")
    os.makedirs(thumb_dir_a, exist_ok=True)
    os.makedirs(thumb_dir_b, exist_ok=True)
    jpeg_a = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00A\xff\xd9"
    jpeg_b = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00B\xff\xd9"

    try:
        with open(os.path.join(thumb_dir_a, "rep_thumb_a.jpg"), "wb") as f:
            f.write(jpeg_a)
        with open(os.path.join(thumb_dir_b, "rep_thumb_b.jpg"), "wb") as f:
            f.write(jpeg_b)

        # Create report for ws_a and verify API returns signed URL that loads cleanly with security headers
        job_a = ReelAnalysisJob(
            workspace_id=ws_a.id,
            analysis_mode="VIDEO_UPLOAD",
            input_type="upload",
            status="COMPLETED",
            progress_percent=100,
            stage_message="Done",
        )
        db_session.add(job_a)
        db_session.flush()
        rep_a = ReelReport(
            workspace_id=ws_a.id,
            job_id=job_a.id,
            title="Signed Thumb Report",
            analysis_mode="VIDEO_UPLOAD",
            thumbnail_url="/api/v1/reel-intelligence/thumbnails/rep_thumb_a.jpg",
        )
        db_session.add(rep_a)
        db_session.commit()

        rep_resp = client.get("/api/v1/reel-intelligence/reports", headers=auth_headers)
        assert rep_resp.status_code == 200
        reports = rep_resp.json()
        target_rep = next(r for r in reports if r["id"] == rep_a.id)
        signed_url = target_rep["thumbnail_url"]
        assert "/api/v1/reel-intelligence/thumbnails/rep_thumb_a.jpg?token=" in signed_url

        # Signed URL succeeds without Bearer header and includes cache + referrer protections
        thumb_res = client.get(signed_url)
        assert thumb_res.status_code == 200
        assert thumb_res.content == jpeg_a
        assert "no-store" in thumb_res.headers.get("cache-control", "").lower()
        assert "private" in thumb_res.headers.get("cache-control", "").lower()
        assert thumb_res.headers.get("pragma", "").lower() == "no-cache"
        assert thumb_res.headers.get("referrer-policy", "").lower() == "no-referrer"
        assert thumb_res.headers.get("x-content-type-options", "").lower() == "nosniff"

        # Signed token from ws_a cannot access ws_b file (401 filename mismatch)
        tok_a = signed_url.split("?token=")[1]
        assert client.get(f"/api/v1/reel-intelligence/thumbnails/rep_thumb_b.jpg?token={tok_a}").status_code == 401

        # Regular Bearer access JWT cannot be passed as query ?token=
        access_jwt = auth_headers["Authorization"].split(" ")[1]
        assert client.get(f"/api/v1/reel-intelligence/thumbnails/rep_thumb_a.jpg?token={access_jwt}").status_code == 401
    finally:
        shutil.rmtree(os.path.join(ris.STORAGE_BASE_DIR, ws_a.id), ignore_errors=True)
        shutil.rmtree(os.path.join(ris.STORAGE_BASE_DIR, ws_b.id), ignore_errors=True)


def test_startup_schema_verification_rejects_unmigrated_staging_db(monkeypatch):
    from sqlalchemy import create_engine
    from app.main import verify_database_schema_ready

    orig_env = settings.ENVIRONMENT
    try:
        settings.ENVIRONMENT = "staging"
        empty_engine = create_engine("sqlite:///:memory:")
        with pytest.raises(RuntimeError, match="alembic upgrade head"):
            verify_database_schema_ready(empty_engine)
    finally:
        settings.ENVIRONMENT = orig_env
        empty_engine.dispose()
