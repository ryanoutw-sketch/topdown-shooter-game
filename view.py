"""
畫面總管 View：視角（鏡頭跟隨）、可見判定、戰爭迷霧的圓形遮罩。
實際的繪圖分在三個檔案：
  view_world.py  地圖上的東西（角色、火、煙、彈道、迷霧）
  view_hud.py    HUD（血量、彈藥、比分、小地圖、擊殺紀錄、準心）
  view_menus.py  大廳、選槍、結算畫面
"""
import math
import random

import pygame

from config import SW, SH, MW, MH, TILE, ZOOM, VW, VH, WEAPONS, FOG_EDGE, DARK_ALPHA
from utils import font, view_r
from view_hud import HudMixin
from view_menus import MenuMixin
from view_world import WorldDrawMixin


class View(WorldDrawMixin, HudMixin, MenuMixin):
    def __init__(self, screen):
        self.s = screen
        self.smoke_layer = pygame.Surface((SW, SH), pygame.SRCALPHA)
        self.fx_layer = pygame.Surface((SW, SH), pygame.SRCALPHA)
        self.dark = pygame.Surface((SW, SH), pygame.SRCALPHA)
        self.holes = {int(w["view"] * ZOOM): self.make_hole(int(w["view"] * ZOOM)) for w in WEAPONS.values()}
        self.fog_r = {}  # 每個視野來源目前顯示的半徑（切槍時平滑變化）
        self.red = pygame.Surface((SW, SH), pygame.SRCALPHA)
        self.f_s, self.f_m, self.f_l, self.f_xl = font(18), font(24, True), font(40, True), font(64, True)
        self.cam = (0.0, 0.0)

    def text(self, t, f, col, pos, anchor="topleft", shadow=True):
        img = f.render(t, True, col)
        r = img.get_rect(**{anchor: pos})
        if shadow:
            self.s.blit(f.render(t, True, (0, 0, 0)), r.move(2, 2))
        self.s.blit(img, r)
        return r

    # ---------------- 視角 / 視野
    @staticmethod
    def my_team(w, me):
        return w.s["side"][me]

    def camera(self, w, me, mouse, fx):
        u = w.unit(me)
        team = self.my_team(w, me)
        aim = bool(u and u.alive)
        focus = u if aim else None
        if not focus:
            mates = [o for o in w.units if o.alive and not o.bot and o.team == team and o.uid != me]
            focus = mates[0] if mates else u
        fxp, fyp = (focus.x, focus.y) if focus else (MW * TILE / 2, MH * TILE / 2)
        cx = fxp - VW / 2 + ((mouse[0] - SW / 2) / ZOOM * 0.35 if aim else 0)
        cy = fyp - VH / 2 + ((mouse[1] - SH / 2) / ZOOM * 0.35 if aim else 0)
        cx = max(0, min(MW * TILE - VW, cx))
        cy = max(0, min(MH * TILE - VH, cy))
        if fx.shake > 0:
            cx += random.uniform(-fx.shake, fx.shake)
            cy += random.uniform(-fx.shake, fx.shake)
        self.cam = (cx, cy)
        return focus

    def viewers(self, w, me):
        if w.unit(me) is None:
            return None  # 觀戰者看得到全部
        team = self.my_team(w, me)
        vs = [o for o in w.units if o.alive and not o.bot and o.team == team]
        return vs or None

    @staticmethod
    def can_see(w, vs, u, team):
        return vs is None or u.team == team or any(
            math.hypot(u.x - v.x, u.y - v.y) < view_r(v) and w.los(v.x, v.y, u.x, u.y) for v in vs)

    @staticmethod
    def make_hole(rs):
        """視野圓（螢幕半徑 rs）：中間透明、邊緣漸層到全黑。用 BLEND_RGBA_MIN 疊上去，多個圓會自動合併。"""
        hole = pygame.Surface((rs * 2, rs * 2), pygame.SRCALPHA)
        hole.fill((0, 0, 0, DARK_ALPHA))
        for r in range(rs, rs - FOG_EDGE, -1):
            a = int(DARK_ALPHA * (r - (rs - FOG_EDGE)) / FOG_EDGE)
            pygame.draw.circle(hole, (0, 0, 0, a), (rs, rs), r)
        pygame.draw.circle(hole, (0, 0, 0, 0), (rs, rs), rs - FOG_EDGE)
        return hole
