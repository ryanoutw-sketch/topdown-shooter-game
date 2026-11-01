"""
主機與畫面兩端共用的地圖格子邏輯：碰撞、視線（含煙霧遮擋）、移動，
以及煙霧彈、燃燒彈的區域物件（用 seed 讓兩端產生完全相同的形狀）。
"""
import math
import random

from config import MW, MH, TILE, R
from map_data import FLOORS, CRATES
from utils import seg_point_dist


class MapGrid:
    def __init__(self):
        self.grid = [[1] * MW for _ in range(MH)]
        for x, y, w, h in FLOORS:
            for yy in range(y, y + h):
                for xx in range(x, x + w):
                    self.grid[yy][xx] = 0
        for x, y, w, h in CRATES:
            for yy in range(y, y + h):
                for xx in range(x, x + w):
                    self.grid[yy][xx] = 2
        self.smokes = []

    def tile_solid(self, tx, ty):
        return not (0 <= tx < MW and 0 <= ty < MH) or self.grid[ty][tx] != 0

    def solid(self, x, y):
        return self.tile_solid(int(x // TILE), int(y // TILE))

    def blocked(self, x, y, r=R):
        for tx in range(int((x - r) // TILE), int((x + r) // TILE) + 1):
            for ty in range(int((y - r) // TILE), int((y + r) // TILE) + 1):
                if self.tile_solid(tx, ty):
                    cx = max(tx * TILE, min(x, tx * TILE + TILE))
                    cy = max(ty * TILE, min(y, ty * TILE + TILE))
                    if (x - cx) ** 2 + (y - cy) ** 2 < r * r:
                        return True
        return False

    def los(self, x1, y1, x2, y2, smoke=True):
        d = math.hypot(x2 - x1, y2 - y1)
        n = int(d / 10) + 1
        for i in range(1, n):
            t = i / n
            if self.solid(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t):
                return False
        if smoke:
            for s in self.smokes:
                if s.blocking and seg_point_dist(x1, y1, x2, y2, s.x, s.y) < s.r * 0.85:
                    return False
        return True

    def move_unit(self, u, dx, dy):
        steps = max(1, int(math.hypot(dx, dy) / 6) + 1)
        sx, sy = dx / steps, dy / steps
        moved = 0.0
        for _ in range(steps):
            if not self.blocked(u.x + sx, u.y):
                u.x += sx
                moved += abs(sx)
            if not self.blocked(u.x, u.y + sy):
                u.y += sy
                moved += abs(sy)
        return moved

    def free_tiles(self, rect):
        x, y, w, h = rect
        return [(tx, ty) for ty in range(y, y + h) for tx in range(x, x + w) if self.grid[ty][tx] == 0]


class Smoke:
    DUR, RMAX = 16.0, 125

    def __init__(self, x, y, seed):
        self.x, self.y, self.age, self.id = x, y, 0.0, seed
        rnd = random.Random(seed)
        self.puffs = [(rnd.uniform(0, math.tau), math.sqrt(rnd.random()) * 0.72,
                       rnd.uniform(42, 66), rnd.uniform(-0.3, 0.3), rnd.randint(150, 185))
                      for _ in range(22)]

    @property
    def r(self):
        return self.RMAX * min(1.0, 0.25 + self.age / 1.0)

    @property
    def fade(self):
        return max(0.0, min(1.0, (self.DUR - self.age) / 2.0))

    @property
    def blocking(self):
        return self.age > 0.3 and self.fade > 0.35


class Fire:
    DUR, RAD, DPS = 7.0, 95, 40

    def __init__(self, x, y, owner, grid, seed):
        self.x, self.y, self.owner, self.age, self.id = x, y, owner, 0.0, seed
        rnd = random.Random(seed)
        self.points = []
        for _ in range(90):
            a, d = rnd.uniform(0, math.tau), math.sqrt(rnd.random()) * self.RAD
            px, py = x + math.cos(a) * d, y + math.sin(a) * d
            if not grid.solid(px, py) and grid.los(x, y, px, py, smoke=False):
                self.points.append((px, py, rnd.uniform(0, 6.28)))
