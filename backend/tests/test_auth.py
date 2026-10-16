def test_register_success(client):
    response = client.post("/api/v1/auth/register", json={
        "email": "newuser@woka.io",
        "password": "Password123!",
        "full_name": "New User",
        "role": "CREATOR"
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "newuser@woka.io"
    assert data["workspace"]["name"] == "New User's Workspace"

def test_register_duplicate_email(client, test_creator_user):
    user, _ = test_creator_user
    response = client.post("/api/v1/auth/register", json={
        "email": user.email,
        "password": "Password123!",
        "full_name": "Duplicate User",
        "role": "CREATOR"
    })
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_login_success(client, test_creator_user):
    response = client.post("/api/v1/auth/login", json={
        "email": "test_creator@woka.io",
        "password": "TestPass123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "test_creator@woka.io"

def test_login_invalid_password(client, test_creator_user):
    response = client.post("/api/v1/auth/login", json={
        "email": "test_creator@woka.io",
        "password": "WrongPassword123"
    })
    assert response.status_code == 401

def test_get_me(client, auth_headers):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "test_creator@woka.io"
