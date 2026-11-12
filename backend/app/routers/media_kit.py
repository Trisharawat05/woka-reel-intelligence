from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import Workspace
from app.schemas.profile import ProfileResponse, ProfileUpdate, PublicInquiryRequest
from app.services.profile_service import (
    get_profile_by_slug,
    get_workspace_profile,
    update_workspace_profile,
    submit_public_inquiry
)
from app.security import get_active_workspace

router = APIRouter(prefix="/media-kit", tags=["Creator Media Kit & Profile"])

@router.get("/my-profile", response_model=ProfileResponse)
def get_my_profile(workspace: Workspace = Depends(get_active_workspace), db: Session = Depends(get_db)):
    return get_workspace_profile(db, workspace.id)

@router.put("/my-profile", response_model=ProfileResponse)
def edit_my_profile(payload: ProfileUpdate, workspace: Workspace = Depends(get_active_workspace), db: Session = Depends(get_db)):
    return update_workspace_profile(db, workspace.id, payload)

@router.get("/public/{slug}", response_model=ProfileResponse)
def get_public_media_kit(slug: str, db: Session = Depends(get_db)):
    return get_profile_by_slug(db, slug)

@router.post("/public/{slug}/inquire")
def send_inquiry(slug: str, payload: PublicInquiryRequest, db: Session = Depends(get_db)):
    return submit_public_inquiry(db, slug, payload)
