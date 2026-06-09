from sqlalchemy.orm import Session
from sqlalchemy.orm import Session
from app.models import Route  

def search_routes(db : Session, source, dest, owner, capacity, direction) :
    query = db.query(Route)
    if source :
        query = query.filter(Route.departure_location == source)
    if dest :
        query = query.filter(Route.arrival_location == dest)
    if owner :
        query = query.filter(Route.owner.ilike(f"%{owner}%"))
    if capacity :
        query = query.filter(Route.remaining_capacity >= capacity)
    if direction and direction != "Any direction" :
        query = query.filter(Route.type == direction)
    return query.all()