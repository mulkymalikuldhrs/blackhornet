"""
Edge Case Handling — BH modules
Provides defensive wrappers, input validation, and graceful degradation
for all BH core components.
"""
from typing import Any, Dict, List, Optional, TypeVar, Callable
import functools
import logging
import asyncio
import time

logger = logging.getLogger(__name__)

T = TypeVar('T')


def safe_execute(default_return: T = None, log_level: str = "warning"):
    """Decorator that catches exceptions and returns default"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                getattr(logger, log_level, logger.warning)(
                    f"{func.__name__} failed: {e}", exc_info=True
                )
                return default_return

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                getattr(logger, log_level, logger.warning)(
                    f"{func.__name__} failed: {e}", exc_info=True
                )
                return default_return

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def validate_input(**validators):
    """Decorator that validates function arguments"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for param_name, validator_fn in validators.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    try:
                        validator_fn(value)
                    except (ValueError, TypeError) as e:
                        raise ValueError(f"Invalid {param_name}: {e}")
            return func(*args, **kwargs)

        return wrapper

    return decorator


def non_empty_string(value: Any):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("must be non-empty string")


def positive_number(value: Any):
    if not isinstance(value, (int, float)) or value <= 0:
        raise ValueError("must be positive number")


def non_negative_number(value: Any):
    if not isinstance(value, (int, float)) or value < 0:
        raise ValueError("must be non-negative number")


def valid_list(value: Any):
    if not isinstance(value, (list, tuple)):
        raise ValueError("must be a list")


class GracefulDegrader:
    """Provides graceful degradation strategies for module failures"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._fallbacks: Dict[str, Callable] = {}
        self._timeouts: Dict[str, float] = {}
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: Dict[str, float] = {}

    def register_fallback(self, operation: str, fallback_fn: Callable):
        self._fallbacks[operation] = fallback_fn

    def register_timeout(self, operation: str, timeout: float):
        self._timeouts[operation] = timeout

    async def execute_with_fallback(self, operation: str, 
                                      primary_fn: Callable,
                                      *args, **kwargs) -> Any:
        timeout = self._timeouts.get(operation, 30.0)
        try:
            result = await asyncio.wait_for(primary_fn(*args, **kwargs), timeout=timeout)
            self._cache[operation] = {"result": result, "timestamp": time.time()}
            return result
        except asyncio.TimeoutError:
            logger.warning(f"{operation} timed out after {timeout}s")
        except Exception as e:
            logger.warning(f"{operation} failed: {e}")

        # Try fallback
        if operation in self._fallbacks:
            try:
                logger.info(f"Using fallback for {operation}")
                return await self._fallbacks[operation](*args, **kwargs)
            except Exception as e:
                logger.error(f"Fallback for {operation} also failed: {e}")

        # Try cache
        if operation in self._cache:
            cached = self._cache[operation]
            age = time.time() - cached["timestamp"]
            if age < self._cache_ttl.get(operation, 60.0):
                logger.info(f"Using cached result for {operation} (age={age:.0f}s)")
                return cached["result"]

        return None


class NullHandler:
    """Null Object Pattern — safe no-op handler for optional features"""

    def __getattr__(self, name):
        return self._noop

    def _noop(self, *args, **kwargs):
        return None

    def __call__(self, *args, **kwargs):
        return None

    def __bool__(self):
        return False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass
