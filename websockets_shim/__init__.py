"""
Minimal asynchronous-compatible websocket client used when the `websockets`
package is unavailable in the execution environment (e.g., Testsprite sandboxes).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Optional

import websocket  # type: ignore


@dataclass
class _AsyncConnection:
    url: str
    kwargs: dict
    _conn: Optional[websocket.WebSocket] = None

    async def __aenter__(self) -> "_AsyncConnection":
        loop = asyncio.get_running_loop()
        self._conn = await loop.run_in_executor(None, lambda: websocket.create_connection(self.url, **self.kwargs))
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._conn is not None:
            await asyncio.get_running_loop().run_in_executor(None, self._conn.close)
            self._conn = None

    async def send(self, data: Any) -> None:
        if not self._conn:
            raise RuntimeError("WebSocket connection is not open")
        await asyncio.get_running_loop().run_in_executor(None, self._conn.send, data)

    async def recv(self) -> Any:
        if not self._conn:
            raise RuntimeError("WebSocket connection is not open")
        return await asyncio.get_running_loop().run_in_executor(None, self._conn.recv)


class _Connect:
    def __init__(self, url: str, **kwargs: Any) -> None:
        self._connection = _AsyncConnection(url, kwargs)

    def __await__(self):
        return self._connection.__aenter__().__await__()

    async def __aenter__(self) -> _AsyncConnection:
        return await self._connection.__aenter__()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._connection.__aexit__(exc_type, exc, tb)


def connect(url: str, **kwargs: Any) -> _Connect:
    return _Connect(url, **kwargs)


__all__ = ["connect"]


