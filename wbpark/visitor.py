# ================================================================
#  WB Park Madrid Simulation — Visitor Thread
#
#  Each visitor is a thread that runs a continuous decision loop
#  for the whole day — just like a real person at a theme park.
#
#  OS concepts:
#   · threading.Thread  – one OS thread per visitor
#   · Shared state read – reads attraction queues, restaurant wait
#     counts (all protected inside those objects)
#   · No direct lock here — visitor only owns its own attributes
# ================================================================

import threading
import random
import time
from enum import Enum

from . import config
from .logger import log
from .simstate import SimState
from .strategies import DecisionStrategy


# ── Visitor State Machine ─────────────────────────────────────────────
class State(Enum):
    ARRIVING  = "arriving"
    EXPLORING = "exploring"
    QUEUEING  = "queueing"
    RIDING    = "riding"
    EATING    = "eating"
    RESTROOM  = "restroom"
    RESTING   = "resting"
    EXITING   = "exiting"
    DONE      = "done"


# ── Name pool ─────────────────────────────────────────────────────────
_NAMES = [
    "Alice","Bruno","Carmen","Diego","Elena","Fran","Gabi","Hugo",
    "Ines","Javi","Karla","Luis","Marta","Noa","Oscar","Paula",
    "Quim","Rosa","Sergio","Tania","Urko","Vera","Xabi","Yolanda",
    "Zoe","Andres","Bea","Carlos","Dani","Eva","Felix","Gloria",
    "Hector","Irene","Jorge","Keila","Laura","Miguel","Neus","Olga",
]


