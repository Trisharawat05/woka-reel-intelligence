from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User, Workspace, WorkspaceMember
from app.models.subscription import Subscription
from app.models.profile import CreatorProfile
from app.schemas.auth import UserRegister
from app.security import get_password_hash, verify_password

def get_or_create_workspace(db: Session, user: User) -> Workspace:
    membership = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user.id).first()
    if membership:
        workspace = db.query(Workspace).filter(Workspace.id == membership.workspace_id).first()
        if workspace:
            return workspace
            
    # Create default workspace
    workspace_name = f"{user.full_name}'s Workspace"
    workspace = Workspace(name=workspace_name, owner_id=user.id)
    db.add(workspace)
    db.flush()

    member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role_in_workspace="OWNER")
    db.add(member)

    # Initialize free subscription
    sub = Subscription(workspace_id=workspace.id, plan_tier="FREE", status="ACTIVE")
    db.add(sub)

    # Initialize default creator profile
    slug = user.email.split("@")[0].lower().replace(".", "_")
    profile = CreatorProfile(
        workspace_id=workspace.id,
        slug=slug,
        display_name=user.full_name,
        bio="Digital creator & storyteller. Collaborating on high-impact brand campaigns.",
        niches='["Lifestyle", "Creator Economy", "Tech"]',
        is_verified=False,
        is_public=True
    )
    db.add(profile)
    db.commit()
    db.refresh(workspace)
    return workspace

def register_user(db: Session, payload: UserRegister) -> tuple[User, Workspace]:
    existing_user = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists"
        )
    
    hashed_pwd = get_password_hash(payload.password)
    user = User(
        email=payload.email.lower(),
        hashed_password=hashed_pwd,
        full_name=payload.full_name,
        role=payload.role.upper()
    )
    db.add(user)
    db.flush()

    workspace = get_or_create_workspace(db, user)
    db.commit()
    db.refresh(user)
    return user, workspace

def authenticate_user(db: Session, email: str, password: str) -> tuple[User, Workspace]:
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended or deactivated"
        )
    workspace = get_or_create_workspace(db, user)
    return user, workspace
