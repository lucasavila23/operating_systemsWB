# ================================================================
#  WB Park Madrid Simulation — Entry Point
#
#  Thread inventory when running:
#    · 1  SimClock daemon thread
#    · 1  EventManager daemon thread
#    · N  Staff daemon threads  (one per attraction)
#    · V  Visitor threads       (V = --visitors, default 40)
#
#  The main thread waits for ALL visitor threads to finish,
#  then prints the end-of-day report.
# ================================================================

import argparse
import random
import sys
import time

# Force UTF-8 output so emojis render on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import config
from clock      import SimClock
from park       import Park
from visitor    import Visitor
from staff      import Staff
from events     import EventManager
from logger     import log
from strategies import ThrillSeekerStrategy, FamilyStrategy, EfficientRouteStrategy

_STRATEGY_CYCLE = [ThrillSeekerStrategy, FamilyStrategy, EfficientRouteStrategy]


def parse_args():
    p = argparse.ArgumentParser(
        description="WB Park Madrid — OS & Parallel Computing Simulation"
    )
    p.add_argument(
        "--visitors", type=int, default=config.NUM_VISITORS,
        help=f"Number of visitors (default: {config.NUM_VISITORS})"
    )
    p.add_argument(
        "--speed", type=float, default=config.SIMULATION_SPEED,
        help="Sim speed: sim-seconds per real-second (default: 60)"
    )
    p.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducible runs"
    )
    return p.parse_args()


def main():
    args = parse_args()

    # Apply overrides before any module reads config
    config.SIMULATION_SPEED = args.speed
    if args.seed is not None:
        random.seed(args.seed)

    # ── Banner ────────────────────────────────────────────────────────
    print("\n" + "=" * 62)
    print("  🎢  WB PARK MADRID SIMULATION")
    print("  Operating Systems & Parallel Computing")
    print(f"  Visitors: {args.visitors}   Speed: {args.speed}x   Seed: {args.seed}")
    print("=" * 62 + "\n")

    # ── 1. Simulation clock ───────────────────────────────────────────
    clock = SimClock()
    log("park", "System", f"🕙 Clock started — park opens at 10:00", clock)

    # ── 2. Park (creates all rides, restaurants, restrooms) ───────────
    park = Park(clock)
    log(
        "park", "System",
        f"🏗️  Park built: {len(park.attractions)} attractions, "
        f"{len(park.restaurants)} restaurants, {len(park.restrooms)} restrooms",
        clock,
    )

    # ── 3. Staff threads (one per attraction) ─────────────────────────
    for i, attraction in enumerate(park.attractions):
        Staff(i, attraction, clock).start()

    # ── 4. Event manager — subscribe every attraction before starting ─
    em = EventManager(park, clock)
    for attraction in park.attractions:
        em.subscribe("breakdown", attraction.on_event)
    em.start()

    # ── 5. Visitor threads with staggered arrivals ────────────────────
    visitors = []
    for i in range(args.visitors):
        delay    = random.uniform(0, config.ARRIVAL_WINDOW_MIN)
        strategy = _STRATEGY_CYCLE[i % len(_STRATEGY_CYCLE)]()
        v = Visitor(i, park, clock, delay_minutes=delay, strategy=strategy)
        visitors.append(v)
        park.visitor_entered()

    log("park", "System", f"🚌 {args.visitors} visitors en route to the park…", clock)

    for v in visitors:
        v.start()

    # ── 6. Wait for every visitor to leave ───────────────────────────
    for v in visitors:
        v.join()

    # ── 7. Shut clock down and report ────────────────────────────────
    clock.stop()
    log("park", "System", "🔒 All visitors have left. Park closed.", clock)
    park.print_stats()

    # Visitor leaderboard
    top = sorted(visitors, key=lambda v: v.rides_taken, reverse=True)[:5]
    print("  🏆  TOP 5 RIDERS TODAY")
    for rank, v in enumerate(top, 1):
        print(f"  {rank}. {v.name:<12} — {v.rides_taken} rides, {v.meals_eaten} meals")
    print()


if __name__ == "__main__":
    main()
