"""Retry utility with exponential backoff for external API calls."""

import asyncio
import functools
import logging
import random
import time
from typing import Callable, Optional, Tuple, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Default retryable exception types
RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    on_retry: Optional[Callable] = None,
):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (total calls = max_attempts)
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
        retryable_exceptions: Tuple of exception types to retry on.
            Defaults to ConnectionError, TimeoutError, OSError.
            Also retries on exceptions with "429", "rate", or "quota" in the message.
        on_retry: Optional callback(attempt, exception, delay) called before each retry
    """
    if retryable_exceptions is None:
        retryable_exceptions = RETRYABLE_EXCEPTIONS

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        break
                    delay = _calculate_delay(attempt, base_delay, max_delay)
                    if on_retry:
                        on_retry(attempt, e, delay)
                    logger.warning(
                        f"Retry {attempt}/{max_attempts} for {func.__name__}: "
                        f"{e}. Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                except Exception as e:
                    # Check if it's a rate limit error by message
                    if _is_rate_limit_error(e) and attempt < max_attempts:
                        last_exception = e
                        delay = _calculate_delay(attempt, base_delay, max_delay)
                        if on_retry:
                            on_retry(attempt, e, delay)
                        logger.warning(
                            f"Rate limit retry {attempt}/{max_attempts} for "
                            f"{func.__name__}: {e}. Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                    else:
                        raise
            raise last_exception

        return wrapper

    return decorator


def async_retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    on_retry: Optional[Callable] = None,
):
    """
    Async decorator for retrying functions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (total calls = max_attempts)
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
        retryable_exceptions: Tuple of exception types to retry on.
            Defaults to ConnectionError, TimeoutError, OSError.
            Also retries on exceptions with "429", "rate", or "quota" in the message.
        on_retry: Optional callback(attempt, exception, delay) called before each retry
    """
    if retryable_exceptions is None:
        retryable_exceptions = RETRYABLE_EXCEPTIONS

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        break
                    delay = _calculate_delay(attempt, base_delay, max_delay)
                    if on_retry:
                        on_retry(attempt, e, delay)
                    logger.warning(
                        f"Retry {attempt}/{max_attempts} for {func.__name__}: "
                        f"{e}. Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                except Exception as e:
                    # Check if it's a rate limit error by message
                    if _is_rate_limit_error(e) and attempt < max_attempts:
                        last_exception = e
                        delay = _calculate_delay(attempt, base_delay, max_delay)
                        if on_retry:
                            on_retry(attempt, e, delay)
                        logger.warning(
                            f"Rate limit retry {attempt}/{max_attempts} for "
                            f"{func.__name__}: {e}. Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise
            raise last_exception

        return wrapper

    return decorator


def _calculate_delay(attempt: int, base_delay: float, max_delay: float) -> float:
    """Calculate delay with exponential backoff and jitter."""
    delay = base_delay * (2 ** (attempt - 1))
    delay = min(delay, max_delay)
    jitter = random.uniform(0, delay * 0.1)
    return delay + jitter


def _is_rate_limit_error(e: Exception) -> bool:
    """Check if an exception is a rate limit error."""
    error_msg = str(e).lower()
    return any(keyword in error_msg for keyword in ("429", "rate", "quota"))
