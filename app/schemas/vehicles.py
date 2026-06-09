from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime, date
from enum import Enum
from decimal import Decimal

class VehicleType(str, Enum) :
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

class VehicleCreate(BaseModel) : # post requests
    plate_number : str
    capacity : Decimal
    type : VehicleType

class VehicleOut(BaseModel) : # get responses
    id : int
    user_id : int
    plate_number : str
    capacity : Decimal
    type: VehicleType
    created_at : datetime
    model_config = ConfigDict(from_attributes=True)