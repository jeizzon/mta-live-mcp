"""Authentication middleware for MCP server."""

import os
from functools import wraps
from typing import Any, Callable


def get_auth_token() -> str | None:
    """Get the configured auth token from environment."""
    return os.environ.get("MCP_AUTH_TOKEN")


def validate_token(token: str | None) -> bool:
    """Validate the provided token against the configured auth token."""
    expected_token = get_auth_token()
    if not expected_token:
        # No token configured - reject all requests for safety
        return False
    if not token:
        return False
    return token == expected_token


def extract_bearer_token(authorization: str | None) -> str | None:
    """Extract token from Authorization header (Bearer scheme)."""
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


def require_auth(func: Callable) -> Callable:
    """Decorator to require authentication for a function.

    Note: This is for use with custom HTTP endpoints, not MCP tools.
    MCP tool authentication is handled at the transport level.
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        # Get authorization from request context if available
        authorization = kwargs.get("authorization")
        token = extract_bearer_token(authorization)
        if not validate_token(token):
            raise PermissionError("Invalid or missing authentication token")
        return func(*args, **kwargs)

    return wrapper