class Visitor(threading.Thread):
    """
    Simulates one park guest for a full day.

    Decision priority each loop iteration:
        1. Bladder critical  → nearest restroom
        2. Very hungry       → best available restaurant
        3. Low energy        → sit and rest
        4. Park closing soon → only join very short queues
        5. Default           → score every attraction, pick the best
    """

    def __init__(self, visitor_id: int, park, clock, delay_minutes: float = 0,
                 strategy: DecisionStrategy = None):
        super().__init__(daemon=True, name=f"Visitor-{visitor_id:02d}")

        self.visitor_id = visitor_id
        self.name       = _NAMES[visitor_id % len(_NAMES)]
        self.park       = park
        self.clock      = clock
        self.delay      = delay_minutes
        self.strategy   = strategy

        self.energy  = random.uniform(85, 100)
        self.hunger  = random.uniform(0, 20)
        self.bladder = random.uniform(0, 15)
        self.money   = random.uniform(40, 180)
        self.gender  = random.choice(["M", "F"])

        self.ticket_type = "fastpass" if random.random() < 0.20 else "standard"

        all_types        = ["thrill", "family", "show", "kids"]
        self.preferences = random.sample(all_types, k=random.randint(1, 3))

        self.visited: dict[str, int] = {}

        self.state = State.ARRIVING

        self.rides_taken = 0
        self.meals_eaten = 0
        self.wc_visits   = 0

        self._last_tick: int = 0

    # ------------------------------------------------------------------
    # Thread entry point
    # ------------------------------------------------------------------
    def run(self):
        if self.delay > 0:
            self.clock.sleep(self.delay)

        while not self.clock.is_open and not self.clock.is_closed:
            time.sleep(0.05)

        if self.clock.is_closed:
            return

        self._last_tick = self.clock.now

        log(
            "visitor", self.name,
            f"🎉 Entered the park!  "
            f"energy={self.energy:.0f}  hunger={self.hunger:.0f}  "
            f"prefs={self.preferences}",
            self.clock,
        )

        while self.state not in (State.EXITING, State.DONE):
            self._tick_needs()

            if self._should_exit():
                break

            action = self._decide()
            self._execute(action)

        self.state = State.EXITING
        log(
            "visitor", self.name,
            f"🚪 Leaving park — "
            f"rides={self.rides_taken}  meals={self.meals_eaten}  "
            f"energy={self.energy:.0f}",
            self.clock,
        )
        self.park.visitor_left(self)
        self.state = State.DONE

    # ------------------------------------------------------------------
    # Need simulation
    # ------------------------------------------------------------------
    def _tick_needs(self):
        now = self.clock.now
        dt  = max(0, now - self._last_tick)
        self._last_tick = now

        if dt == 0:
            return

        self.hunger  = min(100, self.hunger  + config.HUNGER_RATE  * dt)
        self.bladder = min(100, self.bladder + config.BLADDER_RATE * dt)
        self.energy  = max(0,   self.energy  - config.ENERGY_IDLE  * dt)

    # ------------------------------------------------------------------
    # Exit condition
    # ------------------------------------------------------------------
    def _should_exit(self) -> bool:
        if self.energy <= config.ENERGY_EXIT_THRESHOLD:
            log("visitor", self.name, "😴 Exhausted — heading home", self.clock)
            return True
        if self.clock.is_closed:
            log("visitor", self.name, "🔔 Park closed — leaving", self.clock)
            return True
        if self.money <= 0:
            log("visitor", self.name, "💸 Out of money — leaving", self.clock)
            return True
        return False

    # ------------------------------------------------------------------
    # Decision engine
    # ------------------------------------------------------------------
    def _decide(self) -> tuple:
        return self.strategy.decide(self, self.park, self.clock)

    # ------------------------------------------------------------------
    # Action execution
    # ------------------------------------------------------------------
    def _execute(self, action: tuple):
        kind = action[0]
        target = action[1].name if len(action) > 1 and action[1] is not None else "resting"
        SimState.get().emit("visitor_state", {
            "name": self.name,
            "state": self.state.value,
            "target": target,
        }, self.clock.time_str)
        if   kind == "ride":     self._do_ride(action[1])
        elif kind == "eat":      self._do_eat(action[1])
        elif kind == "restroom": self._do_restroom(action[1])
        elif kind == "rest":     self._do_rest()

    def _travel(self, dest: str):
        t = random.uniform(config.TRAVEL_TIME_MIN, config.TRAVEL_TIME_MAX)
        log("visitor", self.name, f"🚶 Walking to {dest} ({t:.0f} min)", self.clock)
        self.clock.sleep(t)

    def _do_ride(self, attraction):
        self._travel(attraction.name)
        self.state = State.QUEUEING

        if not attraction.try_join_queue(self):
            log(
                "visitor", self.name,
                f"❌ Skipping {attraction.name} — queue too long or closed",
                self.clock,
            )
            self.state = State.EXPLORING
            return

        self.state = State.RIDING
        rode = attraction.ride(self)

        if rode:
            self.rides_taken += 1
            self.energy = max(0, self.energy - config.ENERGY_COST_RIDE)
            self.visited[attraction.name] = self.visited.get(attraction.name, 0) + 1
            log(
                "visitor", self.name,
                f"🎢 Great ride! {attraction.name}  "
                f"(total rides today: {self.rides_taken}, energy={self.energy:.0f})",
                self.clock,
            )

        self.state = State.EXPLORING

    def _do_eat(self, restaurant):
        self._travel(restaurant.name)
        self.state = State.EATING
        restaurant.eat(self)
        self.meals_eaten += 1
        self.state = State.EXPLORING

    def _do_restroom(self, restroom):
        self._travel(restroom.name)
        self.state = State.RESTROOM
        restroom.use(self)
        self.wc_visits += 1
        self.state = State.EXPLORING

    def _do_rest(self):
        rest_t = random.uniform(5, 15)
        log(
            "visitor", self.name,
            f"💺 Resting for {rest_t:.0f} min  (energy={self.energy:.0f})",
            self.clock,
        )
        self.state = State.RESTING
        self.clock.sleep(rest_t)
        self.energy = min(100, self.energy + config.ENERGY_RESTORE_REST)
        self.state = State.EXPLORING

    def __repr__(self):
        return (
            f"Visitor({self.name}, {self.state.value}, "
            f"E={self.energy:.0f} H={self.hunger:.0f} B={self.bladder:.0f})"
        )
