import pytest
from app.models.user import User, Workspace, WorkspaceMember
from app.models.instagram import InstagramAccount
from app.models.subscription import Subscription
from app.models.automation import Automation
from app.security import get_password_hash, encrypt_token
from app.services.instagram_service import generate_mock_signed_request
import json

@pytest.fixture
def seeded_reviewer(db_session):
    """Seed the official Meta reviewer account into the test session."""
    reviewer = User(
        email="meta-reviewer@woka.io",
        hashed_password=get_password_hash("MetaReviewer2026!"),
        full_name="Meta Reviewer",
        role="CREATOR",
        is_active=True,
        is_verified=True
    )
    db_session.add(reviewer)
    db_session.flush()

    reviewer_ws = Workspace(name="Meta Reviewer Sandbox", owner_id=reviewer.id)
    db_session.add(reviewer_ws)
    db_session.flush()

    db_session.add(WorkspaceMember(workspace_id=reviewer_ws.id, user_id=reviewer.id, role_in_workspace="OWNER"))
    db_session.add(Subscription(
        workspace_id=reviewer_ws.id,
        plan_tier="PRO",
        status="ACTIVE",
        dm_limit_monthly=2000,
        dm_used_monthly=12
    ))

    ig_account = InstagramAccount(
        workspace_id=reviewer_ws.id,
        ig_user_id="ig_demo_meta_reviewer_123",
        username="creator_woka_demo",
        name="Woka Demo Creator",
        encrypted_access_token=encrypt_token("sandbox_access_token_reviewer_valid"),
        is_connected=True,
        is_sandbox=True,
        followers_count=12400,
        media_count=48
    )
    db_session.add(ig_account)
    db_session.flush()

    auto = Automation(
        workspace_id=reviewer_ws.id,
        ig_account_id=ig_account.id,
        name="Guide Lead Magnet",
        trigger_type="COMMENT",
        target_post_type="ALL_POSTS",
        match_type="CONTAINS_ANY",
        trigger_keywords=json.dumps(["guide", "ebook", "free"]),
        dm_message_template="Hi {{username}}, here is your free guide: https://woka.io/creator-guide",
        reply_comment_template="Just sent the guide to your DMs {{username}}! 🚀",
        is_active=True,
        cooldown_minutes=60,
        total_triggered_count=12
    )
    db_session.add(auto)

    # Also add a separate user/workspace to test isolation
    other_creator = User(
        email="other@woka.io",
        hashed_password=get_password_hash("OtherPass123!"),
        full_name="Other Creator",
        role="CREATOR",
        is_active=True
    )
    db_session.add(other_creator)
    db_session.flush()
    other_ws = Workspace(name="Other Studio", owner_id=other_creator.id)
    db_session.add(other_ws)
    db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=other_ws.id, user_id=other_creator.id, role_in_workspace="OWNER"))
    other_ig = InstagramAccount(
        workspace_id=other_ws.id,
        ig_user_id="ig_demo_other_999",
        username="other_creator_demo",
        name="Other Creator",
        encrypted_access_token=encrypt_token("sandbox_other"),
        is_connected=True,
        is_sandbox=True
    )
    db_session.add(other_ig)
    db_session.flush()

    db_session.add(Automation(
        workspace_id=other_ws.id,
        ig_account_id=other_ig.id,
        name="Secret Other Automation",
        trigger_type="COMMENT",
        target_post_type="ALL_POSTS",
        match_type="EXACT",
        trigger_keywords=json.dumps(["secret"]),
        dm_message_template="Secret DM",
        is_active=True
    ))

    db_session.commit()
    return reviewer, reviewer_ws, ig_account

def test_reviewer_login_and_credentials(client, seeded_reviewer):
    """Verify that the reviewer credentials documented in META_APP_REVIEW.md authenticate cleanly."""
    res = client.post("/api/v1/auth/login", json={
        "email": "meta-reviewer@woka.io",
        "password": "MetaReviewer2026!"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "CREATOR"
    assert data["user"]["email"] == "meta-reviewer@woka.io"

def test_reviewer_privileges_are_strictly_creator(client, seeded_reviewer):
    """Verify that the reviewer account cannot perform admin or brand actions."""
    login_res = client.post("/api/v1/auth/login", json={
        "email": "meta-reviewer@woka.io",
        "password": "MetaReviewer2026!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Admin endpoints must return 403 Forbidden
    stats_res = client.get("/api/v1/admin/stats", headers=headers)
    assert stats_res.status_code == 403

    users_res = client.get("/api/v1/admin/users", headers=headers)
    assert users_res.status_code == 403

    # 2. Brand-only campaign creation must return 403 Forbidden
    campaign_res = client.post("/api/v1/campaigns", json={
        "title": "Unauthorized Campaign",
        "description": "Should fail",
        "niche": "Tech",
        "budget_min": 100,
        "budget_max": 200,
        "required_deliverables": ["1x Reel"],
        "submission_deadline": "2026-12-31T00:00:00Z"
    }, headers=headers)
    assert campaign_res.status_code == 403

def test_reviewer_workspace_and_automation_isolation(client, seeded_reviewer):
    """Verify that the reviewer can only see their own workspace's automations."""
    login_res = client.post("/api/v1/auth/login", json={
        "email": "meta-reviewer@woka.io",
        "password": "MetaReviewer2026!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    automations_res = client.get("/api/v1/automations", headers=headers)
    assert automations_res.status_code == 200
    automations = automations_res.json()
    assert len(automations) == 1
    assert automations[0]["name"] == "Guide Lead Magnet"

def test_reviewer_instagram_sandbox_mode(client, seeded_reviewer):
    """Verify that the reviewer's connected account is explicitly marked as sandbox demo."""
    login_res = client.post("/api/v1/auth/login", json={
        "email": "meta-reviewer@woka.io",
        "password": "MetaReviewer2026!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ig_res = client.get("/api/v1/instagram/account", headers=headers)
    assert ig_res.status_code == 200
    account_data = ig_res.json()
    assert account_data["is_connected"] is True
    assert account_data["is_sandbox"] is True
    assert account_data["username"] == "creator_woka_demo"
    # Verify access token is never leaked in plaintext
    assert "encrypted_access_token" not in account_data

def test_meta_deletion_callback_fulfillment(client, seeded_reviewer):
    """Verify Meta Data Deletion callback produces the exact required JSON and URL structure."""
    _, _, ig_account = seeded_reviewer
    signed_request = generate_mock_signed_request(user_id=ig_account.ig_user_id)

    res = client.post(
        "/api/v1/instagram/data-deletion",
        data={"signed_request": signed_request}
    )
    assert res.status_code == 200
    data = res.json()
    assert "url" in data
    assert "confirmation_code" in data
    assert data["confirmation_code"].startswith("woka_del_")
    assert f"deletion-status?code={data['confirmation_code']}" in data["url"]
