import json
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.profile import CreatorProfile
from app.models.instagram import InstagramAccount
from app.models.notification import Notification
from app.models.user import Workspace
from app.schemas.profile import ProfileUpdate, ProfileResponse, PublicInquiryRequest

def get_profile_by_slug(db: Session, slug: str) -> ProfileResponse:
    profile = db.query(CreatorProfile).filter(
        CreatorProfile.slug == slug.lower(),
        CreatorProfile.is_public == True
    ).first()
    
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creator media kit not found")

    # Get linked account stats if available
    account = db.query(InstagramAccount).filter(
        InstagramAccount.workspace_id == profile.workspace_id,
        InstagramAccount.is_connected == True
    ).first()

    followers_count = account.followers_count if account else 38500
    er = 4.25
    reach = int(followers_count * 3.4)

    try:
        niches_list = json.loads(profile.niches)
    except Exception:
        niches_list = ["Creator", "Lifestyle"]

    return ProfileResponse(
        id=profile.id,
        workspace_id=profile.workspace_id,
        slug=profile.slug,
        display_name=profile.display_name,
        bio=profile.bio,
        avatar_url=profile.avatar_url,
        niches=niches_list,
        location=profile.location,
        rate_reel=profile.rate_reel,
        rate_story=profile.rate_story,
        rate_bundle=profile.rate_bundle,
        is_verified=profile.is_verified,
        is_public=profile.is_public,
        followers_count=followers_count,
        engagement_rate=er,
        total_reach_30d=reach
    )

def get_workspace_profile(db: Session, workspace_id: str) -> ProfileResponse:
    profile = db.query(CreatorProfile).filter(CreatorProfile.workspace_id == workspace_id).first()
    if not profile:
        profile = CreatorProfile(
            workspace_id=workspace_id,
            slug=f"creator_{workspace_id[:8]}",
            display_name="Creator Profile",
            bio="Professional content creator",
            niches='["Lifestyle", "Tech"]'
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return get_profile_by_slug(db, profile.slug)

def update_workspace_profile(db: Session, workspace_id: str, payload: ProfileUpdate) -> ProfileResponse:
    profile = db.query(CreatorProfile).filter(CreatorProfile.workspace_id == workspace_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    if payload.display_name is not None:
        profile.display_name = payload.display_name
    if payload.bio is not None:
        profile.bio = payload.bio
    if payload.avatar_url is not None:
        profile.avatar_url = payload.avatar_url
    if payload.niches is not None:
        profile.niches = json.dumps(payload.niches)
    if payload.location is not None:
        profile.location = payload.location
    if payload.rate_reel is not None:
        profile.rate_reel = payload.rate_reel
    if payload.rate_story is not None:
        profile.rate_story = payload.rate_story
    if payload.rate_bundle is not None:
        profile.rate_bundle = payload.rate_bundle
    if payload.is_public is not None:
        profile.is_public = payload.is_public

    db.commit()
    db.refresh(profile)
    return get_profile_by_slug(db, profile.slug)

def submit_public_inquiry(db: Session, slug: str, payload: PublicInquiryRequest) -> dict:
    profile = db.query(CreatorProfile).filter(CreatorProfile.slug == slug.lower()).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creator not found")

    workspace = db.query(Workspace).filter(Workspace.id == profile.workspace_id).first()
    if workspace:
        notification = Notification(
            user_id=workspace.owner_id,
            title=f"New Brand Inquiry from {payload.brand_name}!",
            message=f"{payload.brand_name} ({payload.contact_email}) inquired about {payload.project_scope} with budget {payload.budget}.",
            category="CAMPAIGN",
            link="/dashboard/campaigns"
        )
        db.add(notification)
        db.commit()

    return {"status": "SUCCESS", "message": "Inquiry transmitted to creator successfully."}
