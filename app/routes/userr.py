from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, APIRouter, UploadFile, File
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app import schemas
from app import models, security  
from jose import JWTError
from pathlib import Path
import shutil
import cloudinary
import cloudinary.uploader
import os

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login") 

router = APIRouter(
    prefix = "/user",
    tags = ["user"]
)

cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET")
)

@router.get("/me")
def get_current_user(token : str = Depends(oauth2_scheme), db : Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail = "could not validate credentials",
        headers = {"www-authenticate" : "bearer"},
    )
    try :
        payload = security.decode_access_token(token) 
        user_id : int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError :
        raise credentials_exception
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

@router.patch("/me")
def update_profile(updated_data : schemas.UserUpdate, db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    for key, value in updated_data.model_dump(exclude_unset = True).items() :
        setattr(current_user, key, value)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.delete("/me", status_code = status.HTTP_204_NO_CONTENT)
def delete_account(db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    user_id = current_user.id
    active_shipment = db.query(models.Shipment).filter(models.Shipment.user_id == user_id, models.Shipment.status == models.shipment.shipment_status_enum.in_transit).first()
    active_route = db.query(models.Route).join(models.Shipment).filter(models.Route.user_id == user_id, models.Shipment.status == models.shipment.shipment_status_enum.in_transit).first()
    if active_shipment or active_route :
        raise HTTPException(status_code = 400, detail = "cannot delete account while deliveries are in transit")
    matched_shipment = db.query(models.Shipment).filter(models.Shipment.user_id == user_id, models.Shipment.status == models.shipment.shipment_status_enum.matched).first()
    matched_route = db.query(models.Route).join(models.Shipment).filter(models.Route.user_id == user_id, models.Shipment.status == models.shipment.shipment_status_enum.matched).first()
    if matched_shipment or matched_route :
        raise HTTPException(400, "cannot delete account while having active matches")
    user_shipment_ids = [s.id for s in db.query(models.Shipment.id).filter(models.Shipment.user_id == user_id)]
    user_route_ids = [r.id for r in db.query(models.Route.id).filter(models.Route.user_id == user_id)]
    for route in db.query(models.Route).all() :
        if route.requesting_shippers :
            route.requesting_shippers = [sid for sid in route.requesting_shippers if sid not in user_shipment_ids]
    for shipment in db.query(models.Shipment).all() :
        if shipment.requesting_routes :
            shipment.requesting_routes = [rid for rid in shipment.requesting_routes if rid not in user_route_ids]
    db.query(models.Shipment).filter(models.Shipment.user_id == user_id).delete(synchronize_session = False)
    db.query(models.Route).filter(models.Route.user_id == user_id).delete(synchronize_session = False)
    db.query(models.Vehicle).filter(models.Vehicle.user_id == user_id).delete()
    db.delete(current_user)
    db.commit()

@router.post("/me/photo")
def upload_profile_photo(file : UploadFile = File(...), db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code = 400, detail = "file must be an image")
    try :
        result = cloudinary.uploader.upload(file.file, folder = "profile_photos", width = 300, height = 300, crop = "fill")
        image_url = result.get("secure_url")
        current_user.photo_url = image_url
        db.commit()
        db.refresh(current_user)
        return {"profile_photo" : image_url}
    except Exception as e :
        raise HTTPException(status_code = 500, detail = str(e))
    
@router.get("/subscription", response_model = schemas.SubscriptionStatus)
def get_subscription_status(current_user : models.User = Depends(get_current_user)) :
    return schemas.SubscriptionStatus.from_orm_custom(current_user)

@router.post("/subscription")
def subscribe(data : schemas.SubscribeRequest, db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    now = datetime.utcnow()
    if data.plan == "monthly" :
        end_date = now + timedelta(days = 30)
    elif data.plan == "yearly" :
        end_date = now + timedelta(days = 365)
    else :
        raise HTTPException(status_code = 400, detail = "invalid plan")
    current_user.subscription_plan = data.plan
    current_user.subscription_start = now
    current_user.subscription_end = end_date
    db.commit()
    db.refresh(current_user)
    return {"message" : "subscription activated"}

@router.delete("/subscription")
def cancel_subscription(db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    if not current_user.subscription_plan :
        raise HTTPException(status_code = 400, detail = "no active subscription")
    current_user.subscription_plan = None
    current_user.subscription_start = None
    current_user.subscription_end = None
    db.commit()
    return {"message" : "subscription cancelled"}

@router.put("/subscription")
def change_subscription_plan(data : schemas.SubscribeRequest, db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    if not current_user.subscription_plan :
        raise HTTPException(status_code = 400, detail = "no active subscription to change")
    now = datetime.utcnow()
    VALID_PLANS = {
        "monthly" : 30,
        "yearly" : 365
    }
    if data.plan not in VALID_PLANS :
        raise HTTPException(status_code = 400, detail = "invalid plan")
    current_user.subscription_plan = data.plan
    current_user.subscription_start = now
    current_user.subscription_end = now + timedelta(days = VALID_PLANS[data.plan])
    db.commit()
    db.refresh(current_user)
    return {"message" : "subscription updated"}

from datetime import datetime, timedelta

def require_active_subscription(current_user : models.User = Depends(get_current_user)) :
    now = datetime.utcnow()
    if current_user.subscription_plan and current_user.subscription_end :
        end = current_user.subscription_end
        if end.tzinfo is not None :
            end = end.replace(tzinfo=None)
        if end > now :
            return current_user
    # check 7-day free trial from account creation
    if current_user.created_at :
        created = current_user.created_at
        if created.tzinfo is not None :
            created = created.replace(tzinfo=None)
        if created + timedelta(days=7) > now :
            return current_user
    raise HTTPException(status_code=403, detail="free trial expired, subscription required")