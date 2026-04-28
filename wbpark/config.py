# ================================================================
#  WB Park Madrid Simulation — Configuration
# ================================================================

# --- Simulation speed ---
# 1 real second = SIMULATION_SPEED simulated seconds
# 60  → 1 real min  = 1 sim hour  (fast, good for testing)
# 120 → 1 real min  = 2 sim hours (very fast)
SIMULATION_SPEED = 60

# --- Park hours (24-h) ---
PARK_OPEN_HOUR  = 10   # 10:00
PARK_CLOSE_HOUR = 22   # 22:00
CLOSING_WARN_MIN = 60  # "closing soon" threshold (sim minutes before close)

# --- Visitors ---
NUM_VISITORS         = 40
ARRIVAL_WINDOW_MIN   = 90   # visitors trickle in over this many sim-minutes

# --- Need thresholds (scale 0-100) ---
HUNGER_EAT_THRESHOLD      = 70
BLADDER_RESTROOM_THRESHOLD = 80
ENERGY_REST_THRESHOLD     = 25
ENERGY_EXIT_THRESHOLD     = 10

# --- Passive need rates (per sim-minute) ---
HUNGER_RATE  = 0.25
BLADDER_RATE = 0.18
ENERGY_IDLE  = 0.10   # energy lost while walking / exploring

# --- One-time energy costs / restores ---
ENERGY_COST_RIDE    = 8
ENERGY_RESTORE_REST = 20
ENERGY_RESTORE_EAT  = 12
HUNGER_RESTORE_EAT  = 65
BLADDER_RESTORE_WC  = 75

# --- Queue / capacity ---
MAX_QUEUE_LENGTH     = 30   # visitors won't join a longer queue
QUEUE_PATIENCE_MIN   = 20   # sim-minutes a visitor waits before giving up

# --- Travel (sim-minutes between locations) ---
TRAVEL_TIME_MIN = 1
TRAVEL_TIME_MAX = 6
