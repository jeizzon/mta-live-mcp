"""MTA real-time feed parsing for GTFS-RT and SIRI APIs."""

import os
from datetime import datetime, timezone
from typing import Optional

import httpx
from google.transit import gtfs_realtime_pb2

# GTFS-RT Feed URLs
SUBWAY_FEEDS = {
    "ACE": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace",
    "BDFM": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm",
    "G": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g",
    "JZ": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz",
    "NQRW": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw",
    "L": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l",
    "1234567S": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
    "SIR": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si",
}

# Map individual lines to their feed
LINE_TO_FEED = {
    "A": "ACE",
    "C": "ACE",
    "E": "ACE",
    "B": "BDFM",
    "D": "BDFM",
    "F": "BDFM",
    "M": "BDFM",
    "G": "G",
    "J": "JZ",
    "Z": "JZ",
    "N": "NQRW",
    "Q": "NQRW",
    "R": "NQRW",
    "W": "NQRW",
    "L": "L",
    "1": "1234567S",
    "2": "1234567S",
    "3": "1234567S",
    "4": "1234567S",
    "5": "1234567S",
    "6": "1234567S",
    "7": "1234567S",
    "S": "1234567S",
    "SIR": "SIR",
}

RAIL_FEEDS = {
    "lirr": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/lirr%2Fgtfs-lirr",
    "metro_north": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/mnr%2Fgtfs-mnr",
}

ALERT_FEEDS = {
    "subway": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fsubway-alerts",
    "bus": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fbus-alerts",
    "lirr": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Flirr-alerts",
    "metro_north": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fmnr-alerts",
}

# Bus API URLs (SIRI)
BUS_STOPS_FOR_LOCATION_URL = (
    "https://bustime.mta.info/api/where/stops-for-location.json"
)
BUS_STOP_MONITORING_URL = "https://bustime.mta.info/api/siri/stop-monitoring.json"


def get_bus_api_key() -> Optional[str]:
    """Get the MTA Bus API key from environment."""
    return os.environ.get("MTA_BUS_API_KEY")


