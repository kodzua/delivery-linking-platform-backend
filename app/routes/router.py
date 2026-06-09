from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.schemas.routes import RouteStatus
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import cast, String, Float, Numeric
from app.database import get_db
from app.models import Route, User, Shipment
from app.schemas import routes
from app import models
from app.models import notifications
from app.routes.userr import get_current_user, require_active_subscription
from app.services.matching import find_matching_routes, find_matching_routes_by_locations, find_matching_shipments_by_locations, find_matching_routes_by_single_location
from app.services.finalize_matching import finalize
from app.services import search_service
from datetime import date as py_date

router = APIRouter(
    prefix = "/routes",
    tags = ["routes"]
)

@router.post("/", response_model = routes.RouteOut)
def create_route(new_route : routes.RouteCreate, db : Session = Depends(get_db), current_user : User = Depends(require_active_subscription)) :
    route = Route(
        departure_location = new_route.departure_location,
        arrival_location = new_route.arrival_location,
        departure_date = new_route.departure_date,
        estimated_arrival_date = new_route.estimated_arrival_date,
        total_capacity = new_route.total_capacity,
        remaining_capacity = new_route.total_capacity, # same value at creation
        type = new_route.type,
        user_id = current_user.id,
        vehicle_id = new_route.vehicle_id
    )
    db.add(route)
    db.commit()
    db.refresh(route)
    return route

@router.get("/my", response_model = list[routes.RouteOut])
def get_my_routes(db : Session = Depends(get_db), current_user : User = Depends(get_current_user)) :
    return db.query(Route).options(joinedload(Route.vehicle)).filter(Route.user_id == current_user.id, Route.status != RouteStatus.cancelled).all()

