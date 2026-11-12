from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import Workspace
from app.schemas.subscription import SubscriptionResponse, UpgradePlanRequest
from app.services.subscription_service import get_workspace_subscription, upgrade_subscription
from app.security import get_active_workspace, require_workspace_admin

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions & Usage"])

@router.get("/current", response_model=SubscriptionResponse)
def get_current_plan(workspace: Workspace = Depends(get_active_workspace), db: Session = Depends(get_db)):
    sub = get_workspace_subscription(db, workspace.id)
    return SubscriptionResponse.model_validate(sub)

@router.post("/upgrade", response_model=SubscriptionResponse)
def upgrade_plan(payload: UpgradePlanRequest, workspace: Workspace = Depends(require_workspace_admin), db: Session = Depends(get_db)):
    sub = upgrade_subscription(db, workspace.id, payload.target_tier)
    return SubscriptionResponse.model_validate(sub)
