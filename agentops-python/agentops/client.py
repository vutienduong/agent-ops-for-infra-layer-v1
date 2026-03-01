from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


@dataclass
class ClientConfig:
    api_key: str
    endpoint: str = "http://localhost:8000"
    environment: str = "dev"
    flush_interval_seconds: float = 1.0
    buffer_size: int = 25
    timeout_seconds: float = 5.0


class AgentOpsClient:
    def __init__(self, config: ClientConfig):
        self.config = config
        self._buffer: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._running = True
        self._thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._thread.start()

    def emit(self, event: dict[str, Any]) -> None:
        with self._lock:
            self._buffer.append(event)
            should_flush = len(self._buffer) >= self.config.buffer_size

        if should_flush:
            self.flush()

    def flush(self) -> None:
        with self._lock:
            if not self._buffer:
                return
            payload = list(self._buffer)
            self._buffer.clear()

        self._send_events(payload)

    def close(self) -> None:
        self._running = False
        self._thread.join(timeout=2)
        self.flush()

    def _flush_loop(self) -> None:
        while self._running:
            time.sleep(self.config.flush_interval_seconds)
            self.flush()

    def _send_events(self, events: Iterable[dict[str, Any]]) -> None:
        url = f"{self.config.endpoint.rstrip('/')}/v1/ingest"
        data = json.dumps(list(events)).encode("utf-8")

        request = urllib.request.Request(
            url=url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-AgentOps-Key": self.config.api_key,
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds):
                return
        except urllib.error.URLError:
            # MVP behavior: drop on network failure to avoid blocking user app.
            return
