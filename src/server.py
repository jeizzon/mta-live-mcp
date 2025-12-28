#!/usr/bin/env python3
"""MTA Live Data MCP Server.

Provides real-time transit data for NYC Subway, Buses, LIRR, and Metro-North.
"""

import asyncio
import os

from fastmcp import FastMCP

from auth import extract_bearer_token, get_auth_token, validate_token
from mta_feeds import (
    get_bus_arrivals as fetch_bus_arrivals,
)
from mta_feeds import (
    get_bus_stops_nearby as fetch_bus_stops_nearby,
)
from mta_feeds import (
    get_rail_arrivals as fetch_rail_arrivals,
)
from mta_feeds import (
    get_service_alerts as fetch_service_alerts,
)
from mta_feeds import (
    get_subway_arrivals as fetch_subway_arrivals,
)
from mta_feeds import (
    get_subway_line_status as fetch_subway_line_status,
)
from station_data import station_data

mcp = FastMCP("MTA Live Data")


# ============================================================================
# Subway Tools
# ============================================================================


@mcp.tool(
    description="Get upcoming subway arrivals at a specific NYC Subway stop. Provide the GTFS stop ID (e.g., '635' for 14th St-Union Sq)."
)
async def get_subway_arrivals(stop_id: str) -> dict:
    """Get upcoming subway arrivals at a specific stop."""
    if not station_data.is_loaded:
        return {"error": "Station data not loaded. Server may still be starting up."}

    return await fetch_subway_arrivals(stop_id)


@mcp.tool(
    description="Find nearby NYC Subway stations and get their upcoming arrivals. Provide latitude, longitude, and optional radius in meters (default 500m)."
)
async def get_nearby_subway_arrivals(
    lat: float, lon: float, radius_meters: int = 500
) -> dict:
    """Find nearby subway stations and return arrivals for each."""
    if not station_data.is_loaded:
        return {"error": "Station data not loaded. Server may still be starting up."}

    nearby = station_data.subway.find_nearby(lat, lon, radius_meters)
    if not nearby:
        return {
            "latitude": lat,
            "longitude": lon,
            "radius_meters": radius_meters,
            "stations": [],
            "message": "No subway stations found within the specified radius.",
        }

    results = []
    for station, distance in nearby[:5]:  # Limit to 5 nearest stations
        arrivals = await fetch_subway_arrivals(station.stop_id)
        results.append(
            {
                "station": station.to_dict(),
                "distance_meters": round(distance, 1),
                "arrivals": arrivals.get("arrivals", []),
            }
        )

    return {
        "latitude": lat,
        "longitude": lon,
        "radius_meters": radius_meters,
        "stations": results,
    }


@mcp.tool(description="Get active service alerts for the NYC Subway system.")
async def get_subway_alerts() -> dict:
    """Get active service alerts for NYC Subway."""
    return await fetch_service_alerts("subway")


@mcp.tool(
    description="Get delay and status information for a specific NYC Subway line. Provide the line letter/number (e.g., 'A', 'L', '7')."
)
async def get_subway_line_status(line: str) -> dict:
    """Get delay/status information for a specific subway line."""
    return await fetch_subway_line_status(line)


@mcp.tool(
    description="Search for NYC Subway stations by name. Provide a partial or full station name (e.g., 'Times Square', '14th')."
)
async def search_subway_stations(query: str) -> dict:
    """Search for subway stations by name."""
    if not station_data.is_loaded:
        return {"error": "Station data not loaded. Server may still be starting up."}

    matches = station_data.subway.search(query)
    return {
        "query": query,
        "stations": [s.to_dict() for s in matches[:20]],  # Limit to 20 results
        "count": len(matches),
    }


@mcp.tool(
    description="Find NYC Subway stations near a location. Provide latitude, longitude, and optional radius in meters (default 500m)."
)
async def find_nearby_subway_stations(
    lat: float, lon: float, radius_meters: int = 500
) -> dict:
    """Find subway stations near a location."""
    if not station_data.is_loaded:
        return {"error": "Station data not loaded. Server may still be starting up."}

    nearby = station_data.subway.find_nearby(lat, lon, radius_meters)
    return {
        "latitude": lat,
        "longitude": lon,
        "radius_meters": radius_meters,
        "stations": [
            {"station": s.to_dict(), "distance_meters": round(d, 1)} for s, d in nearby
        ],
        "count": len(nearby),
    }


# ============================================================================
# Bus Tools
# ============================================================================


@mcp.tool(
    description="Get upcoming MTA bus arrivals at a specific bus stop. Provide the bus stop ID. Requires MTA_BUS_API_KEY environment variable."
)
async def get_bus_arrivals(stop_id: str) -> dict:
    """Get upcoming bus arrivals at a specific stop."""
    return await fetch_bus_arrivals(stop_id)