async def fetch_gtfs_rt_feed(url: str) -> gtfs_realtime_pb2.FeedMessage:
    """Fetch and parse a GTFS-RT feed."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        return feed


def parse_trip_update(
    entity: gtfs_realtime_pb2.FeedEntity, stop_id: str
) -> Optional[dict]:
    """Parse a trip update entity for arrivals at a specific stop."""
    if not entity.HasField("trip_update"):
        return None

    trip_update = entity.trip_update
    trip = trip_update.trip

    for stop_time_update in trip_update.stop_time_update:
        # Check if this stop matches (stop_id can have N/S suffix for direction)
        current_stop_id = stop_time_update.stop_id
        if not (
            current_stop_id == stop_id
            or current_stop_id.startswith(stop_id)
            or stop_id.startswith(current_stop_id.rstrip("NS"))
        ):
            continue

        arrival_time = None
        if stop_time_update.HasField("arrival"):
            arrival_time = stop_time_update.arrival.time
        elif stop_time_update.HasField("departure"):
            arrival_time = stop_time_update.departure.time

        if arrival_time:
            arrival_dt = datetime.fromtimestamp(arrival_time, tz=timezone.utc)
            now = datetime.now(tz=timezone.utc)
            minutes_away = (arrival_dt - now).total_seconds() / 60

            return {
                "route_id": trip.route_id,
                "trip_id": trip.trip_id,
                "arrival_time": arrival_dt.isoformat(),
                "minutes_away": round(minutes_away, 1),
                "stop_id": current_stop_id,
            }

    return None


async def get_subway_arrivals(stop_id: str) -> dict:
    """Get subway arrivals for a specific stop.

    Returns arrivals from all subway feeds that serve this stop.
    """
    arrivals = []
    errors = []

    # Fetch all subway feeds (we don't know which lines serve this stop)
    for feed_name, url in SUBWAY_FEEDS.items():
        try:
            feed = await fetch_gtfs_rt_feed(url)

            for entity in feed.entity:
                arrival = parse_trip_update(entity, stop_id)
                if arrival:
                    arrivals.append(arrival)
        except Exception as e:
            errors.append(f"{feed_name}: {str(e)}")

    # Sort by arrival time
    arrivals.sort(key=lambda x: x["minutes_away"])

    # Limit to next 10 arrivals
    arrivals = arrivals[:10]

    return {
        "stop_id": stop_id,
        "arrivals": arrivals,
        "errors": errors if errors else None,
    }


async def get_subway_line_arrivals(line: str, stop_id: str) -> dict:
    """Get arrivals for a specific subway line at a stop."""
    feed_name = LINE_TO_FEED.get(line.upper())
    if not feed_name:
        return {"error": f"Unknown subway line: {line}"}

    url = SUBWAY_FEEDS[feed_name]
    arrivals = []

    try:
        feed = await fetch_gtfs_rt_feed(url)

        for entity in feed.entity:
            arrival = parse_trip_update(entity, stop_id)
            if arrival and arrival["route_id"].upper() == line.upper():
                arrivals.append(arrival)

        arrivals.sort(key=lambda x: x["minutes_away"])
        arrivals = arrivals[:10]

        return {
            "line": line,
            "stop_id": stop_id,
            "arrivals": arrivals,
        }
    except Exception as e:
        return {"error": str(e)}


async def get_rail_arrivals(stop_id: str, system: str) -> dict:
    """Get arrivals for LIRR or Metro-North."""
    if system not in RAIL_FEEDS:
        return {"error": f"Unknown rail system: {system}. Use 'lirr' or 'metro_north'."}

    url = RAIL_FEEDS[system]
    arrivals = []

    try:
        feed = await fetch_gtfs_rt_feed(url)

        for entity in feed.entity:
            arrival = parse_trip_update(entity, stop_id)
            if arrival:
                arrivals.append(arrival)

        arrivals.sort(key=lambda x: x["minutes_away"])
        arrivals = arrivals[:10]

        return {
            "system": system,
            "stop_id": stop_id,
            "arrivals": arrivals,
        }
    except Exception as e:
        return {"error": str(e)}


async def get_service_alerts(system: str) -> dict:
    """Get service alerts for a transit system."""
    if system not in ALERT_FEEDS:
        return {
            "error": f"Unknown system: {system}. Use 'subway', 'bus', 'lirr', or 'metro_north'."
        }

    url = ALERT_FEEDS[system]
    alerts = []

    try:
        feed = await fetch_gtfs_rt_feed(url)

        for entity in feed.entity:
            if not entity.HasField("alert"):
                continue

            alert = entity.alert

            # Get header text
            header = ""
            if alert.header_text.translation:
                header = alert.header_text.translation[0].text

            # Get description text
            description = ""
            if alert.description_text.translation:
                description = alert.description_text.translation[0].text

            # Get affected routes/stops
            affected_routes = []
            affected_stops = []
            for informed in alert.informed_entity:
                if informed.route_id:
                    affected_routes.append(informed.route_id)
                if informed.stop_id:
                    affected_stops.append(informed.stop_id)

            # Get active period
            active_periods = []
            for period in alert.active_period:
                active_periods.append(
                    {
                        "start": datetime.fromtimestamp(
                            period.start, tz=timezone.utc
                        ).isoformat()
                        if period.start
                        else None,
                        "end": datetime.fromtimestamp(
                            period.end, tz=timezone.utc
                        ).isoformat()
                        if period.end
                        else None,
                    }
                )

            alerts.append(
                {
                    "id": entity.id,
                    "header": header,
                    "description": description,
                    "affected_routes": list(set(affected_routes)),
                    "affected_stops": list(set(affected_stops)),
                    "active_periods": active_periods,
                }
            )

        return {
            "system": system,
            "alerts": alerts,
            "count": len(alerts),
        }
    except Exception as e:
        return {"error": str(e)}


async def get_subway_line_status(line: str) -> dict:
    """Get delay/status information for a specific subway line."""
    # Get alerts that affect this line
    alerts_result = await get_service_alerts("subway")

    if "error" in alerts_result:
        return alerts_result

    line_upper = line.upper()
    line_alerts = []

    for alert in alerts_result.get("alerts", []):
        if line_upper in alert.get("affected_routes", []):
            line_alerts.append(alert)

    # Determine overall status
    if not line_alerts:
        status = "Good Service"
    else:
        # Check for delay keywords in headers/descriptions
        has_delays = any(
            "delay" in (a.get("header", "") + a.get("description", "")).lower()
            for a in line_alerts
        )
        has_suspension = any(
            "suspend" in (a.get("header", "") + a.get("description", "")).lower()
            for a in line_alerts
        )

        if has_suspension:
            status = "Service Suspended"
        elif has_delays:
            status = "Delays"
        else:
            status = "Service Changes"

    return {
        "line": line_upper,
        "status": status,
        "alerts": line_alerts,
        "alert_count": len(line_alerts),
    }


async def get_bus_stops_nearby(
    lat: float, lon: float, lat_span: float = 0.005, lon_span: float = 0.005
) -> dict:
    """Get bus stops near a location using the MTA Bus Time API."""
    api_key = get_bus_api_key()
    if not api_key:
        return {
            "error": "MTA Bus API key not configured. Set MTA_BUS_API_KEY environment variable.",
            "stops": [],
        }

    params = {
        "key": api_key,
        "lat": lat,
        "lon": lon,
        "latSpan": lat_span,
        "lonSpan": lon_span,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(BUS_STOPS_FOR_LOCATION_URL, params=params)
            response.raise_for_status()
            data = response.json()

        stops = []
        for stop in data.get("data", {}).get("stops", []):
            stops.append(
                {
                    "stop_id": stop.get("code") or stop.get("id"),
                    "name": stop.get("name"),
                    "latitude": stop.get("lat"),
                    "longitude": stop.get("lon"),
                    "routes": [
                        r.get("shortName") or r.get("id")
                        for r in stop.get("routes", [])
                    ],
                }
            )

        return {
            "latitude": lat,
            "longitude": lon,
            "stops": stops,
            "count": len(stops),
        }
    except Exception as e:
        return {"error": str(e), "stops": []}


async def get_bus_arrivals(stop_id: str) -> dict:
    """Get bus arrivals at a specific stop using the SIRI API."""
    api_key = get_bus_api_key()
    if not api_key:
        return {
            "error": "MTA Bus API key not configured. Set MTA_BUS_API_KEY environment variable.",
            "arrivals": [],
        }

    params = {
        "key": api_key,
        "MonitoringRef": stop_id,
        "version": "2",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(BUS_STOP_MONITORING_URL, params=params)
            response.raise_for_status()
            data = response.json()

        arrivals = []
        delivery = data.get("Siri", {}).get("ServiceDelivery", {})
        stop_monitoring = delivery.get("StopMonitoringDelivery", [])

        for sm in stop_monitoring:
            for visit in sm.get("MonitoredStopVisit", []):
                journey = visit.get("MonitoredVehicleJourney", {})
                call = journey.get("MonitoredCall", {})

                # Get expected arrival time
                expected_arrival = call.get("ExpectedArrivalTime")
                if expected_arrival:
                    try:
                        arrival_dt = datetime.fromisoformat(
                            expected_arrival.replace("Z", "+00:00")
                        )
                        now = datetime.now(tz=timezone.utc)
                        minutes_away = (arrival_dt - now).total_seconds() / 60
                    except ValueError:
                        minutes_away = None
                else:
                    minutes_away = None

                arrivals.append(
                    {
                        "route_id": journey.get("PublishedLineName")
                        or journey.get("LineRef"),
                        "destination": journey.get("DestinationName"),
                        "arrival_time": expected_arrival,
                        "minutes_away": round(minutes_away, 1)
                        if minutes_away
                        else None,
                        "stop_id": stop_id,
                        "distance_from_stop": call.get("DistanceFromStop"),
                        "stops_away": call.get("NumberOfStopsAway"),
                    }
                )

        # Sort by minutes away
        arrivals.sort(
            key=lambda x: x["minutes_away"] if x["minutes_away"] is not None else 999
        )

        return {
            "stop_id": stop_id,
            "arrivals": arrivals[:10],
        }
    except Exception as e:
        return {"error": str(e), "arrivals": []}
