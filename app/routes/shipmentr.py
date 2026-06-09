from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from typing import Optional
from sqlalchemy import cast, String, Float
from app.routes.userr import get_current_user, require_active_subscription
from app.services.matching import find_matching_shipments, find_matching_shipments_by_locations, find_matching_shipments_by_single_location
from sqlalchemy.orm import Session
from app import models, schemas
from app.models import notifications
from app.database import get_db
from app.services.finalize_matching import finalize
from pathlib import Path
from fastapi import UploadFile, File, Form
from datetime import date as py_date
import cloudinary
import cloudinary.uploader
import os
import shutil

router = APIRouter(
    prefix = "/shipments",
    tags = ["shipments"]
)

cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET")
)

@router.post("/", status_code = status.HTTP_201_CREATED)
def create_shipment(pickup_location : str = Form(...), delivery_location : str = Form(...), pickup_date : str = Form(...), size : float = Form(...), volume : float = Form(None), notes : str = Form(None), photo : UploadFile = File(None), db : Session = Depends(get_db), current_user : models.User = Depends(require_active_subscription)) :
    photo_url = None
    if photo :
        try :
            upload_result = cloudinary.uploader.upload(photo.file)
            photo_url = upload_result.get("secure_url")
        except Exception :
            raise HTTPException(status_code = 500, detail = "photo upload failed")
    new_shipment = models.Shipment(
        pickup_location = pickup_location,
        delivery_location = delivery_location,
        pickup_date = pickup_date,
        size = size,
        user_id = current_user.id,
        notes = notes,
        volume = volume,
        photo = photo_url
    )
    db.add(new_shipment)
    db.commit()
    db.refresh(new_shipment)
    return new_shipment

