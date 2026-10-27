from __future__ import annotations
import time


class SystemClock:
    def now(self) -> int:
        return int(time.time())


class ManualClock:
    def __init__(self, value: int = 0):
        self.value = value

    def now(self) -> int:
        return self.value

    def advance(self, seconds: int) -> None:
        self.value += seconds
