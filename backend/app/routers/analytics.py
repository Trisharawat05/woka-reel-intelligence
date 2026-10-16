from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.analytics import AnalyticsResponse
from app.services.auth_service import get_or_create_workspace
from app.services.analytics_service import get_analytics_dashboard
from app.security import get_current_user

router = APIRouter(prefix="/analytics", tags=["Creator Analytics"])

@router.get("", response_model=AnalyticsResponse)
def get_creator_analytics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    return get_analytics_dashboard(db, workspace.id)
