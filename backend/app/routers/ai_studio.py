from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.ai import (
    CaptionGenerateRequest, CaptionGenerateResponse,
    HookGenerateRequest, HookGenerateResponse,
    HashtagGenerateRequest, HashtagGenerateResponse
)
from app.services.auth_service import get_or_create_workspace
from app.services.subscription_service import check_and_increment_ai_quota
from app.services.ai_service import generate_caption, generate_hooks, generate_hashtags
from app.security import get_current_user

router = APIRouter(prefix="/ai-studio", tags=["AI Content Studio"])

@router.post("/caption", response_model=CaptionGenerateResponse)
def create_caption(payload: CaptionGenerateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    if not check_and_increment_ai_quota(db, workspace.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly AI generations limit reached for your current plan. Please upgrade to Pro."
        )
    return generate_caption(payload)

@router.post("/hooks", response_model=HookGenerateResponse)
def create_hooks(payload: HookGenerateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    if not check_and_increment_ai_quota(db, workspace.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly AI generations limit reached for your current plan. Please upgrade to Pro."
        )
    return generate_hooks(payload)

@router.post("/hashtags", response_model=HashtagGenerateResponse)
def create_hashtags(payload: HashtagGenerateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return generate_hashtags(payload)
