from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 0.5
    max_delay: float = 8.0
    backoff_factor: float = 2.0
    # Excepciones que NO deben reintentarse (fallos logicos).
    non_retryable: tuple = (ValueError, KeyError)


def with_retry(func: Callable[[], Any], policy: Optional[RetryPolicy] = None) -> Any:
    """Ejecuta `func` con reintentos de backoff exponencial (sync)."""
    policy = policy or RetryPolicy()
    delay = policy.base_delay
    last_exc: Optional[BaseException] = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return func()
        except policy.non_retryable:
            raise
        except Exception as exc:  # reintentable
            last_exc = exc
            if attempt >= policy.max_attempts:
                break
            time.sleep(min(delay, policy.max_delay))
            delay *= policy.backoff_factor
    assert last_exc is not None
    raise last_exc


async def with_retry_async(func: Callable[[], Any], policy: Optional[RetryPolicy] = None) -> Any:
    """Variante async de with_retry usando asyncio.sleep."""
    policy = policy or RetryPolicy()
    delay = policy.base_delay
    last_exc: Optional[BaseException] = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return await asyncio.to_thread(func)
        except policy.non_retryable:
            raise
        except Exception as exc:
            last_exc = exc
            if attempt >= policy.max_attempts:
                break
            await asyncio.sleep(min(delay, policy.max_delay))
            delay *= policy.backoff_factor
    assert last_exc is not None
    raise last_exc


def with_timeout(func: Callable[[], Any], timeout: float) -> Any:
    """Ejecuta `func` con un timeout (sync, hilo)."""
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(func)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError as exc:
            raise TimeoutError(f"Tool excedio el timeout de {timeout}s") from exc
