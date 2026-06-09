from sqlalchemy import Integer, Column, String, Text, Enum, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base 

class vehicle_type_enum(str, enum.Enum) : 
    box_van = "box van"
    dry_van_trailer = "dry van trailer"
    refrigerated_truck = "refrigerated truck"
    cargo_van = "cargo van"
    box_truck = "box truck"
    flatbed_truck = "flatbed truck"
    curtain_side_truck = "curtain side truck" 
    tail_lifts_truck = "tail lifts truck"
    tanker_truck = "tanker truck"
    mini_van = "mini van"
    pickup_truck = "pickup truck"
    luton_van = "luton van"
    camper_van = "camper van"
    panel_van = "panel van" 

class Vehicle(Base) : 
    __tablename__ = "vehicle"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    plate_number = Column(String(10), nullable=False)
    capacity = Column(Numeric, nullable=False)
    type = Column(Enum(vehicle_type_enum), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User", back_populates="vehicle")
    route = relationship("Route", back_populates="vehicle")