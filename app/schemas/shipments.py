from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime, date
from enum import Enum
from decimal import Decimal
from app.models.route import wilaya_enum

class ShipmentStatus(str, Enum) :
    posted = "posted"
    matched = "matched"
    in_transit = "in_transit"
    cancelled = "cancelled"
    delivered = "delivered"

class ShipmentCreate(BaseModel) :
    pickup_location : wilaya_enum
    delivery_location : wilaya_enum
    pickup_date : date
    size : Decimal # this is the weight, i just named it badly
    notes : Optional[str] = None
    volume : Decimal
    photo : Optional[str] = None

class ShipmentUpdate(BaseModel) :
    pickup_location : Optional[wilaya_enum] = None
    delivery_location : Optional[wilaya_enum] = None
    pickup_date : Optional[date] = None
    size : Optional[Decimal] = None
    notes : Optional[str] = None
    status : Optional[ShipmentStatus] = None 
    volume : Optional[Decimal] = None
    photo : Optional[str] = None

class ShipmentOut(BaseModel) :
    id : int
    user_id : int
    route_id : Optional[int] = None 
    pickup_location : wilaya_enum
    delivery_location : wilaya_enum
    pickup_date : date
    size : Decimal
    notes : Optional[str] = None
    status : ShipmentStatus
    owner : Optional[str] = None
    volume : Optional[Decimal] = None
    photo : Optional[str] = None
    created_at : datetime
    model_config = ConfigDict(from_attributes=True)