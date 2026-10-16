import pytest

def test_creator_cannot_create_campaign(client, test_creator_user):
    user, ws = test_creator_user
    # Creator token
    login_res = client.post("/api/v1/auth/login", json={"email": "test_creator@woka.io", "password": "TestPass123!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to post a campaign as CREATOR -> 403 Forbidden
    res = client.post("/api/v1/campaigns", json={
        "title": "Unauthorized Campaign",
        "description": "Should fail with 403",
        "niche": "Tech",
        "budget_min": 500,
        "budget_max": 1000,
        "required_deliverables": ["1x Reel"],
        "submission_deadline": "2026-12-01T00:00:00Z"
    }, headers=headers)
    assert res.status_code == 403

def test_brand_cannot_apply_to_own_campaign(client):
    # 1. Brand role user trying to apply is blocked by RBAC (403 Forbidden)
    reg_brand = client.post("/api/v1/auth/register", json={
        "email": "self_brand@woka.io",
        "password": "Password123!",
        "full_name": "Self Brand",
        "role": "BRAND"
    })
    token_brand = reg_brand.json()["access_token"]
    headers_brand = {"Authorization": f"Bearer {token_brand}"}

    camp_res = client.post("/api/v1/campaigns", json={
        "title": "Self Apply Campaign",
        "description": "Brand testing self application",
        "niche": "Fashion",
        "budget_min": 1000,
        "budget_max": 2000,
        "required_deliverables": ["1x Story"],
        "submission_deadline": "2026-12-01T00:00:00Z"
    }, headers=headers_brand)
    assert camp_res.status_code == 201
    camp_id = camp_res.json()["id"]

    # Brand role cannot apply -> 403 Forbidden
    apply_res = client.post(f"/api/v1/campaigns/{camp_id}/apply", json={
        "pitch_text": "I want to sponsor myself!",
        "proposed_rate": 1500
    }, headers=headers_brand)
    assert apply_res.status_code == 403

    # 2. An AGENCY user (allowed to create campaigns and apply) cannot apply to their own campaign
    reg_agency = client.post("/api/v1/auth/register", json={
        "email": "self_agency@woka.io",
        "password": "Password123!",
        "full_name": "Self Agency",
        "role": "AGENCY"
    })
    token_agency = reg_agency.json()["access_token"]
    headers_agency = {"Authorization": f"Bearer {token_agency}"}

    agency_camp = client.post("/api/v1/campaigns", json={
        "title": "Agency Campaign",
        "description": "Agency campaign test",
        "niche": "Tech",
        "budget_min": 1000,
        "budget_max": 2000,
        "required_deliverables": ["1x Video"],
        "submission_deadline": "2026-12-01T00:00:00Z"
    }, headers=headers_agency)
    agency_camp_id = agency_camp.json()["id"]

    # Agency applying to its own campaign -> 400 Bad Request
    self_apply = client.post(f"/api/v1/campaigns/{agency_camp_id}/apply", json={
        "pitch_text": "Self application attempt",
        "proposed_rate": 1500
    }, headers=headers_agency)
    assert self_apply.status_code == 400
    assert "own campaign" in self_apply.json()["detail"].lower()


def test_application_lifecycle_and_deliverables_guard(client):
    # Register brand
    brand_res = client.post("/api/v1/auth/register", json={
        "email": "lifecycle_brand@woka.io",
        "password": "Password123!",
        "full_name": "Lifecycle Brand",
        "role": "BRAND"
    })
    token_brand = brand_res.json()["access_token"]
    headers_brand = {"Authorization": f"Bearer {token_brand}"}

    # Register creator
    creator_res = client.post("/api/v1/auth/register", json={
        "email": "lifecycle_creator@woka.io",
        "password": "Password123!",
        "full_name": "Lifecycle Creator",
        "role": "CREATOR"
    })
    token_creator = creator_res.json()["access_token"]
    headers_creator = {"Authorization": f"Bearer {token_creator}"}

    # Brand creates campaign
    camp_res = client.post("/api/v1/campaigns", json={
        "title": "Beauty Product Launch",
        "description": "Showcase our new serum",
        "niche": "Beauty",
        "budget_min": 800,
        "budget_max": 1500,
        "required_deliverables": ["1x Reel"],
        "submission_deadline": "2026-12-31T00:00:00Z"
    }, headers=headers_brand)
    camp_id = camp_res.json()["id"]

    # Creator applies
    app_res = client.post(f"/api/v1/campaigns/{camp_id}/apply", json={
        "pitch_text": "I specialize in clean beauty reviews with 8% engagement rate.",
        "proposed_rate": 1200
    }, headers=headers_creator)
    assert app_res.status_code == 201
    app_id = app_res.json()["id"]

    # Creator attempts to submit deliverable while status is APPLIED -> 400 Bad Request
    early_deliv = client.post(f"/api/v1/campaigns/applications/{app_id}/deliverables", json={
        "deliverable_type": "REEL",
        "live_url": "https://instagram.com/reel/12345"
    }, headers=headers_creator)
    assert early_deliv.status_code == 400
    assert "accepted applications" in early_deliv.json()["detail"].lower()

    # Brand attempts invalid transition APPLIED -> COMPLETED -> 400 Bad Request
    invalid_trans = client.put(f"/api/v1/campaigns/applications/{app_id}/status?new_status=COMPLETED", headers=headers_brand)
    assert invalid_trans.status_code == 400
    assert "invalid state transition" in invalid_trans.json()["detail"].lower()

    # Brand accepts the application -> 200 OK
    accept_res = client.put(f"/api/v1/campaigns/applications/{app_id}/status?new_status=ACCEPTED", headers=headers_brand)
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "ACCEPTED"

    # Now creator can submit deliverable
    valid_deliv = client.post(f"/api/v1/campaigns/applications/{app_id}/deliverables", json={
        "deliverable_type": "REEL",
        "live_url": "https://instagram.com/reel/validreel123"
    }, headers=headers_creator)
    assert valid_deliv.status_code == 200
    assert valid_deliv.json()["status"] == "IN_REVIEW"

    # Brand completes the application
    complete_res = client.put(f"/api/v1/campaigns/applications/{app_id}/status?new_status=COMPLETED", headers=headers_brand)
    assert complete_res.status_code == 200
    assert complete_res.json()["status"] == "COMPLETED"

    # Attempting to move back out of COMPLETED terminal state fails
    terminal_trans = client.put(f"/api/v1/campaigns/applications/{app_id}/status?new_status=ACCEPTED", headers=headers_brand)
    assert terminal_trans.status_code == 400

def test_invoice_terminal_state_protection(client):
    reg_user = client.post("/api/v1/auth/register", json={
        "email": "inv_guard@woka.io",
        "password": "Password123!",
        "full_name": "Invoice Guard",
        "role": "CREATOR"
    })
    token = reg_user.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create invoice
    inv_res = client.post("/api/v1/invoices", json={
        "client_name": "Terminal Client",
        "client_email": "test@terminal.com",
        "due_date": "2026-11-15",
        "line_items": [{"description": "Item", "quantity": 1, "unit_price": 400, "total": 400}]
    }, headers=headers)
    inv_id = inv_res.json()["id"]

    # Mark as PAID
    paid_res = client.put(f"/api/v1/invoices/{inv_id}/status?status=PAID", headers=headers)
    assert paid_res.status_code == 200
    assert paid_res.json()["status"] == "PAID"

    # Attempting to change status of PAID invoice -> 400 Bad Request
    revert_res = client.put(f"/api/v1/invoices/{inv_id}/status?status=DRAFT", headers=headers)
    assert revert_res.status_code == 400
    assert "already paid" in revert_res.json()["detail"].lower()
