from fastapi import APIRouter, Query
from app.services.map_service import (
    search_poi, search_nearby, geocode,
    driving_route, transit_route, ACCOMMODATION_TYPES
)

router = APIRouter(prefix="/api/map", tags=["map"])

@router.get("/search")
async def map_search(
    keywords: str = Query(...),
    city: str = Query(""),
    location: str = Query(""),
    radius: int = Query(3000),
    types: str = Query("")
):
    return await search_poi(keywords=keywords, city=city, location=location, radius=radius, types=types)

@router.get("/nearby")
async def nearby_search(
    location: str = Query(...),
    types: str = Query("060000"),
    radius: int = Query(3000)
):
    return await search_nearby(location=location, types=types, radius=radius)

@router.get("/accommodation")
async def accommodation_search(
    location: str = Query(...),
    acc_type: str = Query("hotel"),
    radius: int = Query(3000)
):
    """搜索周边住宿：hotel/apartment/hostel"""
    poi_types = ACCOMMODATION_TYPES.get(acc_type, ACCOMMODATION_TYPES["hotel"])
    return await search_nearby(location=location, types=poi_types, radius=radius)

@router.get("/geocode")
async def geo_code(address: str = Query(...), city: str = Query("")):
    return await geocode(address=address, city=city)

@router.get("/route/driving")
async def route_driving(origin: str = Query(...), destination: str = Query(...)):
    return await driving_route(origin=origin, destination=destination)

@router.get("/route/transit")
async def route_transit(
    origin: str = Query(...),
    destination: str = Query(...),
    city: str = Query("")
):
    return await transit_route(origin=origin, destination=destination, city=city)
