# ================================================================
#  WB Park Madrid Simulation — Park (Central Hub)
#
#  Owns all attractions, restaurants and restrooms.
#  Provides lookup helpers used by Visitor threads.
#
#  OS concepts:
#   · threading.Lock  – protects the live visitor counter
#   · threading.Event – signals full park closure to any thread
#                       that wants to check
# ================================================================

import threading
import random

from attraction import Attraction
from restaurant import Restaurant
from restroom   import Restroom
from logger     import log


class Park:
    """
    Instantiates every park entity and acts as a shared directory
    for visitor threads to query (nearest restroom, best restaurant, etc.).
    """

    def __init__(self, clock):
        self.clock = clock

        # ── OS Primitive: Lock ────────────────────────────────────────
        self._visitor_lock  = threading.Lock()
        self._visitor_count = 0

        # ── OS Primitive: Event ───────────────────────────────────────
        # Set when the park physically closes (last visitor gone).
        self.closed_event = threading.Event()

        # ── Build entities ────────────────────────────────────────────
        self.attractions = self._build_attractions()
        self.restaurants = self._build_restaurants()
        self.restrooms   = self._build_restrooms()

    # ------------------------------------------------------------------
    # Entity builders — WB Park Madrid attractions
    # ------------------------------------------------------------------
    def _build_attractions(self):
        c = self.clock
        return [
            # Thrill rides
            Attraction("Batman La Fuga",           "thrill",  4,  5, c, thrill_level=5),
            Attraction("Superman: La Atracción",   "thrill",  6,  4, c, thrill_level=4),
            Attraction("Stunt Falls",              "thrill",  8,  6, c, thrill_level=4),
            # Family rides
            Attraction("Tom y Jerry: La Fuga",     "family", 12,  4, c, thrill_level=2),
            Attraction("Scooby-Doo Mansion",       "family",  8,  5, c, thrill_level=2),
            Attraction("Aqua Mania",               "family", 10,  7, c, thrill_level=3),
            # Shows
            Attraction("Superman Stunt Show",      "show",   50, 25, c, thrill_level=2),
            Attraction("Looney Tunes Live Show",   "show",   80, 20, c, thrill_level=1),
            # Kids
            Attraction("Looney Tunes Carousel",   "kids",   12,  3, c, thrill_level=1),
            Attraction("Bugs Bunny World",         "kids",   15,  4, c, thrill_level=1),
        ]

    def _build_restaurants(self):
        c = self.clock
        return [
            Restaurant("Gotham City Kitchen",     "sit_down",  20, 25, c),
            Restaurant("Looney Tunes Snack Bar",  "fast_food", 30, 10, c),
            Restaurant("Krypton Burgers",         "fast_food", 25, 12, c),
            Restaurant("Hogwarts Café",           "sit_down",  15, 20, c),
            Restaurant("WB Ice Cream Stand",      "snack",     10,  5, c),
        ]

    def _build_restrooms(self):
        c = self.clock
        return [
            Restroom("Main Entrance WC",     male_stalls=4, female_stalls=6, clock=c),
            Restroom("Gotham Area WC",       male_stalls=3, female_stalls=5, clock=c),
            Restroom("Looney Tunes Area WC", male_stalls=3, female_stalls=4, clock=c),
            Restroom("Superman Plaza WC",    male_stalls=3, female_stalls=5, clock=c),
        ]

    # ------------------------------------------------------------------
    # Visitor helpers — called from Visitor threads
    # ------------------------------------------------------------------
    def nearest_restroom(self) -> Restroom:
        """
        In a real grid-based model this would pick the closest one.
        Here we pick at random (simplified).
        """
        return random.choice(self.restrooms)

    def best_restaurant(self) -> Restaurant:
        """Returns the restaurant with the fewest visitors currently waiting."""
        return min(self.restaurants, key=lambda r: r.waiting_count)

    # ------------------------------------------------------------------
    # Visitor tracking — thread-safe counter
    # ------------------------------------------------------------------
    def visitor_entered(self):
        with self._visitor_lock:
            self._visitor_count += 1

    def visitor_left(self, visitor):
        with self._visitor_lock:
            self._visitor_count -= 1
            log(
                "park", "Gate",
                f"{visitor.name} exited. Visitors still inside: {self._visitor_count}",
                self.clock,
            )
            if self._visitor_count == 0:
                self.closed_event.set()

    @property
    def visitor_count(self) -> int:
        with self._visitor_lock:
            return self._visitor_count

    # ------------------------------------------------------------------
    # End-of-day report
    # ------------------------------------------------------------------
    def print_stats(self):
        sep = "=" * 62
        print(f"\n{sep}")
        print("  🎢  WB PARK MADRID — END-OF-DAY REPORT")
        print(sep)

        print("\n  ATTRACTIONS")
        print(f"  {'Name':<32} {'Riders':>7}  {'Breakdowns':>10}")
        print("  " + "-" * 54)
        for a in self.attractions:
            s = a.stats()
            print(
                f"  {s['name']:<32} {s['riders']:>7}  {s['breakdowns']:>10}"
            )

        print("\n  RESTAURANTS")
        print(f"  {'Name':<32} {'Served':>7}")
        print("  " + "-" * 40)
        for r in self.restaurants:
            s = r.stats()
            print(f"  {s['name']:<32} {s['served']:>7}")

        print("\n  RESTROOMS")
        print(f"  {'Name':<32} {'Uses':>7}")
        print("  " + "-" * 40)
        for wc in self.restrooms:
            s = wc.stats()
            print(f"  {s['name']:<32} {s['uses']:>7}")

        print(f"\n{sep}\n")
