# ================================================================
#  WB Park Madrid Simulation — Random Event Manager
#
#  OS concepts:
#   · Daemon thread scheduling random events throughout the day
#   · Calls attraction.trigger_breakdown() which internally uses
#     Condition.notify_all() to wake all blocked visitor threads
# ================================================================

import threading
import random

from .logger import log
from .simstate import SimState


class EventManager(threading.Thread):
    """
    Fires park-wide random events at irregular intervals.
    Events range from ride breakdowns (affect threads via Condition)
    to narrative announcements (logged only).
    """

    def __init__(self, park, clock):
        super().__init__(daemon=True, name="EventManager")
        self.park        = park
        self.clock       = clock
        self._subscribers: dict[str, list] = {}

    # ----------------------------------------------------------
    # Observer interface
    # ----------------------------------------------------------
    def subscribe(self, event_type: str, listener):
        self._subscribers.setdefault(event_type, []).append(listener)

    def _notify(self, event_type: str, data: dict):
        for listener in self._subscribers.get(event_type, []):
            listener(event_type, data)

    def run(self):
        self.clock.sleep(random.uniform(20, 40))

        while not self.clock.is_closed:
            event = random.choices(
                population=["breakdown", "weather", "vip", "flash_sale", "show"],
                weights=   [      0.20,      0.15,  0.15,         0.25,   0.25],
            )[0]
            self._fire(event)
            self.clock.sleep(random.uniform(10, 30))

    def _fire(self, event: str):
        if event == "breakdown":
            candidates = [a for a in self.park.attractions if a.is_operational]
            if candidates:
                victim   = random.choice(candidates)
                duration = random.randint(10, 25)
                self._notify("breakdown", {"attraction": victim, "duration": duration})

        elif event == "weather":
            cond = random.choice(["☀️  Sunny spell", "🌧️  Light rain", "🌤️  Clouds clearing"])
            msg = f"{cond} — slight effect on visitor mood"
            log("event", "Weather", msg, self.clock)
            SimState.get().emit("event_log", {"message": f"Weather: {msg}", "category": "event"}, self.clock.time_str)

        elif event == "vip":
            vip = random.choice([
                "a celebrity spotted near Batman",
                "a sports star visiting Looney Tunes area",
                "a Warner Bros executive touring the park",
            ])
            msg = f"⭐ VIP alert: {vip}!"
            log("event", "Security", msg, self.clock)
            SimState.get().emit("event_log", {"message": f"Security: {msg}", "category": "event"}, self.clock.time_str)

        elif event == "flash_sale":
            restaurant = random.choice(self.park.restaurants)
            msg = f"📣 Flash deal: 30% off at '{restaurant.name}' for 10 min!"
            log("event", "Announcements", msg, self.clock)
            SimState.get().emit("event_log", {"message": msg, "category": "event"}, self.clock.time_str)

        elif event == "show":
            msg = "🎭 Superman stunt show in 15 min at the Main Stage — don't miss it!"
            log("event", "Announcements", msg, self.clock)
            SimState.get().emit("event_log", {"message": msg, "category": "event"}, self.clock.time_str)
