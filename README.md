English | [Español](README.es.md)

# Theme park concurrency sim

A multithreaded simulation of a day at a theme park, with a live dashboard in the browser. Every visitor, staff member and the clock run as their own thread.

## Context

Group course project, IE University, Operating Systems and Parallel Computing (spring 2026).

## Features

- Visitors choose what to do based on hunger, energy, bladder and one of three personalities: thrill seeker, family or efficient route.
- Rides and restaurant tables have limited capacity, guarded by semaphores. Shared counters and queues are guarded by locks.
- Random events: ride breakdowns, weather, VIP alerts, flash sales and shows. During a breakdown, visitors wait on a condition variable until the ride is repaired.
- A FastPass lane that gives priority boarding on any ride.
- A live dashboard with the park clock, queue lengths, ride status and an event log.
- An end-of-day report with ride, restaurant and restroom counts and the top five riders.

## How it works

| Concept | Where |
|---|---|
| `threading.Semaphore` | Ride slots, restaurant tables, restroom stalls |
| `threading.Lock` / `RLock` | Queues, stat counters, the clock's minute counter |
| `threading.Condition` | Visitors block during a breakdown; `notify_all()` wakes them on repair |
| `threading.Event` | Park-closed signal |
| Daemon threads | Clock, event manager, staff, dashboard server |

Three design patterns: Strategy for visitor personalities (`strategies.py`), Observer for events (`events.py`), and Decorator for FastPass (`fastpass.py`). A Flask-SocketIO server pushes the park state to `wbpark/ui/index.html`.

## Run it

```bash
git clone https://github.com/lucasavila23/theme-park-concurrency-sim.git
cd theme-park-concurrency-sim
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py --visitors 20 --speed 60 --seed 42
```

Open `http://localhost:5050` for the dashboard. `--visitors` sets the number of visitor threads (default 40), `--speed` sets simulated minutes per real second (default 60), and `--seed` makes a run reproducible.

## Stack

Python (threading), Flask, Flask-SocketIO.

## Project structure

```
main.py           entry point and command-line options
wbpark/           simulation package: clock, park, visitors, rides, events, strategies
wbpark/ui/        single-file dashboard
CHANGES.md        notes on the design-pattern refactor
```

## Author

Lucas Avila Manotas · [LinkedIn](https://www.linkedin.com/in/lucas-avila23)
