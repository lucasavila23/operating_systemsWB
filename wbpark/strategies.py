# ================================================================
#  WB Park Madrid Simulation — Decision Strategies (Strategy Pattern)
#
#  Each concrete strategy encodes a different visitor personality:
#    · ThrillSeekerStrategy   — favours thrill rides, tolerates long queues
#    · FamilyStrategy         — favours family/kids/show, skips long queues
#    · EfficientRouteStrategy — always picks the shortest wait
# ================================================================

import random
from abc import ABC, abstractmethod

from . import config


class DecisionStrategy(ABC):
    @abstractmethod
    def decide(self, visitor, park, clock) -> tuple:
        """Return an (action_type, target) tuple for the visitor's next action."""
        ...


# ── Shared helpers ────────────────────────────────────────────────────────────

def _base_needs_decide(visitor, park, clock):
    """Priorities 1-3: biological needs shared by every strategy."""
    if visitor.bladder >= config.BLADDER_RESTROOM_THRESHOLD:
        restroom = park.nearest_restroom()
        if restroom:
            return ("restroom", restroom)

    if visitor.hunger >= config.HUNGER_EAT_THRESHOLD:
        restaurant = park.best_restaurant()
        if restaurant:
            return ("eat", restaurant)

    if visitor.energy <= config.ENERGY_REST_THRESHOLD:
        return ("rest", None)

    return None


def _score_base(visitor, attraction) -> float:
    """
    Base attraction score shared by ThrillSeeker and Family strategies.
    Returns -999 for full queues; otherwise: preference + thrill + repeat penalty.
    Queue-wait penalty is left to each strategy.
    """
    if attraction.queue_length >= config.MAX_QUEUE_LENGTH:
        return -999.0

    score = 50.0

    if attraction.type in visitor.preferences:
        score += 25

    if "thrill" in visitor.preferences:
        score += attraction.thrill_level * 3

    score -= visitor.visited.get(attraction.name, 0) * 20

    return score


# ── Concrete strategies ───────────────────────────────────────────────────────

class ThrillSeekerStrategy(DecisionStrategy):
    """
    Loves adrenaline: thrill rides get +30.
    Ignores queue penalties for waits up to 25 sim-min.
    """

    def decide(self, visitor, park, clock) -> tuple:
        result = _base_needs_decide(visitor, park, clock)
        if result:
            return result

        if clock.is_closing_soon:
            short = [a for a in park.attractions if a.is_operational and a.estimated_wait() <= 10]
            if short:
                return ("ride", random.choice(short))
            return ("rest", None)

        candidates = []
        for a in park.attractions:
            if not a.is_operational:
                continue
            score = _score_base(visitor, a)
            if score <= -999:
                continue
            if a.type == "thrill":
                score += 30
            wait = a.estimated_wait()
            if wait > 25:
                score -= (wait - 25) * 0.9
            candidates.append((a, score))

        if not candidates:
            return ("rest", None)

        candidates.sort(key=lambda x: x[1], reverse=True)
        best, best_score = candidates[0]
        if best_score < 0:
            return ("rest", None)
        return ("ride", best)


class FamilyStrategy(DecisionStrategy):
    """
    Prefers family, kids, and show attractions (+30 bonus).
    Refuses to join any queue longer than 15 sim-min.
    """

    def decide(self, visitor, park, clock) -> tuple:
        result = _base_needs_decide(visitor, park, clock)
        if result:
            return result

        if clock.is_closing_soon:
            short = [a for a in park.attractions if a.is_operational and a.estimated_wait() <= 10]
            if short:
                return ("ride", random.choice(short))
            return ("rest", None)

        candidates = []
        for a in park.attractions:
            if not a.is_operational:
                continue
            if a.estimated_wait() > 15:
                continue
            score = _score_base(visitor, a)
            if score <= -999:
                continue
            if a.type in ("family", "kids", "show"):
                score += 30
            score -= a.estimated_wait() * 0.9
            candidates.append((a, score))

        if not candidates:
            return ("rest", None)

        candidates.sort(key=lambda x: x[1], reverse=True)
        best, best_score = candidates[0]
        if best_score < 0:
            return ("rest", None)
        return ("ride", best)


class EfficientRouteStrategy(DecisionStrategy):
    """
    Ignores personal preferences entirely.
    Always picks whichever operational attraction has the shortest current wait.
    """

    def decide(self, visitor, park, clock) -> tuple:
        result = _base_needs_decide(visitor, park, clock)
        if result:
            return result

        if clock.is_closing_soon:
            short = [a for a in park.attractions if a.is_operational and a.estimated_wait() <= 10]
            if short:
                return ("ride", random.choice(short))
            return ("rest", None)

        operational = [
            a for a in park.attractions
            if a.is_operational and a.queue_length < config.MAX_QUEUE_LENGTH
        ]
        if not operational:
            return ("rest", None)

        return ("ride", min(operational, key=lambda a: a.estimated_wait()))
