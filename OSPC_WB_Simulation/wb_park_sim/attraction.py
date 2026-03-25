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

import config
from logger import log


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
        """
        name          – display name (e.g. "Batman La Fuga")
        attr_type     – "thrill" | "family" | "show" | "kids"
        capacity      – max simultaneous riders per cycle
        ride_duration – ride length in simulated minutes
        clock         – SimClock instance
        thrill_level  – 1-5 intensity rating
        """
        self.name          = name
        self.type          = attr_type
        self.capacity      = capacity
        self.ride_duration = ride_duration
        self.clock         = clock
        self.thrill_level  = thrill_level

        # ── OS Primitive 1: Semaphore ────────────────────────────────
        # Only `capacity` visitors can be on the ride at the same time.
        self._capacity_sem = threading.Semaphore(capacity)

        # ── OS Primitive 2: Lock ─────────────────────────────────────
        # Protects the queue deque against concurrent push/pop.
        self._queue_lock = threading.Lock()
        self._queue: deque = deque()

        # ── OS Primitive 3: Condition ────────────────────────────────
        # Visitors waiting during a breakdown block on this condition.
        # When the ride is repaired, notify_all() wakes every waiter.
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
        """
        Rough queue wait in sim-minutes.
        Formula: ceil(queue / capacity) × ride_duration
        """
        q = self.queue_length
        if q == 0:
            return 0
        batches = (q // self.capacity) + 1
        return batches * self.ride_duration

    # ----------------------------------------------------------
    # Visitor Interface
    # ----------------------------------------------------------
    def try_join_queue(self, visitor) -> bool:
        """
        Returns False immediately if the ride is down or the queue
        is at its maximum. Otherwise enqueues the visitor.
        """
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
        return True

    def ride(self, visitor) -> bool:
        """
        Blocking call. The visitor:
          1. Waits if the ride is broken (with a patience timeout).
          2. Acquires a semaphore slot (boards the ride).
          3. Sleeps for ride_duration sim-minutes.
          4. Releases the slot.

        Returns True if the visitor actually rode, False if they gave up.
        """
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

    # ----------------------------------------------------------
    # Event / Staff Interface
    # ----------------------------------------------------------
    def trigger_breakdown(self, duration_minutes: int):
        """
        Called by EventManager. Sets operational=False, then schedules
        a background thread to reopen after `duration_minutes` sim-minutes.
        Uses Condition.notify_all() to wake all blocked visitors.
        """
        with self._op_cond:
            self._operational = False
            with self._stats_lock:
                self.total_breakdowns += 1
        log(
            "event", self.name,
            f"⚠️  BREAKDOWN — closed for ≈{duration_minutes} sim-min",
            self.clock,
        )

        def _reopen():
            self.clock.sleep(duration_minutes)
            with self._op_cond:
                self._operational = True
                self._op_cond.notify_all()   # wake every waiting visitor
            log("event", self.name, "✅ Back in operation", self.clock)

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
