import pytest

def test_tenant_cannot_access_or_modify_other_automations(client, test_creator_user):
    user_a, ws_a = test_creator_user
    # Login/token for User A
    login_a = client.post("/api/v1/auth/login", json={"email": "test_creator@woka.io", "password": "TestPass123!"})
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register User B
    reg_b = client.post("/api/v1/auth/register", json={
        "email": "user_b@woka.io",
        "password": "Password123!",
        "full_name": "User B",
        "role": "CREATOR"
    })
    token_b = reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates automation
    create_res = client.post("/api/v1/automations", json={
        "name": "Secret Automation A",
        "trigger_type": "COMMENT",
        "target_post_type": "ALL_POSTS",
        "match_type": "CONTAINS_ANY",
        "trigger_keywords": ["secret"],
        "dm_message_template": "Secret message from A",
        "is_active": True
    }, headers=headers_a)
    assert create_res.status_code == 201
    auto_id = create_res.json()["id"]

    # User B lists automations -> must NOT see User A's automation
    list_b = client.get("/api/v1/automations", headers=headers_b)
    assert list_b.status_code == 200
    auto_ids_b = [a["id"] for a in list_b.json()]
    assert auto_id not in auto_ids_b

    # User B attempts to update User A's automation -> 404 Not Found
    update_res = client.put(f"/api/v1/automations/{auto_id}", json={"name": "Hacked"}, headers=headers_b)
    assert update_res.status_code == 404

    # User B attempts to delete User A's automation -> 404 Not Found
    delete_res = client.delete(f"/api/v1/automations/{auto_id}", headers=headers_b)
    assert delete_res.status_code == 404

def test_tenant_cannot_access_or_update_other_invoices(client):
    # User A creates invoice
    reg_a = client.post("/api/v1/auth/register", json={
        "email": "inv_a@woka.io",
        "password": "Password123!",
        "full_name": "Invoice User A",
        "role": "CREATOR"
    })
    token_a = reg_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    inv_res = client.post("/api/v1/invoices", json={
        "client_name": "Acme Brand",
        "client_email": "billing@acme.com",
        "due_date": "2026-11-01",
        "line_items": [{"description": "Sponsored Reel", "quantity": 1, "unit_price": 500, "total": 500}]
    }, headers=headers_a)
    assert inv_res.status_code == 201
    inv_id = inv_res.json()["id"]

    # User B
    reg_b = client.post("/api/v1/auth/register", json={
        "email": "inv_b@woka.io",
        "password": "Password123!",
        "full_name": "Invoice User B",
        "role": "CREATOR"
    })
    token_b = reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B tries to fetch User A's invoice directly -> 404
    get_res = client.get(f"/api/v1/invoices/{inv_id}", headers=headers_b)
    assert get_res.status_code == 404

    # User B tries to update User A's invoice status -> 404
    status_res = client.put(f"/api/v1/invoices/{inv_id}/status?status=PAID", headers=headers_b)
    assert status_res.status_code == 404

def test_tenant_cannot_view_other_brand_proposals(client):
    # Brand 1
    reg_b1 = client.post("/api/v1/auth/register", json={
        "email": "brand1@woka.io",
        "password": "Password123!",
        "full_name": "Brand One",
        "role": "BRAND"
    })
    token_b1 = reg_b1.json()["access_token"]
    headers_b1 = {"Authorization": f"Bearer {token_b1}"}

    # Brand 1 creates a campaign
    camp_res = client.post("/api/v1/campaigns", json={
        "title": "Summer Launch 2026",
        "description": "Exclusive campaign looking for fitness creators",
        "niche": "Fitness",
        "budget_min": 1000,
        "budget_max": 3000,
        "required_deliverables": ["1x Reel"],
        "submission_deadline": "2026-12-01T00:00:00Z"
    }, headers=headers_b1)
    assert camp_res.status_code == 201
    camp_id = camp_res.json()["id"]

    # Brand 2
    reg_b2 = client.post("/api/v1/auth/register", json={
        "email": "brand2@woka.io",
        "password": "Password123!",
        "full_name": "Brand Two",
        "role": "BRAND"
    })
    token_b2 = reg_b2.json()["access_token"]
    headers_b2 = {"Authorization": f"Bearer {token_b2}"}

    # Brand 2 attempts to view applications for Brand 1's campaign -> 403 Forbidden
    apps_res = client.get(f"/api/v1/campaigns/{camp_id}/applications", headers=headers_b2)
    assert apps_res.status_code == 403
    assert "not authorized" in apps_res.json()["detail"].lower()
