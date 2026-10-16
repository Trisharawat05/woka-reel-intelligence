import json
from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.invoice import (
    InvoiceCreate, InvoiceResponse, InvoiceLineItem,
    RateCalculatorRequest, RateCalculatorResponse
)
from app.services.auth_service import get_or_create_workspace
from app.services.invoice_service import (
    calculate_creator_rate, create_invoice, list_invoices, get_invoice, update_invoice_status
)
from app.security import get_current_user

router = APIRouter(prefix="/invoices", tags=["Invoices & Rate Calculator"])

def to_invoice_response(inv) -> InvoiceResponse:
    try:
        items = json.loads(inv.line_items_json)
        line_items = [InvoiceLineItem(**it) for it in items]
    except Exception:
        line_items = []

    return InvoiceResponse(
        id=inv.id,
        workspace_id=inv.workspace_id,
        invoice_number=inv.invoice_number,
        client_name=inv.client_name,
        client_email=inv.client_email,
        total_amount=inv.total_amount,
        currency=inv.currency,
        status=inv.status,
        due_date=inv.due_date,
        line_items=line_items,
        notes=inv.notes,
        created_at=inv.created_at
    )

@router.post("/calculate-rate", response_model=RateCalculatorResponse)
def calculate_rate(payload: RateCalculatorRequest):
    return calculate_creator_rate(payload)

@router.get("", response_model=List[InvoiceResponse])
def get_invoices(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    invoices = list_invoices(db, workspace.id)
    return [to_invoice_response(i) for i in invoices]

@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_one_invoice(invoice_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    inv = get_invoice(db, workspace.id, invoice_id)
    return to_invoice_response(inv)

@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_new_invoice(payload: InvoiceCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    inv = create_invoice(db, workspace.id, payload)
    return to_invoice_response(inv)

@router.put("/{invoice_id}/status", response_model=InvoiceResponse)
def change_invoice_status(
    invoice_id: str,
    status: str = Query(..., pattern="^(DRAFT|SENT|PAID|OVERDUE|CANCELLED)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace = get_or_create_workspace(db, current_user)
    inv = update_invoice_status(db, workspace.id, invoice_id, status)
    return to_invoice_response(inv)

