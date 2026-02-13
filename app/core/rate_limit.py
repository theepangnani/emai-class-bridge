"""Rate limiting configuration using slowapi."""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For behind Cloud Run proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


def get_user_id_or_ip(request: Request) -> str:
    """Use authenticated user ID if available, otherwise fall back to IP."""
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    return get_client_ip(request)


# In-memory storage — resets on cold start, acceptable as defense-in-depth.
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=[],
    storage_uri="memory://",
)
