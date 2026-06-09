from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.routes.userr import get_current_user
from app.schemas import notificationss
from app.models import notifications
from app.models.user import User

router = APIRouter(
    prefix = "/notifications",
    tags = ["notifications"]
)

@router.get("/notifications", response_model = list[notificationss.NotificationOut])
def get_notifications(db : Session = Depends(get_db), current_user : User = Depends(get_current_user)) :
    return db.query(notifications.Notification).filter(notifications.Notification.user_id == current_user.id).order_by(notifications.Notification.created_at.desc()).all()

# mark the notif as read
@router.patch("/notifications/{notif_id}/read")
def mark_as_read(notif_id : int, db : Session = Depends(get_db), current_user : User = Depends(get_current_user)) :
    notif = db.query(notifications.Notification).filter(notifications.Notification.id == notif_id, notifications.Notification.user_id == current_user.id).first()
    if notif :
        notif.is_read = True
        db.commit()
    return {"status" : "success"}

# mark all notifs as read
@router.patch("/read-all-notifs")
def mark_all_as_read(db : Session = Depends(get_db), current_user : User = Depends(get_current_user)):
    (db.query(notifications.Notification).filter(notifications.Notification.user_id == current_user.id, notifications.Notification.is_read == False).update({"is_read": True}))
    db.commit()
    return {"status": "success"}

@router.delete("/clear-all")
def clear_all_notifications(db : Session = Depends(get_db), current_user : User = Depends(get_current_user)):
    db.query(notifications.Notification).filter(notifications.Notification.user_id == current_user.id).delete()
    db.commit()
    return {"status": "success"}
    