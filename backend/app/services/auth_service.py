from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User, Workspace, WorkspaceMember
from app.models.subscription import Subscription
from app.models.profile import CreatorProfile
from app.schemas.auth import UserRegister
from app.security import get_password_hash, verify_password

VALID_WORKSPACE_ROLES = ("OWNER", "ADMIN", "MEMBER")
WORKSPACE_ROLE_PRIORITY = {"OWNER": 0, "ADMIN": 1, "MEMBER": 2}


def _membership_sort_key(item: Tuple[WorkspaceMember, Workspace], user_id: str) -> tuple:
    member, ws = item
    created_at = member.created_at
    if created_at is not None and created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    created_ts = created_at.timestamp() if created_at is not None else float("inf")
    return (
        0 if ws.owner_id == user_id else 1,
        WORKSPACE_ROLE_PRIORITY.get(member.role_in_workspace, 99),
        created_ts,
        member.id,
    )


def list_user_workspace_memberships(
    db: Session,
    user: User
) -> List[Tuple[WorkspaceMember, Workspace]]:
    """Returns all valid workspace memberships for the user in deterministic priority order."""
    rows = (
        db.query(WorkspaceMember, Workspace)
        .join(Workspace, Workspace.id == WorkspaceMember.workspace_id)
        .filter(
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.role_in_workspace.in_(VALID_WORKSPACE_ROLES)
        )
        .all()
    )
    rows.sort(key=lambda item: _membership_sort_key(item, user.id))
    return rows


def _get_membership_for_workspace(
    db: Session,
    user_id: str,
    workspace_id: str,
) -> Optional[Tuple[WorkspaceMember, Workspace]]:
    return (
        db.query(WorkspaceMember, Workspace)
        .join(Workspace, Workspace.id == WorkspaceMember.workspace_id)
        .filter(
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.role_in_workspace.in_(VALID_WORKSPACE_ROLES)
        )
        .first()
    )


def resolve_active_workspace(
    db: Session,
    user: User,
    requested_workspace_id: Optional[str] = None,
    token_workspace_id: Optional[str] = None,
) -> Tuple[Workspace, WorkspaceMember]:
    """
    Resolves and verifies the active workspace for an authenticated user.
    - Explicit requested_workspace_id (e.g. X-Workspace-Id) MUST have an active valid membership.
    - Else token_workspace_id claim MUST still have an active valid membership.
    - Else picks the highest-priority workspace deterministically.
    - Never trusts unverified client workspace IDs and never silently creates workspaces.
    """
    if requested_workspace_id is not None:
        target_id = requested_workspace_id.strip()
        if not target_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access the requested workspace"
            )
        row = _get_membership_for_workspace(db, user.id, target_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access the requested workspace"
            )
        member, workspace = row
        return workspace, member

    if token_workspace_id:
        row = _get_membership_for_workspace(db, user.id, token_workspace_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Workspace membership is missing or has been revoked"
            )
        member, workspace = row
        return workspace, member

    memberships = list_user_workspace_memberships(db, user)
    if not memberships:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active workspace membership found for user"
        )
    member, workspace = memberships[0]
    return workspace, member


def get_or_create_workspace(db: Session, user: User) -> Workspace:
    """
    Deterministic default workspace lookup/provisioning for auth bootstrap (register/login/refresh).
    If memberships already exist, returns the highest-priority owned/earliest workspace deterministically.
    """
    memberships = list_user_workspace_memberships(db, user)
    if memberships:
        return memberships[0][1]
            
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
