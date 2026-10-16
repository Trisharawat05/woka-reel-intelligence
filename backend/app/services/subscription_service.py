from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.subscription import Subscription

TIER_LIMITS = {
    "FREE": {"dm": 50, "ai": 10},
    "PRO": {"dm": 2000, "ai": 500},
    "AGENCY": {"dm": 20000, "ai": 5000}
}

def get_workspace_subscription(db: Session, workspace_id: str) -> Subscription:
    sub = db.query(Subscription).filter(Subscription.workspace_id == workspace_id).first()
    if not sub:
        sub = Subscription(
            workspace_id=workspace_id,
            plan_tier="FREE",
            status="ACTIVE",
            dm_limit_monthly=50,
            dm_used_monthly=0,
            ai_limit_monthly=10,
            ai_used_monthly=0
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
    return sub

def upgrade_subscription(db: Session, workspace_id: str, target_tier: str) -> Subscription:
    tier = target_tier.upper()
    if tier not in TIER_LIMITS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid tier {tier}")

    sub = get_workspace_subscription(db, workspace_id)
    sub.plan_tier = tier
    sub.status = "ACTIVE"
    sub.dm_limit_monthly = TIER_LIMITS[tier]["dm"]
    sub.ai_limit_monthly = TIER_LIMITS[tier]["ai"]
    sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
    
    db.commit()
    db.refresh(sub)
    return sub

def check_and_increment_dm_quota(db: Session, workspace_id: str) -> bool:
    sub = get_workspace_subscription(db, workspace_id)
    if sub.dm_used_monthly >= sub.dm_limit_monthly:
        return False
    sub.dm_used_monthly += 1
    db.commit()
    return True

def check_and_increment_ai_quota(db: Session, workspace_id: str) -> bool:
    sub = get_workspace_subscription(db, workspace_id)
    if sub.ai_used_monthly >= sub.ai_limit_monthly:
        return False
    sub.ai_used_monthly += 1
    db.commit()
    return True
