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

def test_get_me_unauthenticated_returns_401(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401

    invalid_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.jwt.token"}
    )
    assert invalid_response.status_code == 401


def test_get_me(client, auth_headers, test_creator_user):
    user, _ = test_creator_user
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user.id
    assert data["email"] == "test_creator@woka.io"
    assert data["full_name"] == user.full_name
    assert data["role"] == user.role
    assert data["is_active"] is True
    assert "created_at" in data
    assert "access_token" not in data
    assert "refresh_token" not in data
    assert "token_type" not in data
    assert "workspace" not in data
    assert "user" not in data
    assert "hashed_password" not in data


def test_get_me_does_not_create_new_jwts(client, auth_headers, monkeypatch):
    import app.routers.auth as auth_router

    token_calls = {"access": 0, "refresh": 0}

    def fail_on_access_token(*args, **kwargs):
        token_calls["access"] += 1
        raise AssertionError("/auth/me must not create new access tokens")

    def fail_on_refresh_token(*args, **kwargs):
        token_calls["refresh"] += 1
        raise AssertionError("/auth/me must not create new refresh tokens")

    monkeypatch.setattr(auth_router, "create_access_token", fail_on_access_token)
    monkeypatch.setattr(auth_router, "create_refresh_token", fail_on_refresh_token)

    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert token_calls == {"access": 0, "refresh": 0}
    data = response.json()
    assert data["email"] == "test_creator@woka.io"
    assert "access_token" not in data
    assert "refresh_token" not in data


def test_login_and_refresh_remain_intact(client, test_creator_user):
    login_res = client.post("/api/v1/auth/login", json={
        "email": "test_creator@woka.io",
        "password": "TestPass123!"
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert "refresh_token" in login_data
    assert login_data["user"]["email"] == "test_creator@woka.io"
    assert login_data["workspace"]["owner_id"] == login_data["user"]["id"]

    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login_data['access_token']}"}
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "test_creator@woka.io"
    assert "access_token" not in me_data
    assert "refresh_token" not in me_data

    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_data["refresh_token"]}
    )
    assert refresh_res.status_code == 200
    refresh_data = refresh_res.json()
    assert refresh_data["access_token"]
    assert refresh_data["refresh_token"]
    assert refresh_data["refresh_token"] != login_data["refresh_token"]

    refreshed_me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_data['access_token']}"}
    )
    assert refreshed_me_res.status_code == 200
    assert refreshed_me_res.json()["email"] == "test_creator@woka.io"
    assert "access_token" not in refreshed_me_res.json()
    assert "refresh_token" not in refreshed_me_res.json()


def test_oauth2_token_endpoint_swagger_form_success(client, test_creator_user):
    from app.security import decode_token

    user, workspace = test_creator_user

    # Simulate exact Swagger Authorize application/x-www-form-urlencoded payload
    res = client.post(
        "/api/v1/auth/token",
        data={
            "grant_type": "password",
            "username": "  Test_Creator@Woka.io ",
            "password": "TestPass123!",
            "scope": "",
            "client_id": "string",
            "client_secret": "string",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]

    claims = decode_token(data["access_token"])
    assert claims["sub"] == user.id
    assert claims["role"] == user.role
    assert claims["workspace_id"] == workspace.id
    assert claims["type"] == "access"

    headers = {"Authorization": f"Bearer {data['access_token']}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "test_creator@woka.io"

    ws_res = client.get("/api/v1/auth/workspaces", headers=headers)
    assert ws_res.status_code == 200
    assert len(ws_res.json()) == 1
    assert ws_res.json()[0]["id"] == workspace.id
    assert ws_res.json()[0]["is_active"] is True

    forbidden_ws = client.get(
        "/api/v1/auth/workspaces",
        headers={**headers, "X-Workspace-Id": "unauthorized-workspace-id"},
    )
    assert forbidden_ws.status_code == 403

    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": data["refresh_token"]},
    )
    assert refresh_res.status_code == 200
    assert refresh_res.json()["access_token"]
    assert refresh_res.json()["token_type"] == "bearer"


def test_oauth2_token_endpoint_incorrect_credentials_and_validation(client, db_session, test_creator_user):
    user, _ = test_creator_user

    wrong_password_res = client.post(
        "/api/v1/auth/token",
        data={"username": "test_creator@woka.io", "password": "WrongPassword123"},
    )
    assert wrong_password_res.status_code == 401
    assert wrong_password_res.headers.get("www-authenticate") == "Bearer"

    unknown_user_res = client.post(
        "/api/v1/auth/token",
        data={"username": "missing@woka.io", "password": "TestPass123!"},
    )
    assert unknown_user_res.status_code == 401
    assert unknown_user_res.headers.get("www-authenticate") == "Bearer"

    json_payload_res = client.post(
        "/api/v1/auth/token",
        json={"email": "test_creator@woka.io", "password": "TestPass123!"},
    )
    assert json_payload_res.status_code == 422

    missing_fields_res = client.post(
        "/api/v1/auth/token",
        data={"username": "test_creator@woka.io"},
    )
    assert missing_fields_res.status_code == 422

    user.is_active = False
    db_session.commit()
    inactive_res = client.post(
        "/api/v1/auth/token",
        data={"username": "test_creator@woka.io", "password": "TestPass123!"},
    )
    assert inactive_res.status_code == 403


def test_openapi_oauth2_scheme_uses_token_endpoint(client):
    from app.security import oauth2_scheme

    assert oauth2_scheme.model.flows.password.tokenUrl == "/api/v1/auth/token"

    schema_res = client.get("/api/v1/openapi.json")
    assert schema_res.status_code == 200
    openapi = schema_res.json()

    sec_schemes = openapi["components"]["securitySchemes"]
    assert sec_schemes["OAuth2PasswordBearer"]["flows"]["password"]["tokenUrl"] == "/api/v1/auth/token"

    token_op = openapi["paths"]["/api/v1/auth/token"]["post"]
    assert "application/x-www-form-urlencoded" in token_op["requestBody"]["content"]

    login_op = openapi["paths"]["/api/v1/auth/login"]["post"]
    assert "application/json" in login_op["requestBody"]["content"]
