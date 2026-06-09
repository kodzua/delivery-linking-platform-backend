from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.routes.userr import get_current_user
from app import models

router = APIRouter(
    prefix = "/shipments", 
    tags = ["contact"]
)

@router.get("/{shipment_id}/contact") # for the shipper
def get_trucker_contact(shipment_id : int, db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    if not shipment :
        raise HTTPException(status_code = 404, detail = "shipment not found")
    if shipment.status != models.shipment.shipment_status_enum.matched :
        raise HTTPException(status_code = 400, detail = "contact not available unless shipment is matched")
    if not shipment.route_id:
        raise HTTPException(status_code = 400, detail = "shipment is not assigned to any route")
    route = db.query(models.Route).filter(models.Route.id == shipment.route_id).first()
    if not route :
        raise HTTPException(status_code = 404, detail = "route not found")
    if current_user.id not in [shipment.user_id, route.user_id] :
        raise HTTPException(status_code = 403, detail = "not authorized to view contact info")
    trucker = db.query(models.User).filter(models.User.id == route.user_id).first()
    return {"contact" : trucker.phone_number}
    
@router.get("/{route_id}/contactt") # for the driver
def get_shipper_contact(route_id : int, db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    route = db.query(models.Route).filter(models.Route.id == route_id).first()
    if not route :
        raise HTTPException(status_code = 404, detail = "route not found")
    shipment = db.query(models.Shipment).filter(models.Shipment.route_id == route_id, models.Shipment.status == models.shipment.shipment_status_enum.matched).first()
    if not shipment :
        raise HTTPException(status_code = 400, detail = "no matched shipment for this route")
    if current_user.id not in [shipment.user_id, route.user_id] :
        raise HTTPException(status_code = 403, detail = "not authorized")
    shipper = db.query(models.User).filter(models.User.id == shipment.user_id).first()
    return {"contact" : shipper.phone_number}