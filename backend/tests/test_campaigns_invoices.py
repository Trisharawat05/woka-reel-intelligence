from datetime import date

def test_rate_calculator(client):
    res = client.post("/api/v1/invoices/calculate-rate", json={
        "followers": 50000,
        "avg_reach": 20000,
        "engagement_rate": 4.5,
        "deliverable_type": "REEL"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["recommended_rate"] > 0
    assert data["min_rate"] < data["recommended_rate"]
    assert data["max_rate"] > data["recommended_rate"]
    assert "reach" in data["reasoning"]

def test_create_and_list_invoice(client, auth_headers):
    payload = {
        "client_name": "Acme Brand Inc",
        "client_email": "billing@acme.com",
        "currency": "USD",
        "due_date": str(date.today()),
        "line_items": [
            {"description": "1x Dedicated Instagram Reel", "quantity": 1, "unit_price": 500.0, "total": 500.0},
            {"description": "2x Story Frames", "quantity": 2, "unit_price": 75.0, "total": 150.0}
        ],
        "notes": "Payment via wire within 30 days."
    }
    res = client.post("/api/v1/invoices", json=payload, headers=auth_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["total_amount"] == 650.0
    assert data["client_name"] == "Acme Brand Inc"
    assert data["status"] == "DRAFT"

    # List invoices
    list_res = client.get("/api/v1/invoices", headers=auth_headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

def test_ai_studio_caption_and_hooks(client, auth_headers):
    # Caption
    caption_res = client.post("/api/v1/ai-studio/caption", json={
        "topic": "productivity tools for creators",
        "tone": "Engaging",
        "target_cta": "Comment for Link",
        "include_emojis": True
    }, headers=auth_headers)
    assert caption_res.status_code == 200
    data = caption_res.json()
    assert "caption" in data
    assert len(data["suggested_hashtags"]) > 0

    # Hooks
    hook_res = client.post("/api/v1/ai-studio/hooks", json={
        "topic": "monetizing Instagram",
        "style": "Curiosity Gap"
    }, headers=auth_headers)
    assert hook_res.status_code == 200
    assert len(hook_res.json()["hooks"]) > 0

def test_public_media_kit(client, test_creator_user):
    user, ws = test_creator_user
    res = client.get("/api/v1/media-kit/public/testcreator")
    assert res.status_code == 200
    data = res.json()
    assert data["slug"] == "testcreator"
    assert data["display_name"] == "Test Creator"
    assert data["rate_reel"] == 350.0
