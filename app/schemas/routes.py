from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime, date
from enum import Enum
from decimal import Decimal
from app.models.route import wilaya_enum
from app.models.vehicle import vehicle_type_enum

class RouteStatus(str, Enum) :
    open = "open"
    full = "full" 
    completed = "completed"
    cancelled = "cancelled"

class RouteType(str, Enum) :
    one_way = "one_way"
    round_trip = "round_trip"

class RouteCreate(BaseModel) :
    vehicle_id : int          
    departure_location : wilaya_enum
    arrival_location : Optional[wilaya_enum] = None
    departure_date : date
    estimated_arrival_date : Optional[date] = None
    total_capacity : Decimal
    type : RouteType 
    notes : Optional[str] = None

class RouteUpdate(BaseModel) :
    departure_location : Optional[wilaya_enum] = None
    arrival_location : Optional[wilaya_enum] = None
    departure_date : Optional[date] = None
    estimated_arrival_date : Optional[date] = None
    total_capacity : Optional[Decimal] = None
    remaining_capacity : Optional[Decimal] = None
    status : Optional[RouteStatus] = None
    type : Optional[RouteType] = None
    notes : Optional[str] = None

class RouteOut(BaseModel) :
    id : int
    user_id : int
    vehicle_id : int
    departure_location : wilaya_enum
    arrival_location : Optional[wilaya_enum] = None
    departure_date : date
    estimated_arrival_date : Optional[date] = None
    total_capacity : Decimal
    remaining_capacity : Decimal
    status : RouteStatus
    type : RouteType
    owner : Optional[str] = None
    notes : Optional[str] = None
    vehicle_type : Optional[vehicle_type_enum] = None
    created_at : datetime
    model_config = ConfigDict(from_attributes=True)

class RouteFilter(BaseModel) :
    departure_location : Optional[wilaya_enum] = None
    arrival_location : Optional[wilaya_enum] = None
    name : Optional[str] = None
    remaining_capacity : Optional[Decimal] = None
    type : Optional[RouteType] = None