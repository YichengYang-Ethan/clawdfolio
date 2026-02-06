"""Broker registry for dynamic broker discovery."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.config import BrokerConfig
    from .base import BaseBroker

# Global broker registry
_BROKER_REGISTRY: dict[str, type[BaseBroker]] = {}


def register_broker(name: str) -> Callable[[type[BaseBroker]], type[BaseBroker]]:
    """Decorator to register a broker implementation.

    Args:
        name: Unique identifier for the broker

    Returns:
        Decorator function

    Example:
        >>> @register_broker("my_broker")
        >>> class MyBroker(BaseBroker):
        ...     pass
    """

    def decorator(cls: type[BaseBroker]) -> type[BaseBroker]:
        if name in _BROKER_REGISTRY:
            raise ValueError(f"Broker '{name}' is already registered")
        cls.name = name
        _BROKER_REGISTRY[name] = cls
        return cls

    return decorator


def get_broker(
    name: str, config: BrokerConfig | None = None
) -> BaseBroker:
    """Get a broker instance by name.

    Args:
        name: Registered broker name
        config: Optional broker configuration

    Returns:
        Broker instance

    Raises:
        KeyError: If broker name is not registered
    """
    if name not in _BROKER_REGISTRY:
        available = ", ".join(_BROKER_REGISTRY.keys()) or "none"
        raise KeyError(f"Unknown broker '{name}'. Available brokers: {available}")

    broker_class = _BROKER_REGISTRY[name]
    return broker_class(config)


def list_brokers() -> list[str]:
    """List all registered broker names.

    Returns:
        List of registered broker names
    """
    return list(_BROKER_REGISTRY.keys())


def get_broker_class(name: str) -> type[BaseBroker]:
    """Get a broker class by name.

    Args:
        name: Registered broker name

    Returns:
        Broker class

    Raises:
        KeyError: If broker name is not registered
    """
    if name not in _BROKER_REGISTRY:
        raise KeyError(f"Unknown broker '{name}'")
    return _BROKER_REGISTRY[name]


def unregister_broker(name: str) -> None:
    """Unregister a broker (mainly for testing).

    Args:
        name: Broker name to unregister
    """
    _BROKER_REGISTRY.pop(name, None)


def clear_registry() -> None:
    """Clear all registered brokers (mainly for testing)."""
    _BROKER_REGISTRY.clear()
