from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload
from app.models import Route, Shipment

def find_matching_routes(session : Session, shipment : Shipment) :
    statement = text("""
        SELECT r.id FROM route r
        JOIN wilaya_coords s_p ON :p_loc = s_p.name
        JOIN wilaya_coords s_d ON :d_loc = s_d.name
        JOIN wilaya_coords r_o ON r_o.name = REPLACE(CAST(r.departure_location AS TEXT), '_', ' ')
        LEFT JOIN wilaya_coords r_a ON r_a.name = REPLACE(CAST(r.arrival_location AS TEXT), '_', ' ')
        JOIN "user" u ON r.user_id = u.id
        WHERE r.status = 'open' AND u.is_available = True AND r.remaining_capacity >= :s_size 
            AND (
                (r.arrival_location IS NULL AND ST_DWithin(s_p.geom, r_o.geom::geography, 50000))
                OR
                (r.arrival_location IS NOT NULL AND (
                    CASE 
                        WHEN ST_Distance(r_o.geom::geography, r_a.geom::geography) < 5000 
                            THEN ST_DWithin(s_p.geom, r_o.geom::geography, 50000)
                        ELSE (
                            ((ST_Distance(r_o.geom::geography, s_p.geom::geography) + 
                              ST_Distance(s_p.geom::geography, s_d.geom::geography) + 
                              ST_Distance(s_d.geom::geography, r_a.geom::geography)) 
                             / ST_Distance(r_o.geom::geography, r_a.geom::geography) <= 1.15)
                            OR
                            (CAST(r.type AS TEXT) = 'round_trip' AND 
                             (ST_Distance(r_a.geom::geography, s_p.geom::geography) + 
                              ST_Distance(s_p.geom::geography, s_d.geom::geography) + 
                              ST_Distance(s_d.geom::geography, r_o.geom::geography)) 
                             / ST_Distance(r_a.geom::geography, r_o.geom::geography) <= 1.15)
                        )
                    END
                ))
            );
    """)
    params = {
        "p_loc" : shipment.pickup_location.value,
        "d_loc" : shipment.delivery_location.value,
        "s_size" : shipment.size
    }
    results = session.execute(statement, params)
    route_ids = [row['id'] for row in results.mappings()]
    if not route_ids:
        return []
    return session.query(Route).options(joinedload(Route.vehicle)).filter(Route.id.in_(route_ids)).all()

def find_matching_routes_by_locations(session: Session, p_loc: str, d_loc: str, s_size: float = 0):
    statement = text("""
        SELECT r.id FROM route r
        JOIN wilaya_coords s_p ON :p_loc = s_p.name
        JOIN wilaya_coords s_d ON :d_loc = s_d.name
        JOIN wilaya_coords r_o ON r_o.name = REPLACE(CAST(r.departure_location AS TEXT), '_', ' ')
        LEFT JOIN wilaya_coords r_a ON r_a.name = REPLACE(CAST(r.arrival_location AS TEXT), '_', ' ')
        JOIN "user" u ON r.user_id = u.id
        WHERE r.status = 'open' AND u.is_available = True AND r.remaining_capacity >= :s_size 
            AND (
                (r.arrival_location IS NULL AND ST_DWithin(s_p.geom, r_o.geom::geography, 50000))
                OR
                (r.arrival_location IS NOT NULL AND (
                    CASE 
                        WHEN ST_Distance(r_o.geom::geography, r_a.geom::geography) < 5000 
                            THEN ST_DWithin(s_p.geom, r_o.geom::geography, 50000)
                        ELSE (
                            ((ST_Distance(r_o.geom::geography, s_p.geom::geography) + 
                              ST_Distance(s_p.geom::geography, s_d.geom::geography) + 
                              ST_Distance(s_d.geom::geography, r_a.geom::geography)) 
                             / ST_Distance(r_o.geom::geography, r_a.geom::geography) <= 1.15)
                            OR
                            (CAST(r.type AS TEXT) = 'round_trip' AND 
                             (ST_Distance(r_a.geom::geography, s_p.geom::geography) + 
                              ST_Distance(s_p.geom::geography, s_d.geom::geography) + 
                              ST_Distance(s_d.geom::geography, r_o.geom::geography)) 
                             / ST_Distance(r_a.geom::geography, r_o.geom::geography) <= 1.15)
                        )
                    END
                ))
            );
    """)
    params = {"p_loc": p_loc, "d_loc": d_loc, "s_size": s_size}
    results = session.execute(statement, params)
    route_ids = [row['id'] for row in results.mappings()]
    if not route_ids:
        return []
    return session.query(Route).options(joinedload(Route.vehicle)).filter(Route.id.in_(route_ids)).all()

