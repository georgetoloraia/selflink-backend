from __future__ import annotations

import threading
import time
from typing import ClassVar


class SnowflakeGenerator:
    """Generate sortable 64-bit IDs similar to Twitter snowflakes."""

    _epoch: ClassVar[int] = 1_704_151_200_000  # 2023-12-31
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, node_id: int = 1) -> None:
        if not 0 <= node_id < 1024:
            raise ValueError("node_id must be between 0 and 1023")
        self.node_id = node_id
        self._last_ts = -1
        self._sequence = 0

    def _timestamp(self) -> int:
        return int(time.time() * 1000)

    def get_id(self) -> int:
        with self._lock:
            ts = self._timestamp()
            if ts < self._last_ts:
                # clock moved backwards, wait until it catches up
                ts = self._wait_next(self._last_ts)

            if ts == self._last_ts:
                self._sequence = (self._sequence + 1) & 0xFFF
                if self._sequence == 0:
                    ts = self._wait_next(ts)
            else:
                self._sequence = 0

            self._last_ts = ts
            return ((ts - self._epoch) << 22) | (self.node_id << 12) | self._sequence

    def _wait_next(self, last_ts: int) -> int:
        ts = self._timestamp()
        while ts <= last_ts:
            time.sleep(0.0001)
            ts = self._timestamp()
        return ts


_GLOBAL_GENERATORS = {}
_REGISTRY_LOCK = threading.Lock()


def generate_id(node_id: int = 1) -> int:
    with _REGISTRY_LOCK:
        generator = _GLOBAL_GENERATORS.get(node_id)
        if generator is None:
            generator = SnowflakeGenerator(node_id=node_id)
            _GLOBAL_GENERATORS[node_id] = generator
    return generator.get_id()
