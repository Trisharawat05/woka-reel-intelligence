def test_create_and_list_automation(client, auth_headers):
    create_payload = {
        "name": "E-Book Lead Magnet",
        "trigger_type": "COMMENT",
        "target_post_type": "ALL_POSTS",
        "match_type": "CONTAINS_ANY",
        "trigger_keywords": ["ebook", "guide", "free"],
        "dm_message_template": "Hi {{username}}, here is your free guide: https://woka.io/guide",
        "reply_comment_template": "Sent you a DM {{username}}!",
        "cooldown_minutes": 60,
        "is_active": True
    }
    res = client.post("/api/v1/automations", json=create_payload, headers=auth_headers)
    assert res.status_code == 201
    created = res.json()
    assert created["name"] == "E-Book Lead Magnet"
    assert "ebook" in created["trigger_keywords"]

    # List automations
    list_res = client.get("/api/v1/automations", headers=auth_headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

def test_simulate_automation_match(client, auth_headers):
    # Create automation first
    client.post("/api/v1/automations", json={
        "name": "Discount Code DM",
        "trigger_type": "COMMENT",
        "target_post_type": "ALL_POSTS",
        "match_type": "CONTAINS_ANY",
        "trigger_keywords": ["discount", "code"],
        "dm_message_template": "Hey {{username}}! Use code WOKA20 for 20% off.",
        "reply_comment_template": "Check your messages!",
        "is_active": True
    }, headers=auth_headers)

    # Simulate matching comment
    sim_res = client.post("/api/v1/automations/simulate", json={
        "comment_text": "Can I please get the discount code?",
        "comment_author": "fan_alex"
    }, headers=auth_headers)

    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["matched"] is True
    assert "@fan_alex" in sim_data["dm_message_preview"]
    assert "WOKA20" in sim_data["dm_message_preview"]
    assert sim_data["status"] == "SIMULATION_SUCCESS"

    # Check logs
    logs_res = client.get("/api/v1/automations/logs", headers=auth_headers)
    assert logs_res.status_code == 200
    assert len(logs_res.json()) >= 1

def test_simulate_automation_no_match(client, auth_headers):
    # Create automation first
    client.post("/api/v1/automations", json={
        "name": "E-Book Guide",
        "trigger_type": "COMMENT",
        "target_post_type": "ALL_POSTS",
        "match_type": "CONTAINS_ANY",
        "trigger_keywords": ["guide", "free"],
        "dm_message_template": "Hey {{username}}! Here is the guide.",
        "is_active": True
    }, headers=auth_headers)

    sim_res = client.post("/api/v1/automations/simulate", json={
        "comment_text": "Great photo today!",
        "comment_author": "friendly_follower"
    }, headers=auth_headers)

    assert sim_res.status_code == 200
    assert sim_res.json()["matched"] is False
    assert sim_res.json()["status"] == "NO_MATCH"
