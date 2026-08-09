"""Deterministic HKDF-like seed expander utilities."""

from __future__ import annotations

import hashlib
import hmac
from typing import ByteString

DEFAULT_INFO = b"cpassgen::hkdf"


class SeedExpander:
    """Produce a deterministic pseudo-random byte stream from a seed."""

    def __init__(self, seed: ByteString, info: ByteString = DEFAULT_INFO):
        if not seed:
            raise ValueError("Seed must not be empty.")
        self._key = bytes(seed)
        self._info = bytes(info)
        self._buffer = bytearray()
        self._cursor = 0
        self._counter = 1

    def _refill(self) -> None:
        counter_bytes = self._counter.to_bytes(4, "big")
        block = hmac.new(
            self._key,
            self._info + counter_bytes,
            hashlib.sha256,
        ).digest()
        self._buffer.extend(block)
        self._counter += 1

    def take(self, length: int) -> bytes:
        if length <= 0:
            raise ValueError("Length must be positive.")
        available = len(self._buffer) - self._cursor
        while available < length:
            self._refill()
            available = len(self._buffer) - self._cursor
        start = self._cursor
        end = start + length
        self._cursor = end
        if self._cursor > 4096:
            # Drop consumed bytes to keep memory bounded.
            self._buffer = self._buffer[self._cursor :]  # noqa: E203
            self._cursor = 0
        return bytes(self._buffer[start:end])

    def randbelow(self, upper_bound: int) -> int:
        if upper_bound <= 0:
            raise ValueError("Upper bound must be positive.")
        needed_bits = upper_bound.bit_length()
        needed_bytes = max(1, (needed_bits + 7) // 8)
        while True:
            candidate = int.from_bytes(self.take(needed_bytes), "big")
            candidate &= (1 << needed_bits) - 1
            if candidate < upper_bound:
                return candidate