@router.get("/my-outgoing-requests")
def get_my_requested_routes(db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    shipments = db.query(models.Shipment).filter(models.Shipment.user_id == current_user.id, models.Shipment.status == models.shipment.shipment_status_enum.posted, models.Shipment.route_id == None).all()
    shipment_ids = [s.id for s in shipments]
    if not shipment_ids :
        return []
    routes = db.query(models.Route).filter(models.Route.user_id != current_user.id).all()
    result = []
    seen = set()
    for route in routes :
        if not route.requesting_shippers :
            continue
        for shipment_id in route.requesting_shippers :
            if shipment_id in shipment_ids :
                request_key = f"{route.id}-{shipment_id}"
                if request_key in seen:
                    continue
                seen.add(request_key)
                shipment = next(s for s in shipments if s.id == shipment_id)
                result.append({
                    "route_id" : route.id,
                    "departure" : route.departure_location,
                    "arrival" : route.arrival_location,
                    "date" : route.departure_date.isoformat() if route.departure_date else None,
                    "shipment_id" : shipment_id, 
                    "pickup" : shipment.pickup_location,
                    "delivery" : shipment.delivery_location,
                    "size" : shipment.size,
                    "notes" : shipment.notes,
                    "direction" : route.type,
                    "counterpart" : route.user.name if route.user else "Driver"
                })
    return result

@router.get("/my-incoming-requests")
def get_incoming_route_requests(db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    shipments = db.query(models.Shipment).filter(models.Shipment.user_id == current_user.id, models.Shipment.status == models.shipment.shipment_status_enum.posted, models.Shipment.route_id == None).all()
    result = []
    for shipment in shipments :
        if not shipment.requesting_routes :
            continue
        routes = db.query(models.Route).filter(models.Route.id.in_(shipment.requesting_routes), models.Route.user_id != current_user.id).all()
        for route in routes :
            result.append({
                "shipment_id" : shipment.id,
                "pickup" : shipment.pickup_location,
                "delivery" : shipment.delivery_location,
                "size" : shipment.size,
                "notes" : shipment.notes,
                "route_id" : route.id,
                "departure" : route.departure_location,
                "arrival" : route.arrival_location,
                "date" : route.departure_date.isoformat() if route.departure_date else None,
                "capacity" : route.remaining_capacity,
                "direction" : route.type,
                "counterpart" : route.user.name if route.user else "Driver"
            })
    return result

@router.get("/me", response_model = list[schemas.ShipmentOut]) # for the shipper's profile
def get_my_shipments(db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    return db.query(models.Shipment).filter(models.Shipment.user_id == current_user.id, models.Shipment.status != models.shipment.shipment_status_enum.cancelled).all()
  
@router.get("/{shipment_id}", response_model = schemas.ShipmentOut)
def get_shipment(shipment_id : int, db : Session = Depends(get_db)) :
    shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    if not shipment :
        raise HTTPException(status_code = 404, detail = "shipment not found")
    return shipment

@router.get("/", response_model = list[schemas.ShipmentOut]) # driver's feed
def get_shipments(source : Optional[str] = Query(None), dest : Optional[str] = Query(None), owner : Optional[str] = Query(None), weight_min : Optional[float] = Query(None), weight_max : Optional[float] = Query(None), volume : Optional[float] = Query(None), date : Optional[str] = Query(None), db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    def clean_any(v):
        if v in [None, "", "Any wilaya", "Any direction", "Any vehicle type"]:
            return None
        return v
    source = clean_any(source)
    dest = clean_any(dest)
    query = db.query(models.Shipment).join(models.User, models.Shipment.user_id == models.User.id).filter(
        models.User.is_available == True,
        models.Shipment.user_id != current_user.id,
        models.Shipment.status == models.shipment.shipment_status_enum.posted
    )
    if source and dest :
        matched_shipments = find_matching_shipments_by_locations(db, source, dest, weight_max if weight_max else 1000000)
        query = query.filter(models.Shipment.id.in_([s.id for s in matched_shipments]))
    elif source :
        matched_shipments = find_matching_shipments_by_single_location(db, source, is_pickup = True)
        query = query.filter(models.Shipment.id.in_([s.id for s in matched_shipments]))
    elif dest :
        matched_shipments = find_matching_shipments_by_single_location(db, dest, is_pickup = False)
        query = query.filter(models.Shipment.id.in_([s.id for s in matched_shipments]))
    if weight_min is not None :
        query = query.filter(cast(models.Shipment.size, Float) >= weight_min)
    if weight_max is not None :
        query = query.filter(cast(models.Shipment.size, Float) <= weight_max)
    if volume :
        query = query.filter(cast(models.Shipment.volume, Float) >= volume)
    if owner :
        query = query.filter(models.User.name.ilike(f"%{owner}%"))
    if date :
        try :
            if "/" in date :
                d, m, y = date.split("/")
                d_obj = py_date(int(y), int(m), int(d))
            else :
                d_obj = py_date.fromisoformat(date)
            query = query.filter(models.Shipment.pickup_date == d_obj)
        except :
            pass
    all_shipments = query.order_by(models.Shipment.created_at.desc(), models.Shipment.id.desc()).all()
    routes = db.query(models.Route).filter(models.Route.user_id == current_user.id, models.Route.status == "open").all()
    if not routes :
        return all_shipments
    matched_set = set()
    matched = []
    others = []
    all_shipment_ids = {s.id for s in all_shipments}
    for route in routes :
        route_matches = find_matching_shipments(db, route)
        for s in route_matches :
            if s.id in all_shipment_ids and s.id not in matched_set :
                matched_set.add(s.id)
                matched.append(s)
    for s in all_shipments :
        if s.id not in matched_set :
            others.append(s)
    matched.sort(key = lambda x: (x.created_at or x.pickup_date, x.id), reverse = True)
    others.sort(key = lambda x: (x.created_at or x.pickup_date, x.id), reverse = True)
    return matched + others

@router.patch("/{shipment_id}", response_model = schemas.ShipmentOut)
def update_shipment(shipment_id : int, shipment_in : schemas.ShipmentUpdate = Depends(), photo : UploadFile = File(None), db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    if not shipment :
        raise HTTPException(status_code = 404, detail = "shipment not found")
    is_shipper = shipment.user_id == current_user.id
    is_driver = False
    if shipment.route_id:
        route = db.query(models.Route).filter(models.Route.id == shipment.route_id).first()
        if route and route.user_id == current_user.id:
            is_driver = True
    if not is_shipper and not is_driver :
        raise HTTPException(status_code = 403, detail = "not authorized")
    update_data = shipment_in.model_dump(exclude_unset = True)
    if is_driver and not is_shipper :
        update_data = {k : v for k, v in update_data.items() if k == "status"}
    if shipment.status != models.shipment.shipment_status_enum.posted :
        if any([
            shipment_in.pickup_location,
            shipment_in.delivery_location,
            shipment_in.pickup_date,
            shipment_in.size,
            shipment_in.notes,
            shipment_in.volume
        ]) :
            raise HTTPException(status_code = 400, detail = "cannot modify shipment details")
    if photo :
        try :
            upload_result = cloudinary.uploader.upload(photo.file)
            new_photo_url = upload_result.get("secure_url")
            if shipment.photo :
                try :
                    public_id = Path(shipment.photo).stem
                    cloudinary.uploader.destroy(public_id)
                except Exception :
                    pass  
            shipment.photo = new_photo_url
        except Exception :
            raise HTTPException(status_code = 500, detail = "photo upload failed")
    if "volume" in update_data and update_data["volume"] is None :
        raise HTTPException(status_code = 400, detail = "volume cannot be null")
    if "status" in update_data :
        current = shipment.status
        new_status = update_data["status"]
        valid_transitions = {
            models.shipment.shipment_status_enum.posted : [
                models.shipment.shipment_status_enum.matched,
                models.shipment.shipment_status_enum.posted
            ],
            models.shipment.shipment_status_enum.matched : [
                models.shipment.shipment_status_enum.in_transit,
                models.shipment.shipment_status_enum.matched
            ],
            models.shipment.shipment_status_enum.in_transit : [
                models.shipment.shipment_status_enum.delivered,
                models.shipment.shipment_status_enum.in_transit
            ],
        }
        if new_status not in valid_transitions.get(current, []) :
            raise HTTPException(status_code = 400, detail = f"invalid status transition from {current.value} to {new_status.value}")
        shipment.status = new_status
        if new_status == models.shipment.shipment_status_enum.delivered:
            db.add(notifications.Notification(
                user_id = shipment.user_id,
                notification_type = notifications.NotificationType.accept, 
                message = f"Package Delivered : Your shipment from {shipment.pickup_location.value if hasattr(shipment.pickup_location, 'value') else shipment.pickup_location} has been marked as delivered.",
                target_id = shipment.id,
                target_type = "shipment"
            ))
            
        update_data.pop("status")
    for key, value in update_data.items() :
        setattr(shipment, key, value)
    db.commit()
    db.refresh(shipment)
    return shipment

@router.delete("/{shipment_id}")
def delete_shipment(shipment_id : int, db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    if not shipment :
        raise HTTPException(status_code = 404, detail = "shipment not found")
    if shipment.user_id != current_user.id :
        raise HTTPException(status_code = 403, detail = "not authorized")
    shipment.status = models.shipment.shipment_status_enum.cancelled
    db.commit()
    return {"message" : "shipment cancelled"}

@router.patch("/{shipment_id}/request-route/{route_id}")
def shipper_requests(shipment_id : int, route_id : int, db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    route = db.query(models.Route).filter(models.Route.id == route_id).first()
    if not shipment or not route :
        raise HTTPException(status_code = 404, detail = "not found")
    if shipment.user_id != current_user.id :
        raise HTTPException(status_code = 403, detail = "not your shipment")
    if shipment.status != models.shipment.shipment_status_enum.posted :
        raise HTTPException(status_code = 400, detail = "shipment not available")
    if shipment_id not in route.requesting_shippers :
        route.requesting_shippers.append(shipment_id)
        db.add(notifications.Notification(user_id = route.user_id, notification_type = notifications.NotificationType.request, message = f"New Route Request: A shipper is interested in your route to {route.arrival_location.value if hasattr(route.arrival_location, 'value') else route.arrival_location}.", target_id = route.id, target_type = "route"))
    db.commit()
    return {"message" : "shipper request sent"}

@router.patch("/{shipment_id}/assign") # for when the shipper click accept after a driver requests to take the shipment
def assign_shipment(shipment_id : int, route_id : int = Query(...), db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    route = db.query(models.Route).filter(models.Route.id == route_id).first()
    if not shipment or not route :
        raise HTTPException(status_code = 404, detail = "shipment or route not found")
    if shipment.user_id != current_user.id :
        raise HTTPException(status_code = 403, detail = "not authorized")
    if shipment.status != models.shipment.shipment_status_enum.posted :
        raise HTTPException(status_code = 400, detail = "shipment already processed")
    success = finalize(shipment, route)
    if not success :
        raise HTTPException(status_code = 400, detail = "finalization failed")
    shipment.requesting_routes = []
    db.add(notifications.Notification(user_id = route.user_id, notification_type = notifications.NotificationType.accept, message = f"New Shipment Assigned: A shipper has assigned their delivery to {route.arrival_location.value if hasattr(route.arrival_location, 'value') else route.arrival_location} to your route.", target_id = route.id, target_type = "route"))
    db.commit()
    return {
        "shipment_id" : shipment.id,
        "route_id" : route.id,
        "status" : shipment.status,
        "remaining_capacity" : route.remaining_capacity
    }

@router.patch("/{shipment_id}/decline-route/{route_id}")
def shipper_decline_route(shipment_id : int, route_id : int, db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    route = db.query(models.Route).filter(models.Route.id == route_id).first()
    if not shipment or not route :
        raise HTTPException(status_code = 404, detail = "not found")
    if shipment.user_id != current_user.id :
        raise HTTPException(status_code = 403, detail = "not your shipment")
    if route_id in shipment.requesting_routes :
        shipment.requesting_routes.remove(route_id)
    if shipment_id in route.requesting_shippers :
        route.requesting_shippers.remove(shipment_id)
    db.add(notifications.Notification(user_id = route.user_id, notification_type = notifications.NotificationType.reject, message = f"Request Declined: A shipper declined your route to {route.arrival_location.value if hasattr(route.arrival_location, 'value') else route.arrival_location}.", target_id = route.id, target_type = "route"))
    db.commit()
    return {"message" : "route request declined by shipper"}

@router.delete("/{shipment_id}/request-route/{route_id}")
def cancel_shipper_request(shipment_id : int, route_id : int, db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    route = db.query(models.Route).filter(models.Route.id == route_id).first()
    if not shipment or not route :
        raise HTTPException(status_code = 404, detail = "not found")
    if shipment.user_id != current_user.id :
        raise HTTPException(status_code = 403, detail = "not your shipment")
    if shipment_id in route.requesting_shippers :
        route.requesting_shippers.remove(shipment_id)
    if route_id in shipment.requesting_routes :
        shipment.requesting_routes.remove(route_id)
    db.commit()
    return {"message" : "request cancelled by shipper"}

@router.get("/{shipment_id}/match") # for the shipper's matches' page
def get_match(shipment_id : int, db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    if not shipment :
        raise HTTPException(status_code = 404, detail = "shipment not found")
    if shipment.user_id != current_user.id :
        raise HTTPException(status_code = 403, detail = "not authorized")
    active_statuses = [models.shipment.shipment_status_enum.matched, models.shipment.shipment_status_enum.in_transit]
    if shipment.status not in active_statuses :
        return {
            "shipment_id" : shipment.id,
            "route" : None,
            "status" : shipment.status
        }
    route = db.query(models.Route).filter(models.Route.id == shipment.route_id).first()
    driver = db.query(models.User).filter(models.User.id == route.user_id).first() if route else None
    return {
        "shipment_id" : shipment.id,
        "route" : route,
        "driver_name" : driver.name if driver else "Driver",
        "driver_phone" : driver.phone_number if driver else None
    }

@router.delete("/{shipment_id}/cancel-match")
def cancel_confirmed_match(shipment_id : int, db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    if not shipment :
        raise HTTPException(status_code = 404, detail = "shipment not found")
    if shipment.user_id != current_user.id :
        raise HTTPException(status_code = 403, detail = "not authorized")
    if shipment.route_id is None :
        raise HTTPException(status_code = 400, detail = "shipment is not matched to any route")
    route = db.query(models.Route).filter(models.Route.id == shipment.route_id).first()
    if route :
        route.remaining_capacity = (route.remaining_capacity or 0) + (shipment.size or 0)
        route.status = models.route.route_status_enum.open
    shipment.route_id = None
    shipment.status = models.shipment.shipment_status_enum.posted
    db.commit()
    return {"message" : "match cancelled successfully"}
