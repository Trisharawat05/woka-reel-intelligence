import uuid
from datetime import datetime, date, timezone
from sqlalchemy import Column, String, DateTime, Date, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    invoice_number = Column(String(50), nullable=False, index=True)
    client_name = Column(String(150), nullable=False)
    client_email = Column(String(255), nullable=False)
    total_amount = Column(Float, nullable=False, default=0.0)
    currency = Column(String(10), nullable=False, default="USD")
    status = Column(String(30), nullable=False, default="DRAFT")  # DRAFT, SENT, PAID, OVERDUE, CANCELLED
    due_date = Column(Date, nullable=False)
    line_items_json = Column(Text, nullable=False, default="[]")  # JSON encoded list of line items
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="invoices")
