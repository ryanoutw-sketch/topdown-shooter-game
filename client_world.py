"""
畫面端的世界資料：把主機送來的快照轉成可以畫的物件，並預先畫好地圖底圖。
"""
import pygame

from config import WEAPONS, MW, MH, TILE, ZOOM
from grid import MapGrid, Smoke, Fire
from map_art import render_map
from map_data import DEFAULT_MAP


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


class World(MapGrid):
    """收到的快照 → 可以畫的東西。"""

    def __init__(self, map_id=DEFAULT_MAP):
        self.s = None
        self.units, self.nades, self.fires = [], [], []
        super().__init__(map_id)

    def load_map(self, map_id):
        """換地圖：重建格子並重畫底圖、小地圖、縮放後的地圖。"""
        super().load_map(map_id)
        self.map_surf = render_map(self)
        self.mini = pygame.transform.smoothscale(self.map_surf, (MW * 4, MH * 4))
        self.map_z = pygame.transform.smoothscale(self.map_surf, (round(MW * TILE * ZOOM), round(MH * TILE * ZOOM)))
        self._smokes, self._fires = {}, {}
        self.smokes, self.fires = [], []

    def apply(self, snap):
        if snap.get("map", DEFAULT_MAP) != self.map_id:  # 主機換了地圖
            self.load_map(snap.get("map", DEFAULT_MAP))
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