def find_matching_shipments(session : Session, route : Route) :
    statement = text("""
        SELECT s.* FROM shipment s
        JOIN wilaya_coords r_o ON r_o.name = REPLACE(CAST(:dep_loc AS TEXT), '_', ' ')
        LEFT JOIN wilaya_coords r_a ON r_a.name = REPLACE(CAST(:arr_loc AS TEXT), '_', ' ')
        JOIN wilaya_coords s_p ON s_p.name = REPLACE(CAST(s.pickup_location AS TEXT), '_', ' ')
        JOIN wilaya_coords s_d ON s_d.name = REPLACE(CAST(s.delivery_location AS TEXT), '_', ' ')
        JOIN "user" u ON s.user_id = u.id
        WHERE s.status = 'posted' AND u.is_available = True AND :rem_cap >= s.size 
            AND (
                (:arr_loc IS NULL AND ST_DWithin(s_p.geom, r_o.geom::geography, 50000))
                OR
                (:arr_loc IS NOT NULL AND (
                    CASE 
                        WHEN ST_Distance(r_o.geom::geography, r_a.geom::geography) < 5000 
                            THEN ST_DWithin(s_p.geom, r_o.geom::geography, 50000)
                        ELSE (
                            ((ST_Distance(r_o.geom::geography, s_p.geom::geography) + 
                              ST_Distance(s_p.geom::geography, s_d.geom::geography) + 
                              ST_Distance(s_d.geom::geography, r_a.geom::geography)) 
                             / ST_Distance(r_o.geom::geography, r_a.geom::geography) <= 1.15)
                            OR
                            (:r_type = 'round_trip' AND 
                             (ST_Distance(r_a.geom::geography, s_p.geom::geography) + 
                              ST_Distance(s_p.geom::geography, s_d.geom::geography) + 
                              ST_Distance(s_d.geom::geography, r_o.geom::geography)) 
                             / ST_Distance(r_a.geom::geography, r_o.geom::geography) <= 1.15)
                        )
                    END
                ))
            );
    """)
    params = {
        "dep_loc" : route.departure_location.value,
        "arr_loc" : route.arrival_location.value if route.arrival_location else None,
        "rem_cap" : route.remaining_capacity,
        "r_type" : route.type.value  
    }
    results = session.execute(statement, params)
    shipment_ids = [row['id'] for row in results.mappings()]
    if not shipment_ids:
        return []
    return session.query(Shipment).filter(Shipment.id.in_(shipment_ids)).all()

def find_matching_routes_by_single_location(session: Session, loc: str, is_source: bool = True):
    statement = text("""
        SELECT r.id FROM route r
        JOIN wilaya_coords s ON :loc = s.name
        JOIN wilaya_coords r_o ON r_o.name = REPLACE(CAST(r.departure_location AS TEXT), '_', ' ')
        LEFT JOIN wilaya_coords r_a ON r_a.name = REPLACE(CAST(r.arrival_location AS TEXT), '_', ' ')
        JOIN "user" u ON r.user_id = u.id
        WHERE r.status = 'open' AND u.is_available = True
            AND (
                (r.arrival_location IS NULL AND ST_DWithin(s.geom, r_o.geom::geography, 50000))
                OR
                (r.arrival_location IS NOT NULL AND (
                    ST_DWithin(s.geom, ST_MakeLine(r_o.geom::geometry, r_a.geom::geometry)::geography, 50000)
                ))
            );
    """)
    params = {"loc" : loc}
    results = session.execute(statement, params)
    route_ids = [row['id'] for row in results.mappings()]
    if not route_ids:
        return []
    return session.query(Route).options(joinedload(Route.vehicle)).filter(Route.id.in_(route_ids)).all()

