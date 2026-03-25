# ================================================================
#  WB Park Madrid Simulation — Restroom
#
#  OS concepts:
#   · Two independent Semaphores — one per gender — so male and
#     female stalls are managed as separate resource pools
# ================================================================

import threading

import config
from logger import log


class Restroom:
    """
    Restroom block with gendered stalls.
    Each gender has its own Semaphore(stall_count) so contention
    is tracked independently.
    """

    USE_TIME = 3   # sim-minutes per visit

    def __init__(
        self,
        name:          str,
        male_stalls:   int,
        female_stalls: int,
        clock,
    ):
        self.name          = name
        self.male_stalls   = male_stalls
        self.female_stalls = female_stalls
        self.clock         = clock

        # ── OS Primitive: two Semaphores ─────────────────────────────
        self._male_sem   = threading.Semaphore(male_stalls)
        self._female_sem = threading.Semaphore(female_stalls)

        self.total_uses  = 0
        self._stats_lock = threading.Lock()

    # ----------------------------------------------------------
    # Visitor Interface
    # ----------------------------------------------------------
    def use(self, visitor) -> bool:
        """
        Selects the correct semaphore based on visitor gender,
        blocks until a stall is free, uses it, then releases.
        """
        sem = self._female_sem if visitor.gender == "F" else self._male_sem

        log(
            "restroom", self.name,
            f"{visitor.name} ({visitor.gender}) waiting for a stall",
            self.clock,
        )
        sem.acquire()
        try:
            log("restroom", self.name, f"{visitor.name} using restroom", self.clock)
            self.clock.sleep(self.USE_TIME)
            visitor.bladder = max(0, visitor.bladder - config.BLADDER_RESTORE_WC)
            with self._stats_lock:
                self.total_uses += 1
            return True
        finally:
            sem.release()

    # ----------------------------------------------------------
    # Stats
    # ----------------------------------------------------------
    def stats(self) -> dict:
        return {"name": self.name, "uses": self.total_uses}
