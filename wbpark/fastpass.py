# ================================================================
#  WB Park Madrid Simulation — FastPass Decorator
#
#  FastPassAttraction wraps any Attraction and adds a priority
#  boarding lane for visitors whose ticket_type == "fastpass".
#
#  OS concepts (new):
#   · Second Semaphore (_fastpass_sem) — independent slot pool
#     for FastPass boarders; does not contend with the regular
#     _capacity_sem used by standard-queue visitors.
#
#  Design:
#   · __getattr__ proxies every attribute/method not explicitly
#     overridden to the wrapped Attraction, so the wrapper is
#     transparent to the rest of the simulation.
# ================================================================

import threading
import time
from collections import deque

from . import config
from .logger import log


class FastPassAttraction:
    """
    Decorator around Attraction.

    - Standard visitors: delegated entirely to wrapped.try_join_queue / ride.
    - FastPass visitors: added to fastpass_queue, acquire _fastpass_sem,
      and skip straight to boarding without waiting in the regular queue.
    """

    def __init__(self, wrapped):
        self._wrapped      = wrapped
        self.fastpass_queue = deque()
        self._fastpass_sem  = threading.Semaphore(wrapped.capacity)

    # ----------------------------------------------------------
    # Transparent proxy to wrapped Attraction
    # ----------------------------------------------------------
    def __getattr__(self, name):
        return getattr(self._wrapped, name)

    # ----------------------------------------------------------
    # Override: queue join
    # ----------------------------------------------------------
    def try_join_queue(self, visitor) -> bool:
        if visitor.ticket_type == "fastpass":
            if not self._wrapped.is_operational:
                return False
            self.fastpass_queue.append(visitor)
            log(
                "attraction", self._wrapped.name,
                f"{visitor.name} joined FASTPASS queue "
                f"(regular wait≈{self.estimated_wait()} min)",
                self._wrapped.clock,
            )
            return True
        return self._wrapped.try_join_queue(visitor)

    # ----------------------------------------------------------
    # Override: boarding
    # ----------------------------------------------------------
    def ride(self, visitor) -> bool:
        if visitor.ticket_type == "fastpass":
            return self._ride_fastpass(visitor)
        return self._wrapped.ride(visitor)

    def _ride_fastpass(self, visitor) -> bool:
        if not self._wrapped.is_operational:
            self._fp_dequeue(visitor)
            return False

        patience_real = config.QUEUE_PATIENCE_MIN / config.SIMULATION_SPEED
        deadline      = time.time() + patience_real

        while True:
            acquired = self._fastpass_sem.acquire(timeout=0.05)
            if acquired:
                break
            if time.time() >= deadline:
                self._fp_dequeue(visitor)
                log(
                    "attraction", self._wrapped.name,
                    f"{visitor.name} LEFT fastpass queue (patience ran out)",
                    self._wrapped.clock,
                )
                return False

        try:
            self._fp_dequeue(visitor)
            log(
                "attraction", self._wrapped.name,
                f"{visitor.name} ⚡ FASTPASS BOARDING",
                self._wrapped.clock,
            )
            self._wrapped.clock.sleep(self._wrapped.ride_duration)
            log(
                "attraction", self._wrapped.name,
                f"{visitor.name} FINISHED ride (fastpass)",
                self._wrapped.clock,
            )
            with self._wrapped._stats_lock:
                self._wrapped.total_riders += 1
            from .simstate import SimState
            SimState.get().emit("attraction_state", {
                "name": self._wrapped.name,
                "queue_length": self._wrapped.queue_length,
                "is_operational": self._wrapped.is_operational,
                "total_riders": self._wrapped.total_riders,
                "total_breakdowns": self._wrapped.total_breakdowns,
            }, self._wrapped.clock.time_str)
            return True
        finally:
            self._fastpass_sem.release()

    def _fp_dequeue(self, visitor):
        try:
            self.fastpass_queue.remove(visitor)
        except ValueError:
            pass

    # ----------------------------------------------------------
    # Override: estimated wait (FastPass lane is effectively halved)
    # ----------------------------------------------------------
    def estimated_wait(self) -> int:
        return self._wrapped.estimated_wait() // 2

    # ----------------------------------------------------------
    # Override: on_event — identity check must use *this* wrapper
    # ----------------------------------------------------------
    def on_event(self, event_type: str, data: dict):
        if event_type == "breakdown" and data.get("attraction") is self:
            self._wrapped.trigger_breakdown(data["duration"])
