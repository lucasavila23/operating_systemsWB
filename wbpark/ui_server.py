import os
import queue
import threading
import time

from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit

from .simstate import SimState

_HERE = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = "wbpark-madrid"

# async_mode='threading' avoids eventlet/gevent monkey-patching,
# which would corrupt the simulation's real threading primitives.
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(os.path.join(_HERE, "ui"), "index.html")


# ------------------------------------------------------------------
# WebSocket handlers
# ------------------------------------------------------------------
@socketio.on("connect")
def handle_connect():
    """Send the current snapshot to the newly-connected client."""
    emit("snapshot", SimState.get().get_snapshot())


# ------------------------------------------------------------------
# Background broadcaster
# ------------------------------------------------------------------
def _broadcaster():
    """
    Drains SimState.queue and re-broadcasts each event via WebSocket.
    Throttled to one flush per 200 ms to avoid flooding the browser.
    """
    sim = SimState.get()
    pending: list = []
    last_send = time.time()

    while True:
        try:
            event = sim.queue.get(timeout=0.05)
            pending.append(event)
        except queue.Empty:
            pass

        now = time.time()
        if pending and (now - last_send) >= 0.2:
            for event in pending:
                socketio.emit(event["type"], event)
            pending.clear()
            last_send = now


# ------------------------------------------------------------------
# Entry point called from main.py
# ------------------------------------------------------------------
def start_ui_server(port: int = 5050):
    """
    Launches the Flask-SocketIO server and the broadcaster in daemon
    threads so they never block or outlive the simulation process.
    """
    server = threading.Thread(
        target=lambda: socketio.run(
            app,
            host="0.0.0.0",
            port=port,
            use_reloader=False,
            log_output=False,
            allow_unsafe_werkzeug=True,
        ),
        daemon=True,
        name="UIServer",
    )
    server.start()

    broadcaster = threading.Thread(
        target=_broadcaster,
        daemon=True,
        name="UIBroadcaster",
    )
    broadcaster.start()
