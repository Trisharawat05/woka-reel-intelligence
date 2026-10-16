import json
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceCreate, RateCalculatorRequest, RateCalculatorResponse

MULTIPLIERS = {
    "REEL": 1.0,
    "STORY_SET": 0.45,
    "POST": 0.70,
    "BUNDLE": 1.65
}

def calculate_creator_rate(payload: RateCalculatorRequest) -> RateCalculatorResponse:
    type_mult = MULTIPLIERS.get(payload.deliverable_type.upper(), 1.0)
    
    # CPM calculation: Standard influencer CPM is $25-$40 per 1,000 reach
    cpm_base = 30.0
    er_factor = max(0.8, min(payload.engagement_rate / 3.0, 2.2))
    effective_cpm = cpm_base * er_factor

    # Estimated value based on reach
    reach_thousands = payload.avg_reach / 1000.0
    base_estimate = reach_thousands * effective_cpm * type_mult

    # Ensure reasonable minimums based on follower tier
    floor_rate = max(50.0, (payload.followers / 1000.0) * 8.0 * type_mult)
    recommended = round(max(base_estimate, floor_rate), 2)
    min_rate = round(recommended * 0.82, 2)
    max_rate = round(recommended * 1.35, 2)

    reasoning = (
        f"Based on {payload.followers:,} followers with {payload.avg_reach:,} average reach "
        f"and {payload.engagement_rate:.2f}% engagement rate ({er_factor:.1f}x audience multiplier). "
        f"Benchmark CPM is estimated at ${effective_cpm:.2f} for a {payload.deliverable_type}."
    )

    return RateCalculatorResponse(
        recommended_rate=recommended,
        min_rate=min_rate,
        max_rate=max_rate,
        cpm_estimate=round(effective_cpm, 2),
        reasoning=reasoning
    )

def create_invoice(db: Session, workspace_id: str, payload: InvoiceCreate) -> Invoice:
    total_amount = sum(item.total for item in payload.line_items)
    items_json = json.dumps([item.model_dump() for item in payload.line_items])
    
    count = db.query(Invoice).filter(Invoice.workspace_id == workspace_id).count()
    invoice_number = f"INV-{datetime.now().year}-{count + 1:03d}"

    invoice = Invoice(
        workspace_id=workspace_id,
        invoice_number=invoice_number,
        client_name=payload.client_name,
        client_email=payload.client_email,
        total_amount=total_amount,
        currency=payload.currency,
        status="DRAFT",
        due_date=payload.due_date,
        line_items_json=items_json,
        notes=payload.notes
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice

def list_invoices(db: Session, workspace_id: str) -> List[Invoice]:
    return db.query(Invoice).filter(Invoice.workspace_id == workspace_id).order_by(Invoice.created_at.desc()).all()

def get_invoice(db: Session, workspace_id: str, invoice_id: str) -> Invoice:
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.workspace_id == workspace_id
    ).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice

def update_invoice_status(db: Session, workspace_id: str, invoice_id: str, new_status: str) -> Invoice:
    invoice = get_invoice(db, workspace_id, invoice_id)

    if invoice.status in ["PAID", "CANCELLED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot change status of an invoice that is already {invoice.status}"
        )

    invoice.status = new_status
    db.commit()
    db.refresh(invoice)
    return invoice