@mcp.tool(
    description="Find nearby MTA bus stops and get their upcoming arrivals. Provide latitude and longitude. Requires MTA_BUS_API_KEY environment variable."
)
async def get_nearby_bus_arrivals(lat: float, lon: float) -> dict:
    """Find nearby bus stops and return arrivals for each."""
    stops_result = await fetch_bus_stops_nearby(lat, lon)

    if "error" in stops_result and not stops_result.get("stops"):
        return stops_result

    results = []
    for stop in stops_result.get("stops", [])[:5]:  # Limit to 5 nearest stops
        arrivals = await fetch_bus_arrivals(stop["stop_id"])
        results.append(
            {
                "stop": stop,
                "arrivals": arrivals.get("arrivals", []),
            }
        )

    return {
        "latitude": lat,
        "longitude": lon,
        "stops": results,
    }


@mcp.tool(description="Get active service alerts for MTA buses.")
async def get_bus_alerts() -> dict:
    """Get active service alerts for MTA buses."""
    return await fetch_service_alerts("bus")


# ============================================================================
# LIRR (Long Island Rail Road) Tools
# ============================================================================


@mcp.tool(
    description="Get upcoming LIRR (Long Island Rail Road) arrivals at a specific station. Provide the GTFS stop ID."
)
async def get_lirr_arrivals(stop_id: str) -> dict:
    """Get upcoming LIRR arrivals at a specific station."""
    return await fetch_rail_arrivals(stop_id, "lirr")


@mcp.tool(
    description="Find nearby LIRR stations and get their upcoming arrivals. Provide latitude, longitude, and optional radius in meters (default 1000m)."
)
async def get_nearby_lirr_arrivals(
    lat: float, lon: float, radius_meters: int = 1000
) -> dict:
    """Find nearby LIRR stations and return arrivals for each."""
    if not station_data.is_loaded:
        return {"error": "Station data not loaded. Server may still be starting up."}

    nearby = station_data.lirr.find_nearby(lat, lon, radius_meters)
    if not nearby:
        return {
            "latitude": lat,
            "longitude": lon,
            "radius_meters": radius_meters,
            "stations": [],
            "message": "No LIRR stations found within the specified radius.",
        }

    results = []
    for station, distance in nearby[:5]:
        arrivals = await fetch_rail_arrivals(station.stop_id, "lirr")
        results.append(
            {
                "station": station.to_dict(),
                "distance_meters": round(distance, 1),
                "arrivals": arrivals.get("arrivals", []),
            }
        )

    return {
        "latitude": lat,
        "longitude": lon,
        "radius_meters": radius_meters,
        "stations": results,
    }


@mcp.tool(description="Get active service alerts for LIRR (Long Island Rail Road).")
async def get_lirr_alerts() -> dict:
    """Get active service alerts for LIRR."""
    return await fetch_service_alerts("lirr")


@mcp.tool(
    description="Search for LIRR stations by name. Provide a partial or full station name (e.g., 'Penn Station', 'Jamaica')."
)
async def search_lirr_stations(query: str) -> dict:
    """Search for LIRR stations by name."""
    if not station_data.is_loaded:
        return {"error": "Station data not loaded. Server may still be starting up."}

    matches = station_data.lirr.search(query)
    return {
        "query": query,
        "stations": [s.to_dict() for s in matches[:20]],
        "count": len(matches),
    }


@mcp.tool(
    description="Find LIRR stations near a location. Provide latitude, longitude, and optional radius in meters (default 1000m)."
)
async def find_nearby_lirr_stations(
    lat: float, lon: float, radius_meters: int = 1000
) -> dict:
    """Find LIRR stations near a location."""
    if not station_data.is_loaded:
        return {"error": "Station data not loaded. Server may still be starting up."}

    nearby = station_data.lirr.find_nearby(lat, lon, radius_meters)
    return {
        "latitude": lat,
        "longitude": lon,
        "radius_meters": radius_meters,
        "stations": [
            {"station": s.to_dict(), "distance_meters": round(d, 1)} for s, d in nearby
        ],
        "count": len(nearby),
    }


# ============================================================================
# Metro-North Tools
# ============================================================================


@mcp.tool(
    description="Get upcoming Metro-North Railroad arrivals at a specific station. Provide the GTFS stop ID."
)
async def get_metro_north_arrivals(stop_id: str) -> dict:
    """Get upcoming Metro-North arrivals at a specific station."""
    return await fetch_rail_arrivals(stop_id, "metro_north")


