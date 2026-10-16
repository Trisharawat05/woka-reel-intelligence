from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import NotificationResponse
from app.security import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("", response_model=List[NotificationResponse])
def get_user_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notifs = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc()).limit(30).all()
    
    if not notifs:
        # Seed welcome notification
        welcome = Notification(
            user_id=current_user.id,
            title="Welcome to Woka! 🚀",
            message="Your creator workspace is live. Connect Instagram or toggle the Sandbox to explore automations.",
            category="SYSTEM",
            link="/dashboard/instagram"
        )
        db.add(welcome)
        db.commit()
        db.refresh(welcome)
        notifs = [welcome]

    return [NotificationResponse.model_validate(n) for n in notifs]

@router.put("/{notification_id}/read")
def mark_as_read(notification_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notif.is_read = True
    db.commit()
    return {"status": "SUCCESS"}

@router.put("/read-all")
def mark_all_read(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).update({"is_read": True})
    db.commit()
    return {"status": "SUCCESS"}
