# ================================================================
#  WB Park Madrid Simulation — Simulation Clock
#
#  OS concepts:
#   · Daemon thread that ticks every simulated minute
#   · RLock protects shared _minute counter (multiple readers)
#   · sleep() converts sim-minutes → real seconds via SIMULATION_SPEED
# ================================================================

import threading
import time
import config


class SimClock:
    """
    Runs in a background daemon thread.
    All other threads call clock.sleep(sim_minutes) instead of
    time.sleep() so that one config knob controls the whole speed.
    """

    def __init__(self):
        self._minute = config.PARK_OPEN_HOUR * 60   # minutes since midnight
        self._lock   = threading.RLock()
        self._stop   = threading.Event()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="SimClock"
        )
        self._thread.start()

    # ----------------------------------------------------------
    # Internal ticker
    # ----------------------------------------------------------
    def _run(self):
        while not self._stop.is_set() and not self.is_closed:
            # Wait one simulated minute in real time
            time.sleep(1.0 / config.SIMULATION_SPEED)
            with self._lock:
                self._minute += 1

    # ----------------------------------------------------------
    # Public read-only properties
    # ----------------------------------------------------------
    @property
    def now(self) -> int:
        """Current sim time as integer minutes since midnight."""
        with self._lock:
            return self._minute

    @property
    def time_str(self) -> str:
        """Human-readable HH:MM string."""
        m = self.now
        return f"{m // 60:02d}:{m % 60:02d}"

    @property
    def is_open(self) -> bool:
        return config.PARK_OPEN_HOUR * 60 <= self.now < config.PARK_CLOSE_HOUR * 60

    @property
    def is_closing_soon(self) -> bool:
        return self.now >= (config.PARK_CLOSE_HOUR * 60 - config.CLOSING_WARN_MIN)

    @property
    def is_closed(self) -> bool:
        return self.now >= config.PARK_CLOSE_HOUR * 60

    # ----------------------------------------------------------
    # Utility
    # ----------------------------------------------------------
    def sleep(self, sim_minutes: float):
        """Block the calling thread for `sim_minutes` of simulated time."""
        time.sleep(max(0.0, sim_minutes / config.SIMULATION_SPEED))

    def stop(self):
        self._stop.set()
