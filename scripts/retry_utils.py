"""Retry utilities for network operations."""

from __future__ import annotations

import logging
import os
from functools import wraps
from typing import Any, Callable

from tenacity import (
    RetryError,
    Retrying,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)

logger = logging.getLogger(__name__)

# Default retry configuration
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_MIN_WAIT = 2
DEFAULT_MAX_WAIT = 10

# Exceptions that should trigger a retry
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def get_retry_config() -> dict[str, Any]:
    """Get retry configuration from environment variables."""
    return {
        "max_attempts": int(os.getenv("RETRY_MAX_ATTEMPTS", DEFAULT_MAX_ATTEMPTS)),
        "min_wait": int(os.getenv("RETRY_MIN_WAIT", DEFAULT_MIN_WAIT)),
        "max_wait": int(os.getenv("RETRY_MAX_WAIT", DEFAULT_MAX_WAIT)),
    }


def should_retry(exception: Exception) -> bool:
    """Determine if an exception should trigger a retry.
    
    Args:
        exception: The exception that was raised
        
    Returns:
        True if the operation should be retried, False otherwise
    """
    # Some callers raise exceptions with .response / .status_code (e.g. requests.HTTPError). Decide from
    # status only: retry 429 and 5xx, not other HTTP failures—even if the class is nested under OSError.
    response = getattr(exception, "response", None)
    if response is not None:
        status_code = getattr(response, "status_code", None)
        if status_code is not None:
            if status_code in (429, 500, 502, 503, 504):
                return True
            return False

    if isinstance(exception, RETRYABLE_EXCEPTIONS):
        return True

    return False


def with_retry(
    func: Callable[..., Any] | None = None,
    *,
    max_attempts: int | None = None,
    min_wait: int | None = None,
    max_wait: int | None = None,
) -> Any:
    """Decorator to add retry logic to a function.
    
    Can be used as:
        @with_retry
        def my_func(): ...
        
        @with_retry(max_attempts=5)
        def my_func(): ...
    
    Args:
        func: The function to wrap
        max_attempts: Maximum number of retry attempts (default from env)
        min_wait: Minimum wait time between retries in seconds (default from env)
        max_wait: Maximum wait time between retries in seconds (default from env)
        
    Returns:
        Wrapped function with retry logic
    """
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            config = get_retry_config()
            attempts = max_attempts or config["max_attempts"]
            min_w = min_wait or config["min_wait"]
            max_w = max_wait or config["max_wait"]
            
            retryer = Retrying(
                stop=stop_after_attempt(attempts),
                wait=wait_exponential(multiplier=1, min=min_w, max=max_w),
                retry=retry_if_exception(should_retry),
                reraise=True,
                before_sleep=lambda retry_state: logger.warning(
                    f"{fn.__name__} failed (attempt {retry_state.attempt_number}/{attempts}), retrying..."
                ),
            )
            
            try:
                result = retryer(fn, *args, **kwargs)
                if retryer.statistics.get("attempt_number", 1) > 1:
                    logger.info(f"{fn.__name__} succeeded after retry")
                return result
            except Exception as e:
                logger.error(f"{fn.__name__} failed after all retries: {e}")
                raise
        
        return wrapper
    
    if func is not None:
        return decorator(func)
    return decorator
