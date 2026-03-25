# ================================================================
#  WB Park Madrid Simulation — Staff Thread
#
#  OS concepts:
#   · Daemon thread — runs alongside visitors, dies when main exits
#   · Reads shared attraction state (is_operational, queue_length)
#     through the attraction's own thread-safe properties
# ================================================================

import threading
import random

from logger import log


class Staff(threading.Thread):
    """
    One park employee assigned to an attraction.
    Periodically checks in, logs status, assists during breakdowns.
    """

    ROLES = [
        "Ride Operator",
        "Queue Manager",
        "Safety Inspector",
        "Guest Services",
        "Entertainer",
    ]

    def __init__(self, staff_id: int, attraction, clock):
        super().__init__(daemon=True, name=f"Staff-{staff_id:02d}")
        self.staff_id  = staff_id
        self.role      = random.choice(self.ROLES)
        self.attraction = attraction
        self.clock     = clock

    def run(self):
        log(
            "staff", self.name,
            f"👷 {self.role} — starting shift at '{self.attraction.name}'",
            self.clock,
        )

        while not self.clock.is_closed:
            self.clock.sleep(random.uniform(15, 25))   # periodic check-in

            if not self.attraction.is_operational:
                log(
                    "staff", self.name,
                    f"🔧 Assisting maintenance at '{self.attraction.name}'",
                    self.clock,
                )
            else:
                q = self.attraction.queue_length
                log(
                    "staff", self.name,
                    f"✅ '{self.attraction.name}' running — queue={q}",
                    self.clock,
                )

        log("staff", self.name, "👋 End of shift", self.clock)
