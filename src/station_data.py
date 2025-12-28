"""Station data loading and geo-lookup for MTA transit systems."""

import csv
import io
import math
import zipfile
from dataclasses import dataclass
from typing import Optional

import httpx

# MTA data source URLs
SUBWAY_STATIONS_URL = "http://web.mta.info/developers/data/nyct/subway/Stations.csv"
LIRR_GTFS_URL = "https://rrgtfsfeeds.s3.amazonaws.com/gtfslirr.zip"
METRO_NORTH_GTFS_URL = "https://rrgtfsfeeds.s3.amazonaws.com/gtfsmnr.zip"


@dataclass
class Station:
    """Represents a transit station."""

    stop_id: str
    name: str
    latitude: float
    longitude: float
    routes: list[str]  # Lines/routes serving this station
    system: str  # 'subway', 'lirr', or 'metro_north'

    def to_dict(self) -> dict:
        """Convert station to dictionary for JSON serialization."""
        return {
            "stop_id": self.stop_id,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "routes": self.routes,
            "system": self.system,
        }


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in meters using Haversine formula."""
    R = 6371000  # Earth's radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


class StationIndex:
    """Index for a single transit system's stations."""

    def __init__(self, system: str):
        self.system = system
        self.stations: dict[str, Station] = {}

    def add_station(self, station: Station) -> None:
        """Add a station to the index."""
        self.stations[station.stop_id] = station

    def get_by_id(self, stop_id: str) -> Optional[Station]:
        """Get a station by its stop ID."""
        return self.stations.get(stop_id)

    def find_nearby(
        self, lat: float, lon: float, radius_meters: int = 500
    ) -> list[tuple[Station, float]]:
        """Find stations within radius_meters of the given coordinates.

        Returns list of (station, distance_meters) tuples sorted by distance.
        """
        nearby = []
        for station in self.stations.values():
            distance = haversine_distance(lat, lon, station.latitude, station.longitude)
            if distance <= radius_meters:
                nearby.append((station, distance))

        # Sort by distance
        nearby.sort(key=lambda x: x[1])
        return nearby

    def search(self, query: str) -> list[Station]:
        """Search for stations by name (case-insensitive partial match)."""
        query_lower = query.lower()
        matches = []
        for station in self.stations.values():
            if query_lower in station.name.lower():
                matches.append(station)

        # Sort by name for consistent results
        matches.sort(key=lambda s: s.name)
        return matches

    def all_stations(self) -> list[Station]:
        """Get all stations in this index."""
        return list(self.stations.values())


class StationData:
    """Singleton holding all station data for all transit systems."""

    _instance: Optional["StationData"] = None

    def __new__(cls) -> "StationData":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.subway = StationIndex("subway")
        self.lirr = StationIndex("lirr")
        self.metro_north = StationIndex("metro_north")
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        """Check if station data has been loaded."""
        return self._loaded

    async def load(self) -> None:
        """Load all station data from MTA sources."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Load all systems concurrently
            await self._load_subway_stations(client)
            await self._load_rail_stations(client, "lirr", LIRR_GTFS_URL)
            await self._load_rail_stations(client, "metro_north", METRO_NORTH_GTFS_URL)

        self._loaded = True

    async def refresh(self) -> dict:
        """Reload all station data from MTA sources.

        Returns summary of loaded stations.
        """
        # Clear existing data
        self.subway = StationIndex("subway")
        self.lirr = StationIndex("lirr")
        self.metro_north = StationIndex("metro_north")
        self._loaded = False

        # Reload
        await self.load()

        return {
            "subway_stations": len(self.subway.stations),
            "lirr_stations": len(self.lirr.stations),
            "metro_north_stations": len(self.metro_north.stations),
        }

    async def _load_subway_stations(self, client: httpx.AsyncClient) -> None:
        """Load subway stations from MTA Stations.csv."""
        response = await client.get(SUBWAY_STATIONS_URL)
        response.raise_for_status()

        # Parse CSV
        content = response.text
        reader = csv.DictReader(io.StringIO(content))

        for row in reader:
            try:
                # Stations.csv has columns: Station ID, Complex ID, GTFS Stop ID, Division,
                # Line, Stop Name, Borough, Daytime Routes, Structure, GTFS Latitude, GTFS Longitude
                stop_id = row.get("GTFS Stop ID", "").strip()
                name = row.get("Stop Name", "").strip()
                lat_str = row.get("GTFS Latitude", "").strip()
                lon_str = row.get("GTFS Longitude", "").strip()
                routes_str = row.get("Daytime Routes", "").strip()

                if not stop_id or not name or not lat_str or not lon_str:
                    continue

                latitude = float(lat_str)
                longitude = float(lon_str)
                routes = [r.strip() for r in routes_str.split(" ") if r.strip()]

                station = Station(
                    stop_id=stop_id,
                    name=name,
                    latitude=latitude,
                    longitude=longitude,
                    routes=routes,
                    system="subway",
                )
                self.subway.add_station(station)
            except (ValueError, KeyError):
                # Skip malformed rows
                continue

    async def _load_rail_stations(
        self, client: httpx.AsyncClient, system: str, url: str
    ) -> None:
        """Load rail stations from GTFS ZIP file."""
        response = await client.get(url)
        response.raise_for_status()

        # Extract stops.txt from ZIP
        zip_bytes = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_bytes, "r") as zf:
            with zf.open("stops.txt") as stops_file:
                content = stops_file.read().decode("utf-8")

        # Parse stops.txt (GTFS format)
        reader = csv.DictReader(io.StringIO(content))

        index = self.lirr if system == "lirr" else self.metro_north

        for row in reader:
            try:
                stop_id = row.get("stop_id", "").strip()
                name = row.get("stop_name", "").strip()
                lat_str = row.get("stop_lat", "").strip()
                lon_str = row.get("stop_lon", "").strip()

                if not stop_id or not name or not lat_str or not lon_str:
                    continue

                latitude = float(lat_str)
                longitude = float(lon_str)

                # GTFS stops.txt doesn't include route info directly
                # We'd need to cross-reference with routes.txt and stop_times.txt
                # For now, leave routes empty - they'll be populated from real-time data
                station = Station(
                    stop_id=stop_id,
                    name=name,
                    latitude=latitude,
                    longitude=longitude,
                    routes=[],
                    system=system,
                )
                index.add_station(station)
            except (ValueError, KeyError):
                # Skip malformed rows
                continue

    def get_index(self, system: str) -> Optional[StationIndex]:
        """Get the station index for a given system."""
        if system == "subway":
            return self.subway
        elif system == "lirr":
            return self.lirr
        elif system == "metro_north":
            return self.metro_north
        return None


# Global instance
station_data = StationData()
