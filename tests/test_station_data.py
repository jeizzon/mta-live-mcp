"""Tests for station data loading and geo-lookup."""

import pytest

from station_data import (
    Station,
    StationIndex,
    haversine_distance,
)


class TestHaversineDistance:
    """Tests for haversine distance calculation."""

    def test_same_point(self):
        """Distance between same point should be 0."""
        distance = haversine_distance(40.7128, -74.0060, 40.7128, -74.0060)
        assert distance == 0.0

    def test_known_distance(self):
        """Test distance between two known points."""
        # Union Square to Times Square is approximately 2.7 km
        union_sq = (40.734673, -73.989951)
        times_sq = (40.758896, -73.985130)

        distance = haversine_distance(*union_sq, *times_sq)

        # Should be roughly 2.7 km (2700 meters), allow some tolerance
        assert 2500 < distance < 3000

    def test_short_distance(self):
        """Test a very short distance (same block)."""
        lat1, lon1 = 40.734673, -73.989951
        lat2, lon2 = 40.734700, -73.989900  # ~10 meters away

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        assert 0 < distance < 50  # Should be less than 50 meters


class TestStation:
    """Tests for Station dataclass."""

    def test_to_dict(self):
        """Test station serialization to dict."""
        station = Station(
            stop_id="635",
            name="14 St - Union Sq",
            latitude=40.734673,
            longitude=-73.989951,
            routes=["4", "5", "6", "L", "N", "Q", "R", "W"],
            system="subway",
        )

        result = station.to_dict()

        assert result["stop_id"] == "635"
        assert result["name"] == "14 St - Union Sq"
        assert result["latitude"] == 40.734673
        assert result["longitude"] == -73.989951
        assert "4" in result["routes"]
        assert result["system"] == "subway"


class TestStationIndex:
    """Tests for StationIndex class."""

    @pytest.fixture
    def subway_index(self):
        """Create a subway index with sample stations."""
        index = StationIndex("subway")

        # Add some sample stations
        stations = [
            Station(
                "635",
                "14 St - Union Sq",
                40.734673,
                -73.989951,
                ["4", "5", "6", "L"],
                "subway",
            ),
            Station(
                "R01",
                "Astoria - Ditmars Blvd",
                40.775036,
                -73.912034,
                ["N", "W"],
                "subway",
            ),
            Station("R03", "Astoria Blvd", 40.770258, -73.917843, ["N", "W"], "subway"),
            Station(
                "127",
                "Times Sq - 42 St",
                40.755983,
                -73.986229,
                ["1", "2", "3", "7", "N", "Q", "R", "W", "S"],
                "subway",
            ),
            Station(
                "A15", "125 St", 40.811109, -73.958372, ["A", "B", "C", "D"], "subway"
            ),
        ]

        for station in stations:
            index.add_station(station)

        return index

    def test_get_by_id_exists(self, subway_index):
        """Test getting a station by ID that exists."""
        station = subway_index.get_by_id("635")

        assert station is not None
        assert station.name == "14 St - Union Sq"

    def test_get_by_id_not_exists(self, subway_index):
        """Test getting a station by ID that doesn't exist."""
        station = subway_index.get_by_id("INVALID")

        assert station is None

    def test_find_nearby(self, subway_index):
        """Test finding nearby stations."""
        # Search near Union Square
        nearby = subway_index.find_nearby(40.734673, -73.989951, radius_meters=500)

        assert len(nearby) >= 1
        # First result should be Union Square itself (distance ~0)
        station, distance = nearby[0]
        assert station.stop_id == "635"
        assert distance < 10  # Should be very close

    def test_find_nearby_larger_radius(self, subway_index):
        """Test finding stations with larger radius."""
        # Search near Times Square with 3km radius
        nearby = subway_index.find_nearby(40.755983, -73.986229, radius_meters=3000)

        # Should find Times Square and Union Square
        stop_ids = [s.stop_id for s, _ in nearby]
        assert "127" in stop_ids  # Times Square
        assert "635" in stop_ids  # Union Square

    def test_find_nearby_no_results(self, subway_index):
        """Test finding nearby with no stations in range."""
        # Search somewhere far away
        nearby = subway_index.find_nearby(40.0, -74.5, radius_meters=100)

        assert len(nearby) == 0

    def test_find_nearby_sorted_by_distance(self, subway_index):
        """Test that nearby results are sorted by distance."""
        nearby = subway_index.find_nearby(40.755983, -73.986229, radius_meters=10000)

        if len(nearby) > 1:
            distances = [d for _, d in nearby]
            assert distances == sorted(distances)

    def test_search_partial_match(self, subway_index):
        """Test searching with partial name match."""
        matches = subway_index.search("Union")

        assert len(matches) == 1
        assert matches[0].stop_id == "635"

    def test_search_case_insensitive(self, subway_index):
        """Test that search is case-insensitive."""
        matches = subway_index.search("TIMES")

        assert len(matches) == 1
        assert matches[0].stop_id == "127"

    def test_search_multiple_results(self, subway_index):
        """Test search returning multiple results."""
        matches = subway_index.search("Astoria")

        assert len(matches) == 2

    def test_search_no_results(self, subway_index):
        """Test search with no matches."""
        matches = subway_index.search("Brooklyn Bridge")

        assert len(matches) == 0

    def test_all_stations(self, subway_index):
        """Test getting all stations."""
        all_stations = subway_index.all_stations()

        assert len(all_stations) == 5
