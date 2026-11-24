"""
繪製地圖上的所有東西：角色、燃燒彈、投擲物、彈道、粒子、煙霧、戰爭迷霧、投擲預覽。
"""
import math

import pygame

from config import SW, SH, ZOOM, R, NADES, FOG_EDGE, DARK_ALPHA, FLASH_MAX, FLASH_WHITE
from utils import team_col, view_r


class WorldDrawMixin:
    @staticmethod
    def _local_layer(radius):
        """Create a transparent surface limited to one local effect."""
        radius = max(1, int(math.ceil(radius)))
        size = radius * 2 + 2
        layer = pygame.Surface((size, size), pygame.SRCALPHA, 32)
        layer.fill((0, 0, 0, 0))
        return layer, radius + 1

    def _draw_fire(self, fire, cx, cy, now):
        Z = ZOOM
        radius = fire.RAD * Z + 22
        layer, offset = self._local_layer(radius)
        fade = max(0.0, min(1.0, (fire.DUR - fire.age) / 1.0))
        for px, py, ph in fire.points:
            pygame.draw.circle(
                layer,
                (40, 20, 10, int(90 * fade)),
                (offset + int((px - fire.x) * Z), offset + int((py - fire.y) * Z)),
                max(1, int(16 * Z)),
            )
        for px, py, ph in fire.points:
            fl = 0.5 + 0.5 * math.sin(now * 13 + ph * 3)
            pygame.draw.circle(
                layer,
                (255, int(110 + 120 * fl), int(30 * fl), int(220 * fade)),
                (
                    offset + int((px - fire.x + math.sin(now * 7 + ph) * 3) * Z),
                    offset + int((py - fire.y - fl * 4) * Z),
                ),
                max(1, int((6 + fl * 7) * Z)),
            )
        self.s.blit(
            layer,
            (int((fire.x - cx) * Z - offset), int((fire.y - cy) * Z - offset)),
            special_flags=pygame.BLEND_ALPHA_SDL2,
        )

    def _draw_smoke(self, smoke, cx, cy):
        Z = ZOOM
        # Puffs extend beyond the nominal smoke radius, so leave extra room.
        radius = smoke.r * 1.3 * Z + 2
        layer, offset = self._local_layer(radius)
        for angle, distance, size, spin, shade in smoke.puffs:
            a = angle + spin * smoke.age
            px = math.cos(a) * distance * smoke.r
            py = math.sin(a) * distance * smoke.r
            pygame.draw.circle(
                layer,
                (shade, shade, shade, int(215 * smoke.fade)),
                (offset + int(px * Z), offset + int(py * Z)),
                max(1, int(size * smoke.r / smoke.RMAX * Z)),
            )
        self.s.blit(
            layer,
            (int((smoke.x - cx) * Z - offset), int((smoke.y - cy) * Z - offset)),
            special_flags=pygame.BLEND_ALPHA_SDL2,
        )

    def draw_fog(self, viewers, cx, cy):
        """圓形戰爭迷霧（跨平台、快速版）。

        直接在半透明黑幕上用 pygame.draw.circle 畫 alpha=0 的圓「挖洞」：
        draw.circle 是直接寫入像素、不經過混色，所以不需要 BLEND_RGBA_MIN
        （該模式在部分 macOS SDL 上不可靠），也不需要每幀做整個畫面的 mask 轉換。
        邊緣漸層：所有視野圓一起「由外往內、alpha 由大到小」畫同心圓，
        兩個圓重疊的地方會保留較透明的值，所以合作模式的視野會正確合併。
        """
        Z = ZOOM
        circles = []
        for v in viewers:
            target = view_r(v)
            cur = self.fog_r.get(v.uid, target)
            cur += (target - cur) * 0.15
            if abs(cur - target) < 1:
                cur = target
            self.fog_r[v.uid] = cur
            circles.append(((int((v.x - cx) * Z), int((v.y - cy) * Z)), max(1, int(cur * Z))))

        fade = max(0.0, min(1.0, self.pan_k))
        dark_alpha = int(DARK_ALPHA * fade)
        dk = self.dark
        dk.fill((0, 0, 0, dark_alpha))
        edge = max(0, int(FOG_EDGE))
        for k in range(edge, 0, -1):  # 外圈 → 內圈，alpha 遞減
            a = int(dark_alpha * k / (edge + 1))
            for c, r in circles:
                pygame.draw.circle(dk, (0, 0, 0, a), c, max(1, r - edge + k))
        for c, r in circles:
            pygame.draw.circle(dk, (0, 0, 0, 0), c, max(1, r - edge))
        self.s.blit(dk, (0, 0), special_flags=pygame.BLEND_ALPHA_SDL2)

    # ---------------- 世界（直接以 ZOOM 縮放後的座標畫在螢幕上）
    def draw_flash(self, w, fx, me):
        """被閃光彈閃到：整個畫面直接全白，最後一段時間才淡出（閃得越久，全白越久）。"""
        p = w.unit(me)
        if not p or not p.alive or p.flash <= 0:
            fx.flash_peak = 0.0
            return
        if p.flash > fx.flash_peak:  # 新被閃（或被閃得更久）
            fx.flash_peak = p.flash
        fade = min(FLASH_MAX - FLASH_WHITE, fx.flash_peak * 0.6)  # 淡出時間
        a = min(1.0, p.flash / max(0.05, fade))
        if a >= 1.0:
            self.s.fill((255, 255, 255))
            return
        if not hasattr(self, "white"):
            self.white = pygame.Surface((SW, SH), pygame.SRCALPHA)
        self.white.fill((255, 255, 255, int(255 * a)))
        self.s.blit(self.white, (0, 0), special_flags=pygame.BLEND_ALPHA_SDL2)

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
            # Fire is rendered only inside its own local alpha surface.
            t = pygame.time.get_ticks() / 1000
            for fire in w.fires:
                self._draw_fire(fire, cx, cy, t)

        for kind, nx, ny in w.nades:
            col = {"he": (60, 90, 50), "smoke": (170, 170, 170), "molotov": (200, 80, 30), "flash": (235, 235, 210)}.get(kind, (200, 200, 200))
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
            for smoke in w.smokes:
                self._draw_smoke(smoke, cx, cy)

        if vs is not None:  # 圓形戰爭迷霧（合作時隊友的視野圓合併）
            self.draw_fog(vs, cx, cy)

        p = w.unit(me)
        if p and p.alive and p.slot in NADES and w.s["st"] == "live":
            mx, my = mouse[0] / Z + cx, mouse[1] / Z + cy
            d = min(650, math.hypot(mx - p.x, my - p.y))
            a = math.atan2(my - p.y, mx - p.x)
            for k in range(0, int(d), 18):
                pygame.draw.circle(s, (255, 255, 255), ((p.x + math.cos(a) * k - cx) * Z, (p.y + math.sin(a) * k - cy) * Z), 2)
            pygame.draw.circle(s, (255, 255, 255), ((p.x + math.cos(a) * d - cx) * Z, (p.y + math.sin(a) * d - cy) * Z), 9, 2)
