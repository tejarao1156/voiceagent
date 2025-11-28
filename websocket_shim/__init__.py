"""
Lightweight fallback implementation of the websocket-client API used in the
Testsprite suites. It wraps the synchronous client provided by the
`websockets` package so we don't need the external websocket-client wheel.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect


Callback = Optional[Callable[..., None]]


@dataclass
class _Callbacks:
    on_message: Callback = None
    on_error: Callback = None
    on_close: Callback = None
    on_open: Callback = None


class WebSocketApp:
    """
    Minimal WebSocketApp shim that matches the subset of the websocket-client
    API leveraged by the generated Testsprite suites.
    """

    def __init__(
        self,
        url: str,
        on_message: Callback = None,
        on_error: Callback = None,
        on_close: Callback = None,
        on_open: Callback = None,
        headers: Optional[Dict[str, str]] = None,
        **_: Any,
    ) -> None:
        self.url = url
        self.callbacks = _Callbacks(on_message, on_error, on_close, on_open)
        self.headers = headers or {}
        self.is_open = False
        self.closed = False
        self.error: Optional[BaseException] = None
        self._ws = None
        self._closing = False

    def send(self, data: Any) -> None:
        if self._ws is None:
            raise RuntimeError("WebSocket connection not open")
        self._ws.send(data)

    def close(self) -> None:
        self._closing = True
        if self._ws is not None:
            try:
                self._ws.close()
            finally:
                self._ws = None

    def run_forever(self) -> None:
        try:
            with connect(self.url, additional_headers=self.headers) as ws:
                self._ws = ws
                self.is_open = True
                self.closed = False
                if callable(self.callbacks.on_open):
                    self.callbacks.on_open(self)

                while not self._closing:
                    try:
                        message = ws.recv()
                    except ConnectionClosed as exc:
                        if not self._closing and callable(self.callbacks.on_close):
                            self.callbacks.on_close(self, exc.code, exc.reason)
                        break

                    if message is None:
                        break

                    if callable(self.callbacks.on_message):
                        self.callbacks.on_message(self, message)

                if callable(self.callbacks.on_close) and not self.closed:
                    self.callbacks.on_close(self, None, None)

        except BaseException as exc:  # noqa: BLE001
            self.error = exc
            if callable(self.callbacks.on_error):
                self.callbacks.on_error(self, exc)
            if callable(self.callbacks.on_close):
                self.callbacks.on_close(self, None, None)

        finally:
            self.is_open = False
            self.closed = True
            self._ws = None
            self._closing = False


__all__ = ["WebSocketApp"]


