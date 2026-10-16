from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.subscription import SubscriptionResponse, UpgradePlanRequest
from app.services.auth_service import get_or_create_workspace
from app.services.subscription_service import get_workspace_subscription, upgrade_subscription
from app.security import get_current_user

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions & Usage"])

@router.get("/current", response_model=SubscriptionResponse)
def get_current_plan(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    sub = get_workspace_subscription(db, workspace.id)
    return SubscriptionResponse.model_validate(sub)

@router.post("/upgrade", response_model=SubscriptionResponse)
def upgrade_plan(payload: UpgradePlanRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    sub = upgrade_subscription(db, workspace.id, payload.target_tier)
    return SubscriptionResponse.model_validate(sub)
