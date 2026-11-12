from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import Workspace
from app.schemas.analytics import AnalyticsResponse
from app.services.analytics_service import get_analytics_dashboard
from app.security import get_active_workspace

router = APIRouter(prefix="/analytics", tags=["Creator Analytics"])

@router.get("", response_model=AnalyticsResponse)
def get_creator_analytics(workspace: Workspace = Depends(get_active_workspace), db: Session = Depends(get_db)):
    return get_analytics_dashboard(db, workspace.id)