@mcp.tool(
    description="Find nearby Metro-North stations and get their upcoming arrivals. Provide latitude, longitude, and optional radius in meters (default 1000m)."
)
async def get_nearby_metro_north_arrivals(
    lat: float, lon: float, radius_meters: int = 1000
) -> dict:
    """Find nearby Metro-North stations and return arrivals for each."""
    if not station_data.is_loaded:
        return {"error": "Station data not loaded. Server may still be starting up."}

    nearby = station_data.metro_north.find_nearby(lat, lon, radius_meters)
    if not nearby:
        return {
            "latitude": lat,
            "longitude": lon,
            "radius_meters": radius_meters,
            "stations": [],
            "message": "No Metro-North stations found within the specified radius.",
        }

    results = []
    for station, distance in nearby[:5]:
        arrivals = await fetch_rail_arrivals(station.stop_id, "metro_north")
        results.append(
            {
                "station": station.to_dict(),
                "distance_meters": round(distance, 1),
                "arrivals": arrivals.get("arrivals", []),
            }
        )

    return {
        "latitude": lat,
        "longitude": lon,
        "radius_meters": radius_meters,
        "stations": results,
    }


@mcp.tool(description="Get active service alerts for Metro-North Railroad.")
async def get_metro_north_alerts() -> dict:
    """Get active service alerts for Metro-North."""
    return await fetch_service_alerts("metro_north")


@mcp.tool(
    description="Search for Metro-North stations by name. Provide a partial or full station name (e.g., 'Grand Central', 'White Plains')."
)
async def search_metro_north_stations(query: str) -> dict:
    """Search for Metro-North stations by name."""
    if not station_data.is_loaded:
        return {"error": "Station data not loaded. Server may still be starting up."}

    matches = station_data.metro_north.search(query)
    return {
        "query": query,
        "stations": [s.to_dict() for s in matches[:20]],
        "count": len(matches),
    }


@mcp.tool(
    description="Find Metro-North stations near a location. Provide latitude, longitude, and optional radius in meters (default 1000m)."
)
async def find_nearby_metro_north_stations(
    lat: float, lon: float, radius_meters: int = 1000
) -> dict:
    """Find Metro-North stations near a location."""
    if not station_data.is_loaded:
        return {"error": "Station data not loaded. Server may still be starting up."}

    nearby = station_data.metro_north.find_nearby(lat, lon, radius_meters)
    return {
        "latitude": lat,
        "longitude": lon,
        "radius_meters": radius_meters,
        "stations": [
            {"station": s.to_dict(), "distance_meters": round(d, 1)} for s, d in nearby
        ],
        "count": len(nearby),
    }


# ============================================================================
# Server Info Tool
# ============================================================================


@mcp.tool(
    description="Get information about the MTA Live Data MCP server, including loaded station counts and configuration status."
)
async def get_server_info() -> dict:
    """Get information about the MCP server."""
    return {
        "server_name": "MTA Live Data",
        "version": "1.0.0",
        "station_data_loaded": station_data.is_loaded,
        "subway_stations": len(station_data.subway.stations)
        if station_data.is_loaded
        else 0,
        "lirr_stations": len(station_data.lirr.stations)
        if station_data.is_loaded
        else 0,
        "metro_north_stations": len(station_data.metro_north.stations)
        if station_data.is_loaded
        else 0,
        "bus_api_configured": bool(os.environ.get("MTA_BUS_API_KEY")),
        "auth_configured": bool(get_auth_token()),
    }


# ============================================================================
# Custom HTTP Endpoints
# ============================================================================


async def load_station_data():
    """Load station data on startup."""
    print("Loading station data from MTA...")
    try:
        await station_data.load()
        print(f"Loaded {len(station_data.subway.stations)} subway stations")
        print(f"Loaded {len(station_data.lirr.stations)} LIRR stations")
        print(f"Loaded {len(station_data.metro_north.stations)} Metro-North stations")
    except Exception as e:
        print(f"Warning: Failed to load station data: {e}")
        print("Server will continue but station lookup features will be unavailable.")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"

    # Check for auth token
    if not get_auth_token():
        print("WARNING: MCP_AUTH_TOKEN not set. All requests will be rejected.")

    # Check for bus API key
    if not os.environ.get("MTA_BUS_API_KEY"):
        print("Note: MTA_BUS_API_KEY not set. Bus tools will not be available.")

    # Load station data before starting server
    asyncio.run(load_station_data())

    print(f"Starting MTA Live Data MCP server on {host}:{port}")

    mcp.run(
        transport="http",
        host=host,
        port=port,
        stateless_http=True,
    )
