"""Broker integrations for Portfolio Monitor."""

from .base import BaseBroker
from .registry import get_broker, list_brokers, register_broker

_DISCOVERED = False


def _ensure_registered() -> None:
    """Lazily import all broker modules so decorators fire."""
    global _DISCOVERED
    if _DISCOVERED:
        return
    _DISCOVERED = True
    from . import demo  # noqa: F401

    try:
        from . import longport  # noqa: F401
    except ImportError:
        pass
    try:
        from . import futu  # noqa: F401
    except ImportError:
        pass


__all__ = [
    "BaseBroker",
    "get_broker",
    "list_brokers",
    "register_broker",
    "_ensure_registered",
]
