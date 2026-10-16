from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class SubscriptionResponse(BaseModel):
    plan_tier: str  # FREE, PRO, AGENCY
    status: str
    dm_limit_monthly: int
    dm_used_monthly: int
    ai_limit_monthly: int
    ai_used_monthly: int
    current_period_end: datetime

    model_config = ConfigDict(from_attributes=True)

class UpgradePlanRequest(BaseModel):
    target_tier: str = Field(description="PRO or AGENCY")
