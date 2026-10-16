import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.automation import (
    AutomationCreate, AutomationUpdate, AutomationResponse,
    AutomationSimulateRequest, AutomationSimulateResponse,
    AutomationLogResponse
)
from app.services.auth_service import get_or_create_workspace
from app.services.automation_engine import (
    list_automations, get_automation, create_automation,
    update_automation, delete_automation, simulate_trigger,
    list_automation_logs
)
from app.security import get_current_user

router = APIRouter(prefix="/automations", tags=["Instagram Automation"])

def to_automation_response(auto) -> AutomationResponse:
    try:
        kw_list = json.loads(auto.trigger_keywords)
    except Exception:
        kw_list = []
    
    return AutomationResponse(
        id=auto.id,
        workspace_id=auto.workspace_id,
        ig_account_id=auto.ig_account_id,
        name=auto.name,
        trigger_type=auto.trigger_type,
        target_post_type=auto.target_post_type,
        target_post_id=auto.target_post_id,
        target_post_preview_url=auto.target_post_preview_url,
        match_type=auto.match_type,
        trigger_keywords=kw_list,
        dm_message_template=auto.dm_message_template,
        reply_comment_template=auto.reply_comment_template,
        is_active=auto.is_active,
        cooldown_minutes=auto.cooldown_minutes,
        total_triggered_count=auto.total_triggered_count,
        created_at=auto.created_at
    )

@router.get("", response_model=List[AutomationResponse])
def get_all_automations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    autos = list_automations(db, workspace.id)
    return [to_automation_response(a) for a in autos]

@router.post("", response_model=AutomationResponse, status_code=status.HTTP_201_CREATED)
def create_new_automation(payload: AutomationCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    auto = create_automation(db, workspace.id, payload)
    return to_automation_response(auto)

@router.get("/logs", response_model=List[AutomationLogResponse])
def get_logs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    logs = list_automation_logs(db, workspace.id)
    return [
        AutomationLogResponse(
            id=l.id,
            automation_id=l.automation_id,
            automation_name=l.automation.name if l.automation else "Automation",
            recipient_ig_id=l.recipient_ig_id,
            recipient_username=l.recipient_username,
            trigger_comment_id=l.trigger_comment_id,
            trigger_comment_text=l.trigger_comment_text,
            dm_text_sent=l.dm_text_sent,
            status=l.status,
            error_message=l.error_message,
            created_at=l.created_at
        )
        for l in logs
    ]

@router.post("/simulate", response_model=AutomationSimulateResponse)
def simulate_comment_flow(payload: AutomationSimulateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    return simulate_trigger(db, workspace.id, payload)

@router.get("/{automation_id}", response_model=AutomationResponse)
def get_single_automation(automation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    auto = get_automation(db, workspace.id, automation_id)
    return to_automation_response(auto)

@router.put("/{automation_id}", response_model=AutomationResponse)
def edit_automation(automation_id: str, payload: AutomationUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    auto = update_automation(db, workspace.id, automation_id, payload)
    return to_automation_response(auto)

@router.delete("/{automation_id}")
def remove_automation(automation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    delete_automation(db, workspace.id, automation_id)
    return {"status": "DELETED"}
