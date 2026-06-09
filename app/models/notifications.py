import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from datetime import datetime
from app.database import Base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

class NotificationType(enum.Enum) :
    match = "match"
    request = "request"
    accept = "accept"
    reject = "reject"
    cancel = "cancel"
    system = "system"

class Notification(Base) :
    __tablename__ = "notifications"
    id = Column(Integer, primary_key = True, index = True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable = False)
    notification_type = Column(Enum(NotificationType), nullable = False)
    message = Column(String, nullable = False)
    is_read = Column(Boolean, default = False)
    created_at = Column(DateTime, server_default = func.now())
    target_id = Column(Integer, nullable = True) # id of the related route or shipment
    target_type = Column(String, nullable = True) # "route" or "shipment"
    user = relationship("User", back_populates="notifications")