@router.get("/", response_model = list[routes.RouteOut])  # shipper's feed
def get_routes(source : Optional[str] = Query(None), dest : Optional[str] = Query(None), owner : Optional[str] = Query(None), capacity : Optional[float] = Query(None), direction : Optional[str] = Query(None), vehicle_types : Optional[list[str]] = Query(None), date : Optional[str] = Query(None), db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    def clean_any(v) :
        if v in [None, "", "Any wilaya", "Any direction", "Any vehicle type"] :
            return None
        return v
    source = clean_any(source)
    dest = clean_any(dest)
    direction = clean_any(direction)
    query = db.query(models.Route).options(joinedload(models.Route.vehicle)).join(models.User, models.Route.user_id == models.User.id).filter(models.User.is_available == True, models.Route.user_id != current_user.id, models.Route.status == models.route.route_status_enum.open)
    if capacity is not None and capacity != "":
        query = query.filter(cast(models.Route.remaining_capacity, Float) >= float(capacity))
    if source and dest :
        matched_routes = find_matching_routes_by_locations(db, source, dest, 0)
        query = query.filter(models.Route.id.in_([r.id for r in matched_routes]))
    elif source :
        matched_routes = find_matching_routes_by_single_location(db, source)
        query = query.filter(models.Route.id.in_([r.id for r in matched_routes]))
    elif dest :
        matched_routes = find_matching_routes_by_single_location(db, dest)
        query = query.filter(models.Route.id.in_([r.id for r in matched_routes]))
    if owner:
        query = query.filter(models.User.name.ilike(f"%{owner}%"))
    if direction :
        query = query.filter(cast(models.Route.type, String) == direction)
    if vehicle_types and len(vehicle_types) > 0 :
        valid_types = [t for t in vehicle_types if clean_any(t)]
        if valid_types :
            query = query.filter(models.Route.vehicle.has(models.Vehicle.type.in_(valid_types)))
    if date :
        try :
            if "/" in date :
                d, m, y = date.split("/")
                d_obj = py_date(int(y), int(m), int(d))
            else :
                d_obj = py_date.fromisoformat(date)
            query = query.filter(models.Route.departure_date == d_obj)
        except :
            pass
    all_routes = query.order_by(models.Route.created_at.desc(), models.Route.id.desc()).all()
    shipments = db.query(models.Shipment).filter(models.Shipment.user_id == current_user.id).all()
    if not shipments :
        return all_routes
    matched_set = set()
    matched = []
    others = []
    all_route_ids = {r.id for r in all_routes}
    for shipment in shipments :
        for r in find_matching_routes(db, shipment) :
            if r.id in all_route_ids and r.id not in matched_set :
                matched_set.add(r.id)
                matched.append(r)
    for r in all_routes :
        if r.id not in matched_set :
            others.append(r)
    matched.sort(key = lambda x : (x.created_at or x.departure_date, x.id), reverse = True)
    others.sort(key = lambda x : (x.created_at or x.departure_date, x.id), reverse = True)
    return matched + others

@router.patch("/{route_id}")
def update_route(route_id : int, update_data : routes.RouteUpdate, db : Session = Depends(get_db), current_user : User = Depends(get_current_user)) :
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route :
        raise HTTPException(status_code = 404, detail = "route not found")
    if route.user_id != current_user.id :
        raise HTTPException(status_code = 403, detail = "not authorized")
    if route.status != RouteStatus.open :
        raise HTTPException(status_code = 400, detail = "cannot modify this route")
    update_dict = update_data.model_dump(exclude_unset = True)
    if "remaining_capacity" in update_dict or "total_capacity" in update_dict :
        new_total = update_dict.get("total_capacity", route.total_capacity)
        new_remaining = update_dict.get("remaining_capacity", route.remaining_capacity)
        if new_remaining < 0 :
            raise HTTPException(status_code = 400, detail = "remaining_capacity cannot be negative")
        if new_remaining > new_total :
            raise HTTPException(status_code = 400, detail = "remaining_capacity cannot exceed total_capacity")
    for key, value in update_dict.items() :
        setattr(route, key, value)
    db.commit()
    db.refresh(route)
    return route

@router.delete("/{route_id}")
def delete_route(route_id : int, db : Session = Depends(get_db), current_user : User = Depends(get_current_user)) :
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route :
        raise HTTPException(status_code = 404, detail = "route not found")
    if route.user_id != current_user.id :
        raise HTTPException(status_code = 403, detail = "not authorized")
    route.status = RouteStatus.cancelled
    db.commit()
    return {"message" : "route cancelled"}

@router.get("/{route_id}/matches") # driver's matches page
def get_matches(route_id : int, db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    route = db.query(models.Route).filter(models.Route.id == route_id).first()
    if not route :
        raise HTTPException(status_code = 404, detail = "route not found")
    if route.user_id != current_user.id :
        raise HTTPException(status_code = 403, detail = "not authorized")
    active_statuses = [models.shipment.shipment_status_enum.matched, models.shipment.shipment_status_enum.in_transit]
    shipments = db.query(models.Shipment).filter(models.Shipment.route_id == route.id, models.Shipment.status.in_(active_statuses)).all()
    return {
        "route_id" : route.id,
        "shipments" : shipments
    }

@router.patch("/{route_id}/request-shipment/{shipment_id}")
def driver_requests(route_id : int, shipment_id : int, db : Session = Depends(get_db), current_user : User = Depends(get_current_user)) :
    route = db.query(Route).filter(Route.id == route_id).first()
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not route or not shipment :
        raise HTTPException(status_code = 404, detail = "not found")
    if route.user_id != current_user.id :
        raise HTTPException(status_code = 403, detail = "not your route")
    if shipment.status != models.shipment.shipment_status_enum.posted :
        raise HTTPException(status_code = 400, detail = "shipment not available")
    if route_id not in shipment.requesting_routes :
        shipment.requesting_routes.append(route_id)
        db.add(notifications.Notification(user_id = shipment.user_id, notification_type = notifications.NotificationType.request, message = f"New Shipment Request: A driver has requested your shipment to {shipment.delivery_location.value if hasattr(shipment.delivery_location, 'value') else shipment.delivery_location}.", target_id = shipment.id, target_type = "shipment"))
    db.commit()
    return {"message" : "driver request sent"}

@router.delete("/{route_id}/request-shipment/{shipment_id}")
def cancel_driver_request(route_id : int, shipment_id : int, db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    route = db.query(models.Route).filter(models.Route.id == route_id).first()
    shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    if not route or not shipment :
        raise HTTPException(status_code = 404, detail = "not found")
    if route.user_id != current_user.id :
        raise HTTPException(status_code = 403, detail = "not your route")
    if route_id in shipment.requesting_routes :
        shipment.requesting_routes.remove(route_id)
    if shipment_id in route.requesting_shippers :
        route.requesting_shippers.remove(shipment_id)
    db.commit()
    return {"message" : "request cancelled by driver"}

@router.get("/outgoing-requests")
def get_outgoing_shipment_requests(db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    routes = db.query(models.Route).filter(models.Route.user_id == current_user.id).all()
    route_ids = [r.id for r in routes]
    if not route_ids :
        return []
    shipments = db.query(models.Shipment).filter(models.Shipment.user_id != current_user.id, models.Shipment.status == models.shipment.shipment_status_enum.posted).all()
    result = []
    seen = set()
    for shipment in shipments :
        if not shipment.requesting_routes :
            continue
        for route_id in shipment.requesting_routes :
            if route_id in route_ids :
                request_key = f"{route_id}-{shipment.id}"
                if request_key in seen:
                    continue
                seen.add(request_key)
                route = next(r for r in routes if r.id == route_id)
                result.append({
                    "route_id" : route_id,
                    "shipment_id" : shipment.id,
                    "pickup" : shipment.pickup_location,
                    "delivery" : shipment.delivery_location,
                    "size" : shipment.size,
                    "departure": route.departure_location,
                    "arrival": route.arrival_location,
                    "date": route.departure_date.isoformat() if route.departure_date else None,
                    "notes": shipment.notes,
                    "counterpart": shipment.user.name if shipment.user else "shipper"
                })
    return result 

@router.get("/incoming-requests")
def get_incoming_shipment_requests(db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    routes = db.query(models.Route).filter(models.Route.user_id == current_user.id).all()
    result = []
    for route in routes :
        if not route.requesting_shippers :
            continue
        shipments = db.query(models.Shipment).filter(models.Shipment.id.in_(route.requesting_shippers), models.Shipment.user_id != current_user.id, models.Shipment.status == models.shipment.shipment_status_enum.posted).all()
        for shipment in shipments :
            result.append({
                "route_id" : route.id,
                "shipment_id" : shipment.id,
                "pickup" : shipment.pickup_location,
                "delivery" : shipment.delivery_location,
                "size" : shipment.size,
                "departure" : route.departure_location,
                "arrival" : route.arrival_location,
                "date" : route.departure_date.isoformat() if route.departure_date else None,
                "notes" : shipment.notes,
                "counterpart" : shipment.user.name if shipment.user else "shipper"
            })
    return result

@router.patch("/{route_id}/accept-shipment/{shipment_id}")
def driver_accept_shipment(route_id : int, shipment_id : int, db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    route = db.query(models.Route).filter(models.Route.id == route_id).first()
    shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    if not route or not shipment :
        raise HTTPException(status_code = 404, detail = "route or shipment not found")
    if route.user_id != current_user.id :
        raise HTTPException(status_code = 403, detail = "not authorized")
    if shipment.status != models.shipment.shipment_status_enum.posted :
        raise HTTPException(status_code = 400, detail = "shipment already processed")
    success = finalize(shipment, route)
    if not success :
        raise HTTPException(status_code = 400, detail = "finalization failed")
    db.add(notifications.Notification(user_id = shipment.user_id, notification_type = notifications.NotificationType.accept, message=f"Match Confirmed: Your shipment to {shipment.delivery_location.value if hasattr(shipment.delivery_location, 'value') else shipment.delivery_location} has been finalized.", target_id = shipment.id, target_type = "shipment"))
    db.commit()
    return {
        "shipment_id" : shipment.id,
        "route_id" : route.id,
        "status" : shipment.status,
        "remaining_capacity" : route.remaining_capacity
    }

@router.patch("/{route_id}/decline-shipment/{shipment_id}")
def driver_decline_shipment(route_id : int, shipment_id : int, db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    route = db.query(models.Route).filter(models.Route.id == route_id).first()
    shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    if not route or not shipment :
        raise HTTPException(status_code = 404, detail = "not found")
    if route.user_id != current_user.id :
        raise HTTPException(status_code = 403, detail = "not your route")
    if shipment_id in route.requesting_shippers :
        route.requesting_shippers.remove(shipment_id)
    if route_id in shipment.requesting_routes :
        shipment.requesting_routes.remove(route_id)
    db.add(notifications.Notification(user_id = shipment.user_id, notification_type=notifications.NotificationType.reject, message = f"Request Declined: A driver declined your shipment to {shipment.delivery_location.value if hasattr(shipment.delivery_location, 'value') else shipment.delivery_location}.", target_id = shipment.id, target_type = "shipment"))
    db.commit()
    return {"message" : "shipment request declined by driver"}

@router.delete("/{route_id}/cancel-match/{shipment_id}")
def driver_cancel_match(route_id : int, shipment_id : int, db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    route = db.query(models.Route).filter(models.Route.id == route_id).first()
    shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    if not route or not shipment :
        raise HTTPException(status_code = 404, detail = "not found")
    if route.user_id != current_user.id :
        raise HTTPException(status_code = 403, detail = "not your route")
    if shipment.route_id != route_id :
        raise HTTPException(status_code = 400, detail = "shipment is not matched to this route")
    route.remaining_capacity = (route.remaining_capacity or 0) + (shipment.size or 0)
    route.status = RouteStatus.open
    shipment.route_id = None
    shipment.status = models.shipment.shipment_status_enum.posted
    db.commit()
    return {"message" : "match cancelled by driver"}
