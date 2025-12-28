"""Pytest fixtures for MTA MCP server tests."""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# Sample station CSV data (subway)
SAMPLE_SUBWAY_CSV = """Station ID,Complex ID,GTFS Stop ID,Division,Line,Stop Name,Borough,Daytime Routes,Structure,GTFS Latitude,GTFS Longitude
1,1,R01,BMT,Astoria,Astoria - Ditmars Blvd,Q,N W,Elevated,40.775036,-73.912034
2,2,R03,BMT,Astoria,Astoria Blvd,Q,N W,Elevated,40.770258,-73.917843
3,3,R04,BMT,Astoria,30 Av,Q,N W,Elevated,40.766779,-73.921479
4,4,R05,BMT,Astoria,Broadway,Q,N W,Elevated,40.76182,-73.925508
5,5,635,IRT,Lexington,14 St - Union Sq,M,4 5 6 L N Q R W,Subway,40.734673,-73.989951
"""

# Sample GTFS stops.txt data (LIRR/Metro-North format)
SAMPLE_GTFS_STOPS = """stop_id,stop_name,stop_lat,stop_lon
PENN,Penn Station,40.750568,-73.993519
JAM,Jamaica,40.700486,-73.807969
ATL,Atlantic Terminal,40.683666,-73.975528
GCT,Grand Central Terminal,40.752998,-73.977056
"""

# Sample GTFS-RT protobuf response (minimal mock)
SAMPLE_TRIP_UPDATE = {
    "trip": {
        "trip_id": "123456_A..N",
        "route_id": "A",
        "start_date": "20250101",
    },
    "stop_time_update": [
        {
            "stop_id": "A15N",
            "arrival": {"time": 1735689600},  # Sample timestamp
        },
    ],
}


@pytest.fixture
def sample_subway_csv():
    """Return sample subway stations CSV data."""
    return SAMPLE_SUBWAY_CSV


@pytest.fixture
def sample_gtfs_stops():
    """Return sample GTFS stops.txt data."""
    return SAMPLE_GTFS_STOPS


@pytest.fixture
def sample_trip_update():
    """Return sample GTFS-RT trip update data."""
    return SAMPLE_TRIP_UPDATE


@pytest.fixture
def auth_token():
    """Return a test auth token."""
    return "test-token-12345"


@pytest.fixture
def auth_headers(auth_token):
    """Return authorization headers with test token."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(autouse=True)
def set_test_env(auth_token):
    """Set up test environment variables."""
    original_token = os.environ.get("MCP_AUTH_TOKEN")
    original_bus_key = os.environ.get("MTA_BUS_API_KEY")

    os.environ["MCP_AUTH_TOKEN"] = auth_token
    os.environ["MTA_BUS_API_KEY"] = "test-bus-key"

    yield

    # Restore original values
    if original_token:
        os.environ["MCP_AUTH_TOKEN"] = original_token
    else:
        os.environ.pop("MCP_AUTH_TOKEN", None)

    if original_bus_key:
        os.environ["MTA_BUS_API_KEY"] = original_bus_key
    else:
        os.environ.pop("MTA_BUS_API_KEY", None)


@pytest.fixture
def mock_subway_response(httpx_mock, sample_subway_csv):
    """Mock the subway stations CSV endpoint."""
    httpx_mock.add_response(
        url="http://web.mta.info/developers/data/nyct/subway/Stations.csv",
        text=sample_subway_csv,
    )
    return httpx_mock


# Coordinates for testing
@pytest.fixture
def union_square_coords():
    """Return coordinates for 14th St - Union Square."""
    return {"lat": 40.734673, "lon": -73.989951}


@pytest.fixture
def times_square_coords():
    """Return coordinates for Times Square."""
    return {"lat": 40.758896, "lon": -73.985130}


@pytest.fixture
def far_away_coords():
    """Return coordinates far from any NYC transit."""
    return {"lat": 40.0, "lon": -74.5}
