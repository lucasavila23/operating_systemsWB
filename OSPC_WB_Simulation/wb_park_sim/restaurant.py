# ================================================================
#  WB Park Madrid Simulation — Restaurant
#
#  OS concepts:
#   · threading.Semaphore – limits diners to available table slots
#   · threading.Lock      – protects waiting-count and stats
# ================================================================

import threading
import random

import config
from logger import log


class Restaurant:
    """
    Food/drink outlet. Visitors acquire a table slot (Semaphore),
    eat for `serve_time` sim-minutes, then release the slot.
    """

    def __init__(
        self,
        name:       str,
        food_type:  str,
        capacity:   int,
        serve_time: int,
        clock,
    ):
        """
        name       – display name
        food_type  – "sit_down" | "fast_food" | "snack" | "drinks"
        capacity   – simultaneous diners (table slots)
        serve_time – time to order + eat (sim-minutes)
        clock      – SimClock instance
        """
        self.name      = name
        self.type      = food_type
        self.capacity  = capacity
        self.serve_time = serve_time
        self.clock     = clock

        # ── OS Primitive: Semaphore ───────────────────────────────────
        # Exactly `capacity` visitors may eat at the same time.
        self._table_sem = threading.Semaphore(capacity)

        self._waiting      = 0
        self._waiting_lock = threading.Lock()

        self.total_served = 0
        self._stats_lock  = threading.Lock()

    # ----------------------------------------------------------
    # Properties
    # ----------------------------------------------------------
    @property
    def waiting_count(self) -> int:
        with self._waiting_lock:
            return self._waiting

    # ----------------------------------------------------------
    # Visitor Interface
    # ----------------------------------------------------------
    def eat(self, visitor) -> bool:
        """
        Visitor blocks until a table is free, eats, then leaves.
        Restores visitor hunger and energy on completion.
        """
        with self._waiting_lock:
            self._waiting += 1

        log(
            "restaurant", self.name,
            f"{visitor.name} waiting for a table (waiting={self.waiting_count})",
            self.clock,
        )

        # Block until a table slot is available
        self._table_sem.acquire()

        with self._waiting_lock:
            self._waiting -= 1

        cost = round(random.uniform(8, 22), 2)
        try:
            log(
                "restaurant", self.name,
                f"{visitor.name} eating 🍔  (≈{self.serve_time} sim-min, €{cost})",
                self.clock,
            )
            self.clock.sleep(self.serve_time)

            # Restore visitor's needs
            visitor.hunger  = max(0,   visitor.hunger  - config.HUNGER_RESTORE_EAT)
            visitor.energy  = min(100, visitor.energy  + config.ENERGY_RESTORE_EAT)
            visitor.money  -= cost

            log("restaurant", self.name, f"{visitor.name} finished eating", self.clock)

            with self._stats_lock:
                self.total_served += 1
            return True

        finally:
            self._table_sem.release()

    # ----------------------------------------------------------
    # Stats
    # ----------------------------------------------------------
    def stats(self) -> dict:
        return {
            "name":    self.name,
            "served":  self.total_served,
            "waiting": self.waiting_count,
        }
