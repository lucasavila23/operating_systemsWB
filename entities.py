import threading
import time
import random


# ---------------------------------------------------------------------------
# Tile — base class
# ---------------------------------------------------------------------------

class Tile(threading.Thread):

    def __init__(self, x, y, capacity):
        super().__init__(daemon=True)
        self.x         = x
        self.y         = y
        self.capacity  = capacity
        self.semaphore = threading.Semaphore(capacity)
        self.is_open   = False
        self._stop     = threading.Event()

    def open(self):
        self.is_open = True

    def close(self):
        self.is_open = False

    def stop(self):
        self._stop.set()

    def run(self):
        while not self._stop.is_set():
            time.sleep(0.1)


# ---------------------------------------------------------------------------
# Road — visitors walk through this
# ---------------------------------------------------------------------------

class Road(Tile):

    def __init__(self, x, y):
        super().__init__(x, y, capacity=10)


# ---------------------------------------------------------------------------
# EmptyTile — impassable cell
# ---------------------------------------------------------------------------

class EmptyTile(Tile):

    def __init__(self, x, y):
        super().__init__(x, y, capacity=0)


# ---------------------------------------------------------------------------
# ServiceTile — a tile that serves visitors
# ---------------------------------------------------------------------------

class ServiceTile(Tile):

    def __init__(self, x, y, capacity):
        super().__init__(x, y, capacity)
        self.queue = []
        self.lock  = threading.Lock()

    def enqueue(self, visitor):
        acquired = self.semaphore.acquire(blocking=False)
        if acquired:
            with self.lock:
                self.queue.append(visitor)
            return True
        return False

    def dequeue(self):
        with self.lock:
            if self.queue:
                self.semaphore.release()
                return self.queue.pop(0)
        return None

    def serve(self):
        visitor = self.dequeue()
        if visitor:
            time.sleep(random.uniform(1, 3))

    def run(self):
        while not self._stop.is_set():
            if self.is_open:
                self.serve()
            else:
                time.sleep(0.1)


# ---------------------------------------------------------------------------
# Concrete service tiles
# ---------------------------------------------------------------------------

class Attraction(ServiceTile):
    def __init__(self, x, y, name, capacity=50):
        super().__init__(x, y, capacity)
        self.name = name

    def serve(self):
        visitor = self.dequeue()
        if visitor:
            print(f"  {visitor} riding {self.name}")
            time.sleep(random.uniform(2, 5))


class Restaurant(ServiceTile):
    def __init__(self, x, y, name, capacity=30):
        super().__init__(x, y, capacity)
        self.name = name

    def serve(self):
        visitor = self.dequeue()
        if visitor:
            print(f"  {visitor} eating at {self.name}")
            time.sleep(random.uniform(1, 3))


class ParkEntrance(ServiceTile):
    def __init__(self, x, y, capacity=20):
        super().__init__(x, y, capacity)

    def serve(self):
        visitor = self.dequeue()
        if visitor:
            visitor.in_park = True
            print(f"  {visitor} entered the park")
            time.sleep(0.5)


class Exit(ServiceTile):
    def __init__(self, x, y, capacity=50):
        super().__init__(x, y, capacity)

    def serve(self):
        visitor = self.dequeue()
        if visitor:
            visitor.in_park = False
            print(f"  {visitor} left the park")
            time.sleep(0.2)


# ---------------------------------------------------------------------------
# Visitor
# ---------------------------------------------------------------------------

class Visitor(threading.Thread):

    def __init__(self, visitor_id):
        super().__init__(daemon=True)
        self.visitor_id = visitor_id
        self.in_park    = False
        self._stop      = threading.Event()

    def stop(self):
        self._stop.set()

    def __repr__(self):
        return f"Visitor({self.visitor_id})"


# ---------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------

class Grid:

    def __init__(self, width, height):
        self.width  = width
        self.height = height
        self.tiles  = [
            [EmptyTile(x, y) for y in range(height)]
            for x in range(width)
        ]

    def set_tile(self, x, y, tile):
        self.tiles[x][y] = tile

    def get_tile(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[x][y]
        return None

    def start_all(self):
        for col in self.tiles:
            for tile in col:
                tile.open()
                tile.start()

    def stop_all(self):
        for col in self.tiles:
            for tile in col:
                tile.stop()
