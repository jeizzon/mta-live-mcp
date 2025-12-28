"""Tests for MTA feed parsing."""

import os
import pytest
from unittest.mock import patch

from mta_feeds import (
    LINE_TO_FEED,
    SUBWAY_FEEDS,
    RAIL_FEEDS,
    ALERT_FEEDS,
    get_bus_api_key,
)


class TestFeedConfiguration:

    def test_all_subway_lines_mapped(self):
        expected_lines = ["A", "C", "E", "B", "D", "F", "M", "G", "J", "Z", "N", "Q", "R", "W", "L", "1", "2", "3", "4", "5", "6", "7", "S", "SIR"]
        for line in expected_lines:
            assert line in LINE_TO_FEED

    def test_subway_feeds_have_urls(self):
        expected_feeds = ["ACE", "BDFM", "G", "JZ", "NQRW", "L", "1234567S", "SIR"]
        for feed in expected_feeds:
            assert feed in SUBWAY_FEEDS
            assert SUBWAY_FEEDS[feed].startswith("https://")

    def test_rail_feeds_configured(self):
        assert "lirr" in RAIL_FEEDS
        assert "metro_north" in RAIL_FEEDS

    def test_alert_feeds_configured(self):
        assert "subway" in ALERT_FEEDS
        assert "bus" in ALERT_FEEDS
        assert "lirr" in ALERT_FEEDS
        assert "metro_north" in ALERT_FEEDS


class TestBusApiKey:

    def test_get_bus_api_key_when_set(self):
        with patch.dict(os.environ, {"MTA_BUS_API_KEY": "test-key-123"}):
            key = get_bus_api_key()
            assert key == "test-key-123"


class TestGtfsRtParsing:

    def test_line_to_feed_mapping(self):
        assert LINE_TO_FEED["A"] == "ACE"
        assert LINE_TO_FEED["1"] == "1234567S"
        assert LINE_TO_FEED["L"] == "L"
        assert LINE_TO_FEED["G"] == "G"


class TestAlertParsing:

    def test_alert_feed_urls_valid(self):
        for system, url in ALERT_FEEDS.items():
            assert url.startswith("https://api-endpoint.mta.info")
            assert "alerts" in url.lower()
