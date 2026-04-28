# WB Park Madrid Simulation

A multithreaded theme-park simulation built to demonstrate Operating Systems and Parallel Computing concepts — semaphores, mutexes, condition variables, daemon threads, and the Observer, Strategy, and Decorator design patterns — with a real-time browser dashboard.

---

## What it simulates

Every entity in the park runs as a Python thread:

| Thread type | Count | Role |
|-------------|-------|------|
| `SimClock` | 1 | Ticks simulated time; converts real seconds to sim-minutes via `--speed` |
| `EventManager` | 1 | Fires random events (breakdowns, weather, VIP alerts, flash sales, shows) |
| `Staff` | 1 per attraction | Periodically checks on the ride; logs status and assists during breakdowns |
| `Visitor` | `--visitors` | Each guest decides what to do next every loop iteration based on hunger, energy, bladder, and preference strategy |

Visitors acquire **Semaphores** to board rides and grab restaurant tables, block on **Conditions** during breakdowns, and share state protected by **Locks**.

---

## Project structure

```
OSPC_WB_Simulation/
├── main.py                  # Entry point — run this
├── requirements.txt
├── .gitignore
├── CHANGES.md               # Design pattern & UI refactoring notes
└── wbpark/                  # Simulation package
    ├── config.py            # All tuneable constants
    ├── clock.py             # SimClock — daemon thread, sim-time control
    ├── logger.py            # Thread-safe colour logger
    ├── simstate.py          # Singleton event bus for the live dashboard
    ├── attraction.py        # Ride / show — Semaphore + Lock + Condition
    ├── fastpass.py          # FastPass decorator — priority boarding lane
    ├── park.py              # Hub: builds all entities, tracks visitor count
    ├── visitor.py           # Visitor thread — state machine + strategy
    ├── restaurant.py        # Restaurant — Semaphore for table slots
    ├── restroom.py          # Restroom — two Semaphores (gendered stalls)
    ├── staff.py             # Staff daemon thread
    ├── events.py            # EventManager — Observer pattern dispatcher
    ├── strategies.py        # ThrillSeeker / Family / EfficientRoute strategies
    ├── ui_server.py         # Flask-SocketIO WebSocket server + broadcaster
    └── ui/
        └── index.html       # Single-file live dashboard (no build step)
```

---

## Setup

```bash
# 1. Clone / enter the project directory
cd OSPC_WB_Simulation

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\activate       # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Running the simulation

```bash
python main.py
```

Then open **http://localhost:5050** in your browser for the live dashboard.

### CLI options

| Flag | Default | Description |
|------|---------|-------------|
| `--visitors N` | `40` | Number of visitor threads |
| `--speed X` | `60` | Sim-minutes per real-second (higher = faster) |
| `--seed N` | random | Fixed seed for reproducible runs |

Examples:

```bash
# Fast demo with 20 visitors, fixed seed
python main.py --visitors 20 --speed 60 --seed 42

# Slow run — watch the dashboard in real time
python main.py --visitors 30 --speed 10

# Very fast — just see the report
python main.py --speed 600
```

---

## Live dashboard

While the simulation runs, open **http://localhost:5050**:

- **Top bar** — sim clock, visitors currently in the park, total rides taken today
- **Attraction cards** — queue bar (blue → orange → red as it fills), OPEN / BROKEN badge, rider count, breakdown count
- **Restaurant panel** — waiting count and total served per outlet
- **Event log** — last 12 events, newest on top; breakdowns in red, announcements in yellow

---

## Design patterns implemented

| Pattern | Where | What it does |
|---------|-------|--------------|
| **Strategy** | `visitor.py` + `strategies.py` | Three visitor personalities (ThrillSeeker, Family, EfficientRoute) that each encode different ride-scoring and queue-tolerance rules |
| **Observer** | `events.py` + `attraction.py` | `EventManager` notifies subscribed attractions of breakdowns via `on_event`; attractions respond by closing and scheduling a repair thread |
| **Decorator** | `fastpass.py` | `FastPassAttraction` wraps any `Attraction` and adds a priority boarding lane; all other attributes proxy transparently to the inner object |

---

## OS concepts demonstrated

| Concept | Where |
|---------|-------|
| `threading.Semaphore` | Ride capacity slots, restaurant table slots, restroom stalls |
| `threading.Lock` | Queue deque protection, stat counters, visitor counter |
| `threading.Condition` | Visitors block during breakdowns; `notify_all()` wakes them on repair |
| `threading.RLock` | SimClock minute counter |
| `threading.Event` | Park closed signal |
| Daemon threads | Clock, EventManager, Staff, UIServer, UIBroadcaster |
| Thread-per-entity | One OS thread per visitor |
