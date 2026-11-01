"""
畫面端的世界資料：把主機送來的快照轉成可以畫的物件，並預先畫好地圖底圖。
"""
import random

import pygame

from config import WEAPONS, MW, MH, TILE, ZOOM
from grid import MapGrid, Smoke, Fire
from map_data import CT_SPAWN, T_SPAWN


class VUnit:
    def __init__(self, a):
        (self.uid, self.name, self.team, bot, self.x, self.y, self.angle, self.hp, alive, self.primary, self.slot,
         self.mag, self.res, self.rl, he, sm, mo, self.moving, self.recoil, self.regen) = a
        self.bot, self.alive = bool(bot), bool(alive)
        self.nades = {"he": he, "smoke": sm, "molotov": mo}

    @property
    def weapon(self):
        if self.slot == "primary":
            return WEAPONS[self.primary]
        if self.slot == "pistol":
            return WEAPONS["pistol"]
        return None

    def spread(self):
        w = self.weapon
        return w["spread"] + w["move"] * self.moving + self.recoil


def render_map(g):
    surf = pygame.Surface((MW * TILE, MH * TILE))
    rnd = random.Random(42)
    for ty in range(MH):
        for tx in range(MW):
            r = pygame.Rect(tx * TILE, ty * TILE, TILE, TILE)
            k = g.grid[ty][tx]
            if k == 0:
                v = rnd.randint(-8, 8)
                surf.fill((196 + v, 172 + v, 124 + v), r)
                pygame.draw.rect(surf, (184, 160, 114), r, 1)
            elif k == 1:
                surf.fill((112, 92, 68), r)
            else:
                surf.fill((150, 108, 60), r)
                pygame.draw.rect(surf, (95, 65, 35), r.inflate(-4, -4), 3)
                pygame.draw.line(surf, (95, 65, 35), r.topleft, r.bottomright, 3)
                pygame.draw.line(surf, (95, 65, 35), r.topright, r.bottomleft, 3)
    for ty in range(MH):
        for tx in range(MW):
            if g.grid[ty][tx] == 0:
                x, y = tx * TILE, ty * TILE
                if g.tile_solid(tx, ty - 1):
                    pygame.draw.rect(surf, (160, 138, 96), (x, y, TILE, 7))
                if g.tile_solid(tx - 1, ty):
                    pygame.draw.rect(surf, (172, 150, 106), (x, y, 5, TILE))
            elif g.grid[ty][tx] == 1 and not g.tile_solid(tx, ty + 1):
                pygame.draw.rect(surf, (90, 72, 52), (tx * TILE, ty * TILE + TILE - 6, TILE, 6))
    tint = pygame.Surface((MW * TILE, MH * TILE), pygame.SRCALPHA)
    for rect, col in ((CT_SPAWN, (70, 130, 255, 22)), (T_SPAWN, (255, 130, 40, 22))):
        x, y, w, h = rect
        tint.fill(col, (x * TILE, y * TILE, w * TILE, h * TILE))
    surf.blit(tint, (0, 0))
    return surf


class World(MapGrid):
    """收到的快照 → 可以畫的東西。"""

    def __init__(self):
        super().__init__()
        self.map_surf = render_map(self)
        self.mini = pygame.transform.smoothscale(self.map_surf, (MW * 4, MH * 4))
        self.map_z = pygame.transform.smoothscale(self.map_surf, (round(MW * TILE * ZOOM), round(MH * TILE * ZOOM)))
        self.s = None
        self.units, self.nades, self.fires = [], [], []
        self._smokes, self._fires = {}, {}

    def apply(self, snap):
        self.s = snap
        self.units = [VUnit(a) for a in snap["u"]]
        self.nades = snap["n"]
        sm = {}
        for sid, x, y, age in snap["sm"]:
            o = self._smokes.get(sid) or Smoke(x, y, sid)
            o.age = age
            sm[sid] = o
        self._smokes = sm
        self.smokes = list(sm.values())
        fi = {}
        for fid, x, y, age in snap["fi"]:
            o = self._fires.get(fid) or Fire(x, y, None, self, fid)
            o.age = age
            fi[fid] = o
        self._fires = fi
        self.fires = list(fi.values())

    def unit(self, uid):
        for u in self.units:
            if u.uid == uid:
                return u
        return None
