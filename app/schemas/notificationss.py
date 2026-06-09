from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class NotificationOut(BaseModel) :
    id : int
    notification_type : str
    message : str
    is_read : bool
    created_at : datetime
    target_id : Optional[int] 
    target_type : Optional[str] 
    model_config = ConfigDict(from_attributes = True)