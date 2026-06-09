from app import models

def finalize(shipment, route) :
    if route.remaining_capacity < shipment.size :
        return False
    driver_requested = shipment.requesting_routes and route.id in shipment.requesting_routes
    shipper_requested = route.requesting_shippers and shipment.id in route.requesting_shippers
    if not (shipper_requested or driver_requested) :
        return False
    shipment.route_id = route.id
    shipment.status = models.shipment.shipment_status_enum.matched
    route.remaining_capacity = route.remaining_capacity - shipment.size
    return True