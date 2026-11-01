"""
繪製地圖上的所有東西：角色、燃燒彈、投擲物、彈道、粒子、煙霧、戰爭迷霧、投擲預覽。
"""
import math

import pygame

from config import SW, SH, ZOOM, R, NADES, DARK_ALPHA
from utils import team_col, view_r


class WorldDrawMixin:
    # ---------------- 世界（直接以 ZOOM 縮放後的座標畫在螢幕上）
    def draw_unit(self, u, cx, cy, me, team):
        Z = ZOOM
        x, y = (u.x - cx) * Z, (u.y - cy) * Z
        r = R * Z
        col = team_col(u.team)
        s = self.s
        if not u.alive:
            pygame.draw.circle(s, (70, 50, 40), (x, y), r)
            k = 6 * Z
            pygame.draw.line(s, (40, 30, 25), (x - k, y - k), (x + k, y + k), 3)
            pygame.draw.line(s, (40, 30, 25), (x + k, y - k), (x - k, y + k), 3)
            return
        w = u.weapon
        length = (R + (w["length"] if w else 6)) * Z
        ex, ey = x + math.cos(u.angle) * length, y + math.sin(u.angle) * length
        pygame.draw.line(s, (30, 30, 30), (x, y), (ex, ey), 5 if w and w["length"] > 20 else 4)
        pygame.draw.circle(s, (20, 20, 20), (x, y), r + 2)
        pygame.draw.circle(s, col, (x, y), r)
        pygame.draw.circle(s, tuple(min(255, c + 60) for c in col),
                           (x + math.cos(u.angle) * 3, y + math.sin(u.angle) * 3), 5 * Z)
        if u.uid == me:
            pygame.draw.circle(s, (255, 255, 255), (x, y), r + 3, 2)
            return
        pygame.draw.rect(s, (40, 0, 0), (x - 12, y - r - 9, 24, 4))
        pygame.draw.rect(s, (90, 220, 110) if u.team == team else (230, 60, 50), (x - 12, y - r - 9, 24 * u.hp / 100, 4))
        if not u.bot:
            self.text(u.name, self.f_s, col, (x, y - r - 20), "center")

    def draw_world(self, w, fx, me, mouse):
        Z = ZOOM
        cx, cy = self.cam
        s = self.s
        s.blit(w.map_z, (0, 0), (cx * Z, cy * Z, SW, SH))
        team = self.my_team(w, me)
        vs = self.viewers(w, me)

        if w.fires:
            lay = self.fx_layer
            lay.fill((0, 0, 0, 0))
            t = pygame.time.get_ticks() / 1000
            for f in w.fires:
                fade = max(0.0, min(1.0, (f.DUR - f.age) / 1.0))
                for px, py, ph in f.points:
                    pygame.draw.circle(lay, (40, 20, 10, int(90 * fade)), ((px - cx) * Z, (py - cy) * Z), 16 * Z)
                for px, py, ph in f.points:
                    fl = 0.5 + 0.5 * math.sin(t * 13 + ph * 3)
                    pygame.draw.circle(lay, (255, int(110 + 120 * fl), int(30 * fl), int(220 * fade)),
                                       ((px - cx + math.sin(t * 7 + ph) * 3) * Z, (py - cy - fl * 4) * Z),
                                       (6 + fl * 7) * Z)
            s.blit(lay, (0, 0))

        for kind, nx, ny in w.nades:
            col = {"he": (60, 90, 50), "smoke": (170, 170, 170), "molotov": (200, 80, 30)}[kind]
            pygame.draw.circle(s, (20, 20, 20), ((nx - cx) * Z, (ny - cy) * Z), 6)
            pygame.draw.circle(s, col, ((nx - cx) * Z, (ny - cy) * Z), 4)

        for u in w.units:
            if not u.alive:
                self.draw_unit(u, cx, cy, me, team)
        for u in w.units:
            if u.alive and self.can_see(w, vs, u, team):
                self.draw_unit(u, cx, cy, me, team)

        for x1, y1, x2, y2, life in fx.tracers:
            pygame.draw.line(s, (255, 240, 170), ((x1 - cx) * Z, (y1 - cy) * Z), ((x2 - cx) * Z, (y2 - cy) * Z), 2)
        for x, y, vx, vy, life, mx, col, size in fx.parts:
            pygame.draw.circle(s, col, ((x - cx) * Z, (y - cy) * Z), max(1, size * life / mx * Z))

        if w.smokes:
            sl = self.smoke_layer
            sl.fill((0, 0, 0, 0))
            for sm in w.smokes:
                r = sm.r
                for a, d, size, spin, shade in sm.puffs:
                    aa = a + spin * sm.age
                    pygame.draw.circle(sl, (shade, shade, shade, int(215 * sm.fade)),
                                       ((sm.x + math.cos(aa) * d * r - cx) * Z, (sm.y + math.sin(aa) * d * r - cy) * Z),
                                       size * r / sm.RMAX * Z)
            s.blit(sl, (0, 0))

        if vs is not None:  # 圓形戰爭迷霧（合作時隊友的視野圓合併）
            dk = self.dark
            dk.fill((0, 0, 0, DARK_ALPHA))
            for v in vs:
                target = view_r(v)
                cur = self.fog_r.get(v.uid, target)
                cur += (target - cur) * 0.15
                if abs(cur - target) < 1:
                    cur = target
                self.fog_r[v.uid] = cur
                hole = self.holes[int(target * Z)]
                if cur != target:  # 切槍中：把目標的圓縮放到目前大小
                    rs = int(cur * Z)
                    hole = pygame.transform.scale(hole, (rs * 2, rs * 2))
                hr = hole.get_width() // 2
                dk.blit(hole, ((v.x - cx) * Z - hr, (v.y - cy) * Z - hr), special_flags=pygame.BLEND_RGBA_MIN)
            s.blit(dk, (0, 0))

        p = w.unit(me)
        if p and p.alive and p.slot in NADES and w.s["st"] == "live":
            mx, my = mouse[0] / Z + cx, mouse[1] / Z + cy
            d = min(650, math.hypot(mx - p.x, my - p.y))
            a = math.atan2(my - p.y, mx - p.x)
            for k in range(0, int(d), 18):
                pygame.draw.circle(s, (255, 255, 255), ((p.x + math.cos(a) * k - cx) * Z, (p.y + math.sin(a) * k - cy) * Z), 2)
            pygame.draw.circle(s, (255, 255, 255), ((p.x + math.cos(a) * d - cx) * Z, (p.y + math.sin(a) * d - cy) * Z), 9, 2)
