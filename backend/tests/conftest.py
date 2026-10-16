import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.user import User, Workspace, WorkspaceMember
from app.models.subscription import Subscription
from app.models.profile import CreatorProfile
from app.models.instagram import InstagramAccount
from app.security import get_password_hash, create_access_token, encrypt_token

# In-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_creator_user(db_session):
    user = User(
        email="test_creator@woka.io",
        hashed_password=get_password_hash("TestPass123!"),
        full_name="Test Creator",
        role="CREATOR"
    )
    db_session.add(user)
    db_session.flush()

    ws = Workspace(name="Test Creator Workspace", owner_id=user.id)
    db_session.add(ws)
    db_session.flush()

    db_session.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role_in_workspace="OWNER"))
    db_session.add(Subscription(workspace_id=ws.id, plan_tier="FREE", status="ACTIVE"))
    db_session.add(CreatorProfile(
        workspace_id=ws.id,
        slug="testcreator",
        display_name="Test Creator",
        bio="Test Bio",
        niches='["Tech"]'
    ))

    # Add active Instagram sandbox account
    db_session.add(InstagramAccount(
        workspace_id=ws.id,
        ig_user_id="ig_test_user_id",
        username="test_creator_ig",
        name="Test IG",
        encrypted_access_token=encrypt_token("mock_token"),
        is_connected=True,
        is_sandbox=True,
        followers_count=10000,
        media_count=45
    ))

    db_session.commit()
    db_session.refresh(user)
    return user, ws

@pytest.fixture
def auth_headers(test_creator_user):
    user, ws = test_creator_user
    token = create_access_token(data={"sub": user.id, "role": user.role, "workspace_id": ws.id})
    return {"Authorization": f"Bearer {token}"}
