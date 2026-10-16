import json
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.automation import Automation, AutomationLog
from app.models.instagram import InstagramAccount
from app.schemas.automation import AutomationCreate, AutomationUpdate, AutomationSimulateRequest, AutomationSimulateResponse

def list_automations(db: Session, workspace_id: str) -> List[Automation]:
    return db.query(Automation).filter(Automation.workspace_id == workspace_id).order_by(Automation.created_at.desc()).all()

def get_automation(db: Session, workspace_id: str, automation_id: str) -> Automation:
    automation = db.query(Automation).filter(
        Automation.id == automation_id,
        Automation.workspace_id == workspace_id
    ).first()
    if not automation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Automation not found")
    return automation

def create_automation(db: Session, workspace_id: str, payload: AutomationCreate) -> Automation:
    account = db.query(InstagramAccount).filter(
        InstagramAccount.workspace_id == workspace_id,
        InstagramAccount.is_connected == True
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must have an active or sandbox Instagram account connected to create automations"
        )

    keywords_json = json.dumps([kw.strip().lower() for kw in payload.trigger_keywords if kw.strip()])
    
    automation = Automation(
        workspace_id=workspace_id,
        ig_account_id=account.id,
        name=payload.name,
        trigger_type=payload.trigger_type,
        target_post_type=payload.target_post_type,
        target_post_id=payload.target_post_id,
        target_post_preview_url=payload.target_post_preview_url,
        match_type=payload.match_type,
        trigger_keywords=keywords_json,
        dm_message_template=payload.dm_message_template,
        reply_comment_template=payload.reply_comment_template,
        is_active=payload.is_active,
        cooldown_minutes=payload.cooldown_minutes,
        total_triggered_count=0
    )
    db.add(automation)
    db.commit()
    db.refresh(automation)
    return automation

def update_automation(db: Session, workspace_id: str, automation_id: str, payload: AutomationUpdate) -> Automation:
    automation = get_automation(db, workspace_id, automation_id)
    
    if payload.name is not None:
        automation.name = payload.name
    if payload.trigger_type is not None:
        automation.trigger_type = payload.trigger_type
    if payload.target_post_type is not None:
        automation.target_post_type = payload.target_post_type
    if payload.target_post_id is not None:
        automation.target_post_id = payload.target_post_id
    if payload.target_post_preview_url is not None:
        automation.target_post_preview_url = payload.target_post_preview_url
    if payload.match_type is not None:
        automation.match_type = payload.match_type
    if payload.trigger_keywords is not None:
        automation.trigger_keywords = json.dumps([kw.strip().lower() for kw in payload.trigger_keywords if kw.strip()])
    if payload.dm_message_template is not None:
        automation.dm_message_template = payload.dm_message_template
    if payload.reply_comment_template is not None:
        automation.reply_comment_template = payload.reply_comment_template
    if payload.is_active is not None:
        automation.is_active = payload.is_active
    if payload.cooldown_minutes is not None:
        automation.cooldown_minutes = payload.cooldown_minutes

    db.commit()
    db.refresh(automation)
    return automation

def delete_automation(db: Session, workspace_id: str, automation_id: str):
    automation = get_automation(db, workspace_id, automation_id)
    db.delete(automation)
    db.commit()

def match_comment(automation: Automation, post_id: Optional[str], comment_text: str) -> tuple[bool, Optional[str]]:
    # Check post target
    if automation.target_post_type == "SPECIFIC_POST" and automation.target_post_id:
        if post_id and automation.target_post_id != post_id:
            return False, None

    comment_lower = comment_text.lower().strip()
    try:
        keywords = json.loads(automation.trigger_keywords)
    except Exception:
        keywords = []

    if automation.match_type == "ANY_COMMENT":
        return True, "ANY_COMMENT"

    if automation.match_type == "EXACT_MATCH":
        for kw in keywords:
            if comment_lower == kw:
                return True, kw
        return False, None

    if automation.match_type == "CONTAINS_ALL":
        for kw in keywords:
            if kw not in comment_lower:
                return False, None
        return True, "ALL_MATCHED"

    # Default: CONTAINS_ANY
    for kw in keywords:
        if kw in comment_lower:
            return True, kw

    return False, None

def render_template(template: str, username: str) -> str:
    rendered = template.replace("{{username}}", f"@{username}")
    rendered = rendered.replace("{{user}}", f"@{username}")
    return rendered

def simulate_trigger(db: Session, workspace_id: str, payload: AutomationSimulateRequest) -> AutomationSimulateResponse:
    query = db.query(Automation).filter(
        Automation.workspace_id == workspace_id,
        Automation.is_active == True
    )
    if payload.automation_id:
        query = query.filter(Automation.id == payload.automation_id)
    
    automations = query.all()
    
    if not automations:
        return AutomationSimulateResponse(
            matched=False,
            recipient=payload.comment_author,
            status="NO_ACTIVE_RULES",
            explanation="No active comment automations found for this workspace."
        )

    for auto in automations:
        matched, kw = match_comment(auto, payload.post_id, payload.comment_text)
        if matched:
            # Anti-spam cooldown check per recipient
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=auto.cooldown_minutes)
            recent_trigger = db.query(AutomationLog).filter(
                AutomationLog.automation_id == auto.id,
                AutomationLog.recipient_username == payload.comment_author,
                AutomationLog.created_at >= cutoff,
                AutomationLog.status.in_(["SIMULATED", "SUCCESS"])
            ).first()

            if recent_trigger:
                return AutomationSimulateResponse(
                    matched=True,
                    automation_id=auto.id,
                    automation_name=auto.name,
                    matched_keyword=kw,
                    dm_message_preview="",
                    reply_comment_preview="",
                    recipient=f"@{payload.comment_author}",
                    status="SUPPRESSED_COOLDOWN",
                    explanation=f"DM suppressed by anti-spam cooldown policy ({auto.cooldown_minutes}m rule between DMs to the same user)."
                )

            dm_preview = render_template(auto.dm_message_template, payload.comment_author)
            reply_preview = render_template(auto.reply_comment_template or "Check your DMs! 💌", payload.comment_author)
            
            # Log the simulated execution
            log_entry = AutomationLog(
                automation_id=auto.id,
                recipient_ig_id=f"sim_{payload.comment_author}",
                recipient_username=payload.comment_author,
                trigger_comment_id="sim_comment_test",
                trigger_comment_text=payload.comment_text,
                dm_text_sent=dm_preview,
                status="SIMULATED"
            )
            db.add(log_entry)
            auto.total_triggered_count += 1
            db.commit()

            return AutomationSimulateResponse(
                matched=True,
                automation_id=auto.id,
                automation_name=auto.name,
                matched_keyword=kw,
                dm_message_preview=dm_preview,
                reply_comment_preview=reply_preview,
                recipient=f"@{payload.comment_author}",
                status="SIMULATION_SUCCESS",
                explanation=f"Matched automation '{auto.name}' with trigger rule '{kw}'. DM dispatched successfully in sandbox."
            )

    return AutomationSimulateResponse(
        matched=False,
        recipient=payload.comment_author,
        status="NO_MATCH",
        explanation=f"Comment '{payload.comment_text}' did not match any active trigger keywords."
    )

def list_automation_logs(db: Session, workspace_id: str, limit: int = 50) -> List[AutomationLog]:
    return db.query(AutomationLog).join(Automation).filter(
        Automation.workspace_id == workspace_id
    ).order_by(AutomationLog.created_at.desc()).limit(limit).all()
