from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Optional
from datetime import datetime, timedelta
from enum import Enum

class AccountType(str, Enum) :
    personal = "personal"
    business = "business"

class UserUpdate(BaseModel):
    name : Optional[str] = Field(None, min_length = 1, max_length = 50)
    phone_number : Optional[str] = Field(None, min_length = 9, max_length = 13)
    photo_url : Optional[str] = None
    city : Optional[str] = None
    is_available : Optional[bool] = None
    model_config = {
        "use_enum_values" : True
    }

class UserOut(BaseModel) :
    id : int
    name : str
    email : EmailStr
    # account_type : AccountType
    phone_number : str
    photo_url : Optional[str] = None
    city : Optional[str] = None
    is_available : bool = True
    created_at : datetime
    model_config = ConfigDict(from_attributes=True)

class SubscriptionStatus(BaseModel) :
    plan : Optional[str]
    expires_at : Optional[datetime]
    days_left : int
    is_active : bool
    @classmethod
    def from_orm_custom(cls, user) :
        days = 0
        is_active = False
        expires_at = user.subscription_end
        
        if user.subscription_end :
            # paid plan — check against subscription_end
            end = user.subscription_end
            if end.tzinfo is not None :
                end = end.replace(tzinfo=None)
            now = datetime.utcnow()
            delta = end - now
            days = max(0, delta.days)
            is_active = delta.total_seconds() > 0
        else :
            # no paid plan — compute remaining free trial days from created_at
            created = user.created_at
            if created is not None :
                if created.tzinfo is not None :
                    created = created.replace(tzinfo=None)
                trial_end = created + timedelta(days=7)
                expires_at = trial_end
                delta = trial_end - datetime.utcnow()
                days = max(0, delta.days)
                is_active = delta.total_seconds() > 0
        return cls(plan=user.subscription_plan, expires_at=expires_at, days_left=days, is_active=is_active)
class SubscribeRequest(BaseModel) :
    plan : str