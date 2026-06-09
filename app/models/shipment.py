from sqlalchemy import Column, Integer, ForeignKey, Enum, DateTime, Numeric, Text, Date
from sqlalchemy.sql import func
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
import enum 
from app.database import Base
from app.models.route import wilaya_enum

class shipment_status_enum(str, enum.Enum) : 
    matched = "matched"
    delivered = "delivered"
    in_transit = "in_transit"
    posted = "posted"
    cancelled = "cancelled"

class Shipment(Base) :
    __tablename__ = "shipment"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    route_id = Column(Integer, ForeignKey("route.id"), nullable=True)
    size = Column(Numeric, nullable=False)
    status = Column(Enum(shipment_status_enum), nullable=False, default=shipment_status_enum.posted)
    notes = Column(Text, nullable=True)
    pickup_location = Column(Enum(wilaya_enum, values_callable=lambda obj : [e.value for e in obj]), nullable=False)
    delivery_location = Column(Enum(wilaya_enum, values_callable=lambda obj : [e.value for e in obj]), nullable=False)
    pickup_date = Column(Date, nullable=False)
    requesting_routes = Column(MutableList.as_mutable(JSONB), default=[])
    volume = Column(Numeric, nullable=True)
    photo = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User", back_populates="shipment")
    route = relationship("Route", back_populates="shipment")
    @property
    def owner(self) :
        return self.user.name if self.user else "unknown"