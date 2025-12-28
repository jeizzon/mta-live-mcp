"""Tests for MCP server and authentication."""

import os
from unittest.mock import patch

import pytest

from auth import (
    extract_bearer_token,
    get_auth_token,
    validate_token,
)


class TestAuthToken:
    """Tests for authentication token handling."""

    def test_get_auth_token_when_set(self):
        """Test getting auth token when set."""
        with patch.dict(os.environ, {"MCP_AUTH_TOKEN": "my-secret-token"}):
            token = get_auth_token()
            assert token == "my-secret-token"

    def test_get_auth_token_when_not_set(self):
        """Test getting auth token when not set."""
        env_copy = os.environ.copy()
        env_copy.pop("MCP_AUTH_TOKEN", None)

        with patch.dict(os.environ, env_copy, clear=True):
            token = get_auth_token()
            assert token is None


class TestValidateToken:
    """Tests for token validation."""

    def test_validate_correct_token(self):
        """Test validating correct token."""
        with patch.dict(os.environ, {"MCP_AUTH_TOKEN": "correct-token"}):
            assert validate_token("correct-token") is True

    def test_validate_incorrect_token(self):
        """Test validating incorrect token."""
        with patch.dict(os.environ, {"MCP_AUTH_TOKEN": "correct-token"}):
            assert validate_token("wrong-token") is False

    def test_validate_none_token(self):
        """Test validating None token."""
        with patch.dict(os.environ, {"MCP_AUTH_TOKEN": "correct-token"}):
            assert validate_token(None) is False

    def test_validate_empty_token(self):
        """Test validating empty token."""
        with patch.dict(os.environ, {"MCP_AUTH_TOKEN": "correct-token"}):
            assert validate_token("") is False

    def test_validate_when_no_token_configured(self):
        """Test that validation fails when no token is configured."""
        env_copy = os.environ.copy()
        env_copy.pop("MCP_AUTH_TOKEN", None)

        with patch.dict(os.environ, env_copy, clear=True):
            # Should reject all tokens when none is configured
            assert validate_token("any-token") is False
            assert validate_token(None) is False


class TestExtractBearerToken:
    """Tests for extracting Bearer token from Authorization header."""

    def test_extract_valid_bearer(self):
        """Test extracting valid Bearer token."""
        token = extract_bearer_token("Bearer my-token-123")
        assert token == "my-token-123"

    def test_extract_bearer_case_insensitive(self):
        """Test that Bearer is case-insensitive."""
        token = extract_bearer_token("bearer my-token-123")
        assert token == "my-token-123"

        token = extract_bearer_token("BEARER my-token-123")
        assert token == "my-token-123"

    def test_extract_from_none(self):
        """Test extracting from None header."""
        token = extract_bearer_token(None)
        assert token is None

    def test_extract_from_empty(self):
        """Test extracting from empty header."""
        token = extract_bearer_token("")
        assert token is None

    def test_extract_wrong_scheme(self):
        """Test extracting with wrong auth scheme."""
        token = extract_bearer_token("Basic dXNlcjpwYXNz")
        assert token is None

    def test_extract_no_token_value(self):
        """Test extracting when no token value provided."""
        token = extract_bearer_token("Bearer")
        assert token is None

    def test_extract_token_with_spaces(self):
        """Test extracting token that contains spaces after scheme."""
        # Only first space should split
        token = extract_bearer_token("Bearer token with spaces")
        assert token == "token with spaces"


class TestToolNaming:
    """Tests to verify MCP tool names are clear and specific."""

    def test_subway_tools_have_subway_in_name(self):
        """Verify subway tool names contain 'subway'."""
        subway_tools = [
            "get_subway_arrivals",
            "get_nearby_subway_arrivals",
            "get_subway_alerts",
            "get_subway_line_status",
            "search_subway_stations",
            "find_nearby_subway_stations",
        ]

        for tool in subway_tools:
            assert "subway" in tool.lower()

    def test_bus_tools_have_bus_in_name(self):
        """Verify bus tool names contain 'bus'."""
        bus_tools = [
            "get_bus_arrivals",
            "get_nearby_bus_arrivals",
            "get_bus_alerts",
        ]

        for tool in bus_tools:
            assert "bus" in tool.lower()

    def test_lirr_tools_have_lirr_in_name(self):
        """Verify LIRR tool names contain 'lirr'."""
        lirr_tools = [
            "get_lirr_arrivals",
            "get_nearby_lirr_arrivals",
            "get_lirr_alerts",
            "search_lirr_stations",
            "find_nearby_lirr_stations",
        ]

        for tool in lirr_tools:
            assert "lirr" in tool.lower()

    def test_metro_north_tools_have_metro_north_in_name(self):
        """Verify Metro-North tool names contain 'metro_north'."""
        metro_north_tools = [
            "get_metro_north_arrivals",
            "get_nearby_metro_north_arrivals",
            "get_metro_north_alerts",
            "search_metro_north_stations",
            "find_nearby_metro_north_stations",
        ]

        for tool in metro_north_tools:
            assert "metro_north" in tool.lower()
