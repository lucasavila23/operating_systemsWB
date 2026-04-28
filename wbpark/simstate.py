import queue
import threading


class SimState:
    """
    Singleton event bus shared by all simulation threads.
    Callers call SimState.get().emit(...) from any thread.
    ui_server drains the queue and broadcasts via WebSocket.
    """

    _instance = None
    _init_lock = threading.Lock()

    @classmethod
    def get(cls) -> "SimState":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.queue: queue.Queue = queue.Queue()

        self._snap_lock = threading.Lock()
        self._attractions: dict = {}     # name → last attraction_state dict
        self._restaurants: dict = {}     # name → last restaurant_state dict
        self._visitor_states: dict = {}  # visitor name → state string
        self._visitor_count: int = 0

    # ------------------------------------------------------------------
    # Emit — called from simulation threads
    # ------------------------------------------------------------------
    def emit(self, event_type: str, data: dict, ts: str = ""):
        """
        Put an event on the queue so ui_server can broadcast it.
        Also updates the internal snapshot so new connections see current state.
        """
        event_data = dict(data)

        with self._snap_lock:
            if event_type == "attraction_state":
                self._attractions[data["name"]] = {**data, "ts": ts}

            elif event_type == "restaurant_state":
                self._restaurants[data["name"]] = {**data, "ts": ts}

            elif event_type == "visitor_state":
                name = data["name"]
                old  = self._visitor_states.get(name, "")
                new  = data["state"]
                self._visitor_states[name] = new

                _active = {
                    "arriving", "exploring", "queueing",
                    "riding", "eating", "restroom", "resting",
                }
                if new in _active and old not in _active:
                    self._visitor_count += 1
                elif new not in _active and old in _active:
                    self._visitor_count -= 1

                event_data["visitor_count"] = self._visitor_count

        self.queue.put({"type": event_type, "ts": ts, "data": event_data})

    # ------------------------------------------------------------------
    # Snapshot — returned to newly-connected browser clients
    # ------------------------------------------------------------------
    def get_snapshot(self) -> dict:
        with self._snap_lock:
            return {
                "attractions": list(self._attractions.values()),
                "restaurants": list(self._restaurants.values()),
                "visitor_count": self._visitor_count,
                "total_riders": sum(
                    a.get("total_riders", 0) for a in self._attractions.values()
                ),
            }
