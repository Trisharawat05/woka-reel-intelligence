from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class InvoiceLineItem(BaseModel):
    description: str = Field(min_length=1)
    quantity: int = Field(default=1, ge=1)
    unit_price: float = Field(ge=0)
    total: float = Field(ge=0)

class InvoiceCreate(BaseModel):
    client_name: str = Field(min_length=2, max_length=150)
    client_email: str
    currency: str = Field(default="USD")
    due_date: date
    line_items: List[InvoiceLineItem]
    notes: Optional[str] = None

class InvoiceUpdateStatus(BaseModel):
    status: str = Field(description="DRAFT, SENT, PAID, OVERDUE, CANCELLED")

class InvoiceResponse(BaseModel):
    id: str
    workspace_id: str
    invoice_number: str
    client_name: str
    client_email: str
    total_amount: float
    currency: str
    status: str
    due_date: date
    line_items: List[InvoiceLineItem]
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RateCalculatorRequest(BaseModel):
    followers: int = Field(ge=100)
    avg_reach: int = Field(ge=100)
    engagement_rate: float = Field(ge=0.1, le=100)
    deliverable_type: str = Field(default="REEL", description="REEL, STORY_SET, POST, BUNDLE")

class RateCalculatorResponse(BaseModel):
    recommended_rate: float
    min_rate: float
    max_rate: float
    cpm_estimate: float
    reasoning: str
