# ================================================================
#  WB Park Madrid Simulation — Thread-safe Coloured Logger
#
#  OS concepts:
#   · threading.Lock ensures log lines never interleave
# ================================================================

import threading

_lock = threading.Lock()

# ANSI colours
_C = {
    "visitor":    "\033[96m",   # cyan
    "staff":      "\033[93m",   # yellow
    "attraction": "\033[92m",   # green
    "restaurant": "\033[95m",   # magenta
    "restroom":   "\033[94m",   # blue
    "event":      "\033[91m",   # red
    "park":       "\033[97m",   # white
}
_RESET = "\033[0m"
_BOLD  = "\033[1m"


def log(entity_type: str, name: str, message: str, clock=None):
    colour   = _C.get(entity_type, "")
    time_tag = f"[{clock.time_str}] " if clock else ""
    with _lock:
        print(f"{colour}{_BOLD}{time_tag}[{name}]{_RESET}{colour} {message}{_RESET}")
