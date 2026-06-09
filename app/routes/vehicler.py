from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.routes.userr import get_current_user

router = APIRouter(
    prefix = "/vehicles",
    tags = ["vehicles"]
)

@router.post("/", status_code = status.HTTP_201_CREATED)
def create_vehicle(vehicle : schemas.VehicleCreate, db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    if vehicle.capacity <= 0 :
        raise HTTPException(status_code = 400, detail = "capacity must be positive")
    new_vehicle = models.Vehicle(
        plate_number = vehicle.plate_number,
        capacity = vehicle.capacity,
        type = vehicle.type,
        user_id = current_user.id
    )
    db.add(new_vehicle)
    db.commit()
    db.refresh(new_vehicle)
    return new_vehicle

@router.get("/", response_model = list[schemas.VehicleOut])
def get_vehicles(db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    vehicles = db.query(models.Vehicle).filter(models.Vehicle.user_id == current_user.id).all()
    return vehicles

@router.get("/{vehicle_id}", response_model = schemas.VehicleOut)
def get_vehicle(vehicle_id : int, db : Session = Depends(get_db), current_user : models.User = Depends(get_current_user)) :
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == vehicle_id, models.Vehicle.user_id == current_user.id).first()
    if not vehicle :
        raise HTTPException(status_code = 404, detail = "vehicle not found")
    return vehicle

@router.delete("/{vehicle_id}", status_code = status.HTTP_204_NO_CONTENT)
def delete_vehicle(vehicle_id : int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)) :
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == vehicle_id, models.Vehicle.user_id == current_user.id).first()
    if not vehicle :
        raise HTTPException(status_code = 404, detail = "vehicle not found")
    if vehicle.route : 
        raise HTTPException(status_code = 400, detail = "vehicle is assigned to an active route")
    db.delete(vehicle)
    db.commit()
    return