"""Shared utility functions."""


def escape_like(value: str) -> str:
    """Escape LIKE wildcard characters (%, _, \\) so they match literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
