from sqlalchemy import Column, Integer, String, Text, Enum, DateTime, CheckConstraint, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base
from app.models.route import wilaya_enum

class account_type_enum(str, enum.Enum) :
    personal = "personal"
    business = "business"

class User(Base) :
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    password_hash = Column(Text, nullable=False)
    phone_number = Column(String(20), nullable=False)
    account_type = Column(Enum(account_type_enum), nullable=True)
    business_registration_number = Column(String(255), nullable=True)
    business_address = Column(String(255), nullable=True)
    tax_id = Column(String(255), nullable=True)
    otp_code = Column(Integer, nullable=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    otp_expires = Column(DateTime(timezone=True), nullable=True)
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    photo_url = Column(Text, nullable=True)
    city = Column(Enum(wilaya_enum, values_callable=lambda obj : [e.value for e in obj]), nullable=True)
    is_available = Column(Boolean, nullable=False, default=True)
    subscription_plan = Column(String(25), nullable=True)
    subscription_start = Column(DateTime, nullable=True)
    subscription_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = ( 
        CheckConstraint (
            "(account_type = 'business' AND business_registration_number IS NOT NULL) OR "
            "(account_type = 'personal' AND business_registration_number IS NULL)"
        ),
        CheckConstraint (
            "(account_type = 'business' AND business_address IS NOT NULL) OR "
            "(account_type = 'personal' AND business_address IS NULL)"
        ),
        CheckConstraint (
            "(account_type = 'business' AND tax_id IS NOT NULL) OR "
            "(account_type = 'personal' AND tax_id IS NULL)"
        ),
        CheckConstraint (
            "subscription_end IS NULL OR subscription_start IS NULL OR subscription_end > subscription_start",
            name = "check_subscription_dates"
        )
    )
    shipment = relationship("Shipment", back_populates="user")
    route = relationship("Route", back_populates="user")
    vehicle = relationship("Vehicle", back_populates="user")
    notifications = relationship("Notification", back_populates="user")