def find_matching_shipments_by_single_location(session: Session, loc: str, is_pickup: bool = True):
    statement = text("""
        SELECT s.id FROM shipment s
        JOIN wilaya_coords loc_c ON :loc = loc_c.name
        JOIN wilaya_coords s_p ON s_p.name = REPLACE(CAST(s.pickup_location AS TEXT), '_', ' ')
        JOIN wilaya_coords s_d ON s_d.name = REPLACE(CAST(s.delivery_location AS TEXT), '_', ' ')
        JOIN "user" u ON s.user_id = u.id
        WHERE s.status = 'posted' AND u.is_available = True
            AND (
                ST_DWithin(loc_c.geom, s_p.geom::geography, 50000)
                OR
                ST_DWithin(loc_c.geom, s_d.geom::geography, 50000)
            );
    """)
    params = {"loc" : loc}
    results = session.execute(statement, params)
    shipment_ids = [row['id'] for row in results.mappings()]
    if not shipment_ids:
        return []
    return session.query(Shipment).filter(Shipment.id.in_(shipment_ids)).all()

def find_matching_shipments_by_locations(session: Session, dep_loc: str, arr_loc: str, rem_cap: float = 1000000):
    statement = text("""
        SELECT s.* FROM shipment s
        JOIN wilaya_coords r_o ON r_o.name = REPLACE(CAST(:dep_loc AS TEXT), '_', ' ')
        LEFT JOIN wilaya_coords r_a ON r_a.name = REPLACE(CAST(:arr_loc AS TEXT), '_', ' ')
        JOIN wilaya_coords s_p ON s_p.name = REPLACE(CAST(s.pickup_location AS TEXT), '_', ' ')
        JOIN wilaya_coords s_d ON s_d.name = REPLACE(CAST(s.delivery_location AS TEXT), '_', ' ')
        JOIN "user" u ON s.user_id = u.id
        WHERE s.status = 'posted' AND u.is_available = True AND :rem_cap >= s.size 
            AND (
                (:arr_loc IS NULL AND ST_DWithin(s_p.geom, r_o.geom::geography, 50000))
                OR
                (:arr_loc IS NOT NULL AND (
                    CASE 
                        WHEN ST_Distance(r_o.geom::geography, r_a.geom::geography) < 5000 
                            THEN ST_DWithin(s_p.geom, r_o.geom::geography, 50000)
                        ELSE (
                            ((ST_Distance(r_o.geom::geography, s_p.geom::geography) + 
                              ST_Distance(s_p.geom::geography, s_d.geom::geography) + 
                              ST_Distance(s_d.geom::geography, r_a.geom::geography)) 
                             / ST_Distance(r_o.geom::geography, r_a.geom::geography) <= 1.15)
                            OR
                            ((ST_Distance(r_a.geom::geography, s_p.geom::geography) + 
                              ST_Distance(s_p.geom::geography, s_d.geom::geography) + 
                              ST_Distance(s_d.geom::geography, r_o.geom::geography)) 
                             / ST_Distance(r_a.geom::geography, r_o.geom::geography) <= 1.15)
                        )
                    END
                ))
            );
    """)
    params = {"dep_loc" : dep_loc, "arr_loc" : arr_loc, "rem_cap" : rem_cap}
    results = session.execute(statement, params)
    shipment_ids = [row['id'] for row in results.mappings()]
    if not shipment_ids:
        return []
    return session.query(Shipment).filter(Shipment.id.in_(shipment_ids)).all()