# Design Pattern Refactoring — WB Park Madrid Simulation

## 1. Strategy — Visitor Decision Logic

**What it does in this codebase:**  
Each `Visitor` thread now holds a `DecisionStrategy` instance. When the visitor's main loop calls `_decide()`, execution is delegated entirely to `strategy.decide(visitor, park, clock)`. The three concrete strategies — `ThrillSeekerStrategy`, `FamilyStrategy`, and `EfficientRouteStrategy` — each encode a different personality: thrill-seekers tolerate long queues and score thrill rides higher; family visitors refuse queues over 15 minutes and prefer family/kids/show attractions; efficient visitors always pick the ride with the shortest current wait.

**Files created or modified:**

| File | Change |
|------|--------|
| `wb_park_sim/strategies.py` | **Created.** Defines `DecisionStrategy` ABC, shared helpers `_base_needs_decide` and `_score_base`, and the three concrete strategy classes. |
| `wb_park_sim/visitor.py` | **Modified.** Added `strategy: DecisionStrategy` parameter and `ticket_type` attribute to `__init__`; replaced `_decide()` body with a one-liner delegation; removed `_score()` (logic now lives in strategies). |
| `wb_park_sim/main.py` | **Modified.** Imports the three strategy classes and cycles through them (`i % 3`) when creating visitor threads. |

**Design decisions / trade-offs:**  
- Biological-need priorities (restroom, food, rest) are the same for every personality type and are factored into the shared helper `_base_needs_decide`, avoiding duplication across strategies.
- `_score_base` computes the preference/repeat-penalty portion of scoring but deliberately omits the queue-wait penalty, leaving each strategy free to handle it differently (ThrillSeeker ignores waits ≤ 25 min; FamilyStrategy pre-filters attractions with waits > 15 min before scoring).
- Adding a new visitor personality requires only a new class in `strategies.py`; `Visitor` and `main.py` do not need to know about it.

---

## 2. Observer — Event Dispatch

**What it does in this codebase:**  
`EventManager` now acts as a publisher. Any object can register a listener via `subscribe(event_type, listener)`. When a breakdown event fires, `_notify("breakdown", {"attraction": victim, "duration": duration})` is called instead of invoking `trigger_breakdown` directly. Each `Attraction` (and `FastPassAttraction`) is subscribed as a listener; the listener's `on_event` method checks whether the breakdown targets itself via object identity before acting.

**Files created or modified:**

| File | Change |
|------|--------|
| `wb_park_sim/events.py` | **Modified.** Added `_subscribers` dict, `subscribe()` method, `_notify()` dispatcher, and replaced the direct `victim.trigger_breakdown(duration)` call with `self._notify(...)`. |
| `wb_park_sim/attraction.py` | **Modified.** Added `on_event(event_type, data)` — the Observer callback that calls `trigger_breakdown` only when `data["attraction"] is self`. |
| `wb_park_sim/fastpass.py` | **Created** (see §3). Overrides `on_event` with the same identity check against the wrapper object rather than the inner attraction. |
| `wb_park_sim/main.py` | **Modified.** Keeps the `EventManager` reference before calling `.start()` so that each attraction can be subscribed with `em.subscribe("breakdown", attraction.on_event)`. |

**Design decisions / trade-offs:**  
- Only the `"breakdown"` event type has subscribers that act on it. Weather, VIP, flash sale, and show events remain log-only; they can be promoted to full Observer events later without touching `EventManager`'s dispatch mechanism.
- Identity check (`data["attraction"] is self`) rather than name comparison keeps the coupling minimal and avoids string-based coupling while still being O(1).
- Because `FastPassAttraction` proxies unknown attributes to the wrapped `Attraction`, the `on_event` override in `FastPassAttraction` is necessary: without it, `self` inside the proxied method would be the inner `Attraction`, causing the identity check to fail against the wrapper stored in `park.attractions`.

---

## 3. Decorator — FastPass Queue on Attractions

**What it does in this codebase:**  
`FastPassAttraction` wraps a plain `Attraction` and adds a priority boarding lane. Visitors whose `ticket_type == "fastpass"` (≈20% of visitors, assigned randomly at construction) bypass the regular queue and go straight to acquiring a dedicated `_fastpass_sem` semaphore, then board immediately. All other attributes and methods are transparently proxied to the inner attraction via `__getattr__`. Batman La Fuga and Superman: La Atracción are the two attractions wrapped this way.

**Files created or modified:**

| File | Change |
|------|--------|
| `wb_park_sim/fastpass.py` | **Created.** `FastPassAttraction` class with `__getattr__` proxy, `try_join_queue`, `ride` (branching on `ticket_type`), `estimated_wait` (returns `wrapped // 2`), and `on_event` overrides. |
| `wb_park_sim/visitor.py` | **Modified.** Added `self.ticket_type = "fastpass" if random.random() < 0.20 else "standard"` in `__init__`. |
| `wb_park_sim/park.py` | **Modified.** Imports `FastPassAttraction` and wraps the two high-demand thrill rides at construction time. |

**Design decisions / trade-offs:**  
- `__getattr__` is used (not `__getattribute__`) so only attributes not found on the wrapper itself are proxied. Attributes like `_wrapped`, `fastpass_queue`, and `_fastpass_sem` that are set in `__init__` are accessed directly without triggering the proxy.
- `FastPassAttraction` uses its own `_fastpass_sem` (capacity = wrapped.capacity) rather than sharing the wrapped attraction's `_capacity_sem`. This means FastPass riders and standard riders maintain separate concurrent-rider counts; in a real system both lanes would share physical capacity, but for this simulation the separation keeps the boarding paths independent and avoids cross-lane contention.
- `estimated_wait()` always returns `wrapped.estimated_wait() // 2` regardless of who is asking. This reflects the general perception that FastPass attractions move faster, and avoids the need to thread visitor identity through a method that has no visitor parameter in the base interface.
- FastPass riders do not wait out breakdowns (`is_operational` is checked once; if the ride is down the rider gives up immediately). This is intentional: FastPass privileges include not being stuck in a broken queue.

---

## 4. Real-Time UI

### Architecture

Three layers connect the simulation to a live browser dashboard:

```
Simulation threads
  └─ SimState.get().emit(event_type, data, ts)
        └─ thread-safe queue.Queue
              └─ UIBroadcaster thread (drains queue, throttled 200 ms)
                    └─ Flask-SocketIO → WebSocket → browser
```

**SimState** (`wb_park_sim/simstate.py`) is a double-checked-locking singleton. Any simulation thread calls `emit()` to put an event on the queue and simultaneously update an in-memory snapshot. The snapshot is sent to every new browser connection via a `snapshot` message so the page shows the current state immediately, even mid-run.

**UIServer** (`wb_park_sim/ui_server.py`) runs Flask-SocketIO with `async_mode='threading'` (no eventlet/gevent monkey-patching) in a daemon thread. A second daemon thread, the UIBroadcaster, drains `SimState.queue` in a 50 ms poll loop and flushes batched events via `socketio.emit` at most every 200 ms.

**Frontend** (`wb_park_sim/ui/index.html`) is a single static HTML file served by Flask. It connects via the Socket.IO 4.x CDN. On each incoming event it updates only the affected card — no full re-render. State is maintained locally in a plain JS object `S`.

### Files created

| File | Purpose |
|------|---------|
| `wb_park_sim/simstate.py` | Singleton event bus: thread-safe queue, snapshot, visitor-count tracking |
| `wb_park_sim/ui_server.py` | Flask-SocketIO server + UIBroadcaster daemon threads |
| `wb_park_sim/ui/index.html` | Single-file dashboard: top bar, attraction grid, restaurant side panel, event log |

### Files modified

| File | Change |
|------|--------|
| `wb_park_sim/attraction.py` | Import `SimState`; emit `attraction_state` in `try_join_queue`; emit `breakdown` + `attraction_state` in `trigger_breakdown`; emit `attraction_state` in `_reopen` |
| `wb_park_sim/visitor.py` | Import `SimState`; emit `visitor_state` at the top of `_execute` |
| `wb_park_sim/restaurant.py` | Import `SimState`; emit `restaurant_state` in `eat` after incrementing `_waiting` |
| `wb_park_sim/events.py` | Import `SimState`; emit `event_log` for weather, vip, flash_sale, and show branches in `_fire` |
| `wb_park_sim/main.py` | Import `start_ui_server`; call it (with dashboard URL print) before creating `SimClock` |

### Trade-offs

- **Throttling (200 ms):** The broadcaster batches all events that arrive within a 200 ms window and emits them in one go. This prevents WebSocket flooding during busy simulation ticks while still feeling live to the eye. At `--speed 60` (one sim-minute per real-second) 200 ms is well below the pace of visible change.
- **Singleton pattern:** `SimState` uses double-checked locking so it is safe to import and call from any simulation thread without passing references through the call stack. The trade-off is that it is global state; tests that need isolation must reset `SimState._instance`.
- **Daemon thread lifecycle:** Both the Flask server and the UIBroadcaster threads are `daemon=True`. They are killed automatically when the main simulation thread exits, so no explicit shutdown is needed and the process never hangs.
- **`async_mode='threading'`:** Eventlet is installed (as requested) but Flask-SocketIO is pinned to threading mode to avoid monkey-patching `threading.Semaphore`, `threading.Condition`, and `time.sleep` — all of which are load-bearing OS primitives in the simulation.
