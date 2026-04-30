# ================================================================
#  WB Park Madrid Simulation — Attraction (Ride / Show)
#
#  OS concepts:
#   · threading.Semaphore  – limits simultaneous riders to `capacity`
#   · threading.Lock       – protects queue deque from race conditions
#   · threading.Condition  – visitors block while attraction is broken;
#                            staff signals all waiters when it reopens
# ================================================================

import threading
import time
from collections import deque

from . import config
from .logger import log
from .simstate import SimState


class Attraction:
    """
    A single ride or show at WB Park Madrid.

    Lifecycle per visitor:
        1. try_join_queue()  → adds visitor to queue if space allows
        2. ride()            → visitor blocks until boarded & ride ends
        3. (optional) trigger_breakdown() called by EventManager
    """

    def __init__(
        self,
        name:          str,
        attr_type:     str,
        capacity:      int,
        ride_duration: int,
        clock,
        thrill_level:  int = 3,
    ):
        self.name          = name
        self.type          = attr_type
        self.capacity      = capacity
        self.ride_duration = ride_duration
        self.clock         = clock
        self.thrill_level  = thrill_level

        # ── OS Primitive 1: Semaphore ────────────────────────────────
        self._capacity_sem = threading.Semaphore(capacity)

        # ── OS Primitive 2: Lock ─────────────────────────────────────
        self._queue_lock = threading.Lock()
        self._queue: deque = deque()

        # ── OS Primitive 3: Condition ────────────────────────────────
        self._op_cond   = threading.Condition()
        self._operational = True

        # Stats
        self.total_riders     = 0
        self.total_breakdowns = 0
        self._stats_lock      = threading.Lock()

    # ----------------------------------------------------------
    # Properties
    # ----------------------------------------------------------
    @property
    def queue_length(self) -> int:
        with self._queue_lock:
            return len(self._queue)

    @property
    def is_operational(self) -> bool:
        with self._op_cond:
            return self._operational

    def estimated_wait(self) -> int:
        q = self.queue_length
        if q == 0:
            return 0
        batches = (q // self.capacity) + 1
        return batches * self.ride_duration

    # ----------------------------------------------------------
    # Visitor Interface
    # ----------------------------------------------------------
    def try_join_queue(self, visitor) -> bool:
        if not self.is_operational:
            return False
        if self.queue_length >= config.MAX_QUEUE_LENGTH:
            return False
        with self._queue_lock:
            self._queue.append(visitor)
        log(
            "attraction", self.name,
            f"{visitor.name} joined queue "
            f"(len={self.queue_length}, wait≈{self.estimated_wait()} min)",
            self.clock,
        )
        SimState.get().emit("attraction_state", {
            "name": self.name,
            "queue_length": self.queue_length,
            "is_operational": self.is_operational,
            "total_riders": self.total_riders,
            "total_breakdowns": self.total_breakdowns,
        }, self.clock.time_str)
        return True

    def ride(self, visitor) -> bool:
        patience_real = config.QUEUE_PATIENCE_MIN / config.SIMULATION_SPEED

        # Step 1 — wait out any breakdown ─────────────────────────────
        with self._op_cond:
            deadline = time.time() + patience_real
            while not self._operational:
                remaining = deadline - time.time()
                if remaining <= 0:
                    self._dequeue(visitor)
                    log(
                        "attraction", self.name,
                        f"{visitor.name} LEFT queue (gave up during breakdown)",
                        self.clock,
                    )
                    return False
                self._op_cond.wait(timeout=remaining)

        # Step 2 — acquire boarding slot (Semaphore) ──────────────────
        deadline = time.time() + patience_real
        while True:
            acquired = self._capacity_sem.acquire(timeout=0.05)
            if acquired:
                break
            if time.time() >= deadline:
                self._dequeue(visitor)
                log(
                    "attraction", self.name,
                    f"{visitor.name} LEFT queue (patience ran out)",
                    self.clock,
                )
                return False

        # Step 3 — ride! ──────────────────────────────────────────────
        try:
            self._dequeue(visitor)
            log(
                "attraction", self.name,
                f"{visitor.name} BOARDING — ride lasts {self.ride_duration} sim-min",
                self.clock,
            )
            self.clock.sleep(self.ride_duration)
            log("attraction", self.name, f"{visitor.name} FINISHED ride", self.clock)

            with self._stats_lock:
                self.total_riders += 1
            SimState.get().emit("attraction_state", {
                "name": self.name,
                "queue_length": self.queue_length,
                "is_operational": self.is_operational,
                "total_riders": self.total_riders,
                "total_breakdowns": self.total_breakdowns,
            }, self.clock.time_str)
            return True

        finally:
            # Step 4 — release slot ───────────────────────────────────
            self._capacity_sem.release()

    def _dequeue(self, visitor):
        with self._queue_lock:
            try:
                self._queue.remove(visitor)
            except ValueError:
                pass
        SimState.get().emit("attraction_state", {
            "name": self.name,
            "queue_length": self.queue_length,
            "is_operational": self.is_operational,
            "total_riders": self.total_riders,
            "total_breakdowns": self.total_breakdowns,
        }, self.clock.time_str)

    # ----------------------------------------------------------
    # Event / Staff Interface
    # ----------------------------------------------------------
    def on_event(self, event_type: str, data: dict):
        """Observer callback — called by EventManager._notify()."""
        if event_type == "breakdown" and data.get("attraction") is self:
            self.trigger_breakdown(data["duration"])

    def trigger_breakdown(self, duration_minutes: int):
        with self._op_cond:
            self._operational = False
            with self._stats_lock:
                self.total_breakdowns += 1
        log(
            "event", self.name,
            f"⚠️  BREAKDOWN — closed for ≈{duration_minutes} sim-min",
            self.clock,
        )
        SimState.get().emit("breakdown", {
            "name": self.name,
            "duration": duration_minutes,
        }, self.clock.time_str)
        SimState.get().emit("attraction_state", {
            "name": self.name,
            "queue_length": self.queue_length,
            "is_operational": False,
            "total_riders": self.total_riders,
            "total_breakdowns": self.total_breakdowns,
        }, self.clock.time_str)

        def _reopen():
            self.clock.sleep(duration_minutes)
            with self._op_cond:
                self._operational = True
                self._op_cond.notify_all()
            log("event", self.name, "✅ Back in operation", self.clock)
            SimState.get().emit("attraction_state", {
                "name": self.name,
                "queue_length": self.queue_length,
                "is_operational": True,
                "total_riders": self.total_riders,
                "total_breakdowns": self.total_breakdowns,
            }, self.clock.time_str)

        threading.Thread(
            target=_reopen, daemon=True, name=f"{self.name}-repair"
        ).start()

    # ----------------------------------------------------------
    # Stats
    # ----------------------------------------------------------
    def stats(self) -> dict:
        return {
            "name":       self.name,
            "riders":     self.total_riders,
            "breakdowns": self.total_breakdowns,
            "queue_now":  self.queue_length,
        }
