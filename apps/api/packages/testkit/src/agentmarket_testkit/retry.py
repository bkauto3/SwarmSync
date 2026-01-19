from __future__ import annotations

import asyncio
import functools
from collections.abc import Awaitable, Callable, Coroutine
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


def retry_with_exponential_backoff(
    *,
    attempts: int = 5,
    initial_delay: float = 0.25,
    max_delay: float = 3.0,
    factor: float = 2.0,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Coroutine[None, None, T]]]:
    """
    Decorator that retries an async function with exponential backoff.

    Useful for smoothing over startup races between the API container and the
    test suite when running locally.
    """

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Coroutine[None, None, T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            delay = initial_delay
            for attempt in range(1, attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception:  # noqa: BLE001
                    if attempt == attempts:
                        raise
                    await asyncio.sleep(delay)
                    delay = min(delay * factor, max_delay)
            raise RuntimeError("retry_with_exponential_backoff exhausted retries")

        return wrapper

    return decorator
