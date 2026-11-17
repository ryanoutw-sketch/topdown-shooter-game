"""
遊戲中的 HUD：小地圖、比分與時間、擊殺紀錄、血量、武器欄、彈藥、準心、回合結束橫幅。
"""
import math

import pygame

from config import SW, SH, MW, MH, TILE, ZOOM, WIN_ROUNDS, WEAPONS, SLOTS, NADES, NADE_NAMES, TEAM_NAMES, CT_COL, T_COL
from utils import team_col


class HudMixin:
    # ---------------- HUD
    def draw_hud(self, w, fx, me, mouse, focus):
        s, S = self.s, w.s
        p = w.unit(me)
        team = self.my_team(w, me)
        enemy = "T" if team == "CT" else "CT"
        vs = self.viewers(w, me)
        if fx.hurt > 0:
            self.red.fill((200, 0, 0, int(90 * fx.hurt)))
            s.blit(self.red, (0, 0))

        # 小地圖
        s.blit(w.mini, (12, 12))
        pygame.draw.rect(s, (0, 0, 0), (12, 12, MW * 4, MH * 4), 2)
        k = 4 / TILE
        for sm in w.smokes:
            pygame.draw.circle(s, (200, 200, 200), (12 + sm.x * k, 12 + sm.y * k), sm.r * k)
        for f in w.fires:
            pygame.draw.circle(s, (255, 120, 30), (12 + f.x * k, 12 + f.y * k), f.RAD * k)
        for u in w.units:
            if u.alive and self.can_see(w, vs, u, team):
                col = (255, 255, 255) if u.uid == me else team_col(u.team)
                pygame.draw.circle(s, col, (12 + u.x * k, 12 + u.y * k), 4 if u.uid == me or not u.bot else 3)

        # 比分（左邊永遠是自己這邊）
        if S["mode"] == "coop":
            mine, theirs = S["score"][0], S["score"][1]
        else:
            mine, theirs = S["score"][me], S["score"][1 - me]
        tm = max(0, int(S["timer"]))
        bx = SW // 2
        pygame.draw.rect(s, (20, 20, 25), (bx - 130, 8, 260, 52), border_radius=8)
        self.text(str(mine), self.f_l, team_col(team), (bx - 95, 34), "center")
        self.text(str(theirs), self.f_l, team_col(enemy), (bx + 95, 34), "center")
        self.text(f"{tm // 60}:{tm % 60:02d}", self.f_l, (255, 80, 80) if tm < 15 else (240, 240, 240), (bx, 34), "center")
        foes = [u for u in w.units if u.team == enemy]
        alive = sum(1 for u in foes if u.alive)
        for i in range(len(foes)):
            pygame.draw.circle(s, team_col(enemy) if i < alive else (70, 70, 70), (bx + (i - (len(foes) - 1) / 2) * 18, 72), 6)
        side_txt = "" if S["mode"] == "coop" else f"  ·  Your team: {TEAM_NAMES[team]}"
        self.text(f"Round {S['round']}  ·  First to {WIN_ROUNDS} wins{side_txt}", self.f_s, (220, 220, 220), (bx, 92), "center")

        # 擊殺紀錄
        y = 14
        for kn, kt, wn, vn, vt, life in reversed(S["feed"]):
            imgs = [self.f_s.render(kn, True, team_col(kt)), self.f_s.render(f"  [{wn}]  ", True, (230, 230, 230)),
                    self.f_s.render(vn, True, team_col(vt))]
            wsum = sum(i.get_width() for i in imgs)
            x = SW - 14 - wsum
            pygame.draw.rect(s, (0, 0, 0), (x - 8, y - 3, wsum + 16, 28), border_radius=5)
            for i in imgs:
                s.blit(i, (x, y))
                x += i.get_width()
            y += 32

        if p is None:
            self.text("Spectating — you'll join next round", self.f_m, (240, 240, 240), (SW // 2, SH - 40), "center")
        elif not p.alive:
            who = f"watching {focus.name}" if focus and focus is not p and focus.alive else "waiting for the round to end"
            self.text(f"You died — {who}", self.f_m, (240, 240, 240), (SW // 2, SH - 40), "center")
        else:
            self.draw_player_hud(p, fx, mouse)

        if S["st"] == "end":
            if S["mode"] == "coop":
                big = "Defenders win" if S["rw"] else "Attackers win"
                col = CT_COL if S["rw"] else T_COL
            else:
                big = "Draw" if S["rw"] < 0 else ("You won the round" if S["rw"] == me else "Opponent won the round")
                col = (230, 230, 230) if S["rw"] < 0 else (CT_COL if S["rw"] == me else T_COL)
            pygame.draw.rect(s, (0, 0, 0), (0, SH // 2 - 80, SW, 130))
            self.text(big, self.f_xl, col, (SW // 2, SH // 2 - 30), "center")
            self.text(S["reason"], self.f_m, (220, 220, 220), (SW // 2, SH // 2 + 25), "center")

    def draw_player_hud(self, p, fx, mouse):
        s = self.s
        pygame.draw.rect(s, (20, 20, 25), (14, SH - 64, 230, 50), border_radius=8)
        self.text("+", self.f_l, (90, 230, 120) if p.regen else (240, 240, 240), (36, SH - 39), "center")
        if p.regen:
            self.text("Regenerating", self.f_s, (90, 230, 120), (130, SH - 66), "midleft")
        self.text(str(int(math.ceil(p.hp))), self.f_l, (240, 240, 240) if p.hp > 30 else (255, 70, 70), (60, SH - 39), "midleft")
        pygame.draw.rect(s, (60, 60, 60), (130, SH - 44, 100, 10))
        pygame.draw.rect(s, (90, 220, 110) if p.hp > 30 else (240, 70, 60), (130, SH - 44, p.hp, 10))

        labels = {"primary": WEAPONS[p.primary]["name"], "pistol": WEAPONS["pistol"]["name"] if "pistol" in WEAPONS else "",
                  "he": f"HE x{p.nades['he']}", "smoke": f"Smoke x{p.nades['smoke']}",
                  "molotov": f"Molotov x{p.nades['molotov']}"}
        x = SW // 2 - (len(SLOTS) * 134 - 6) // 2
        for i, sl in enumerate(SLOTS):
            sel = sl == p.slot
            empty = sl in NADES and p.nades[sl] <= 0
            r = pygame.Rect(x, SH - 46, 128, 34)
            pygame.draw.rect(s, (60, 70, 90) if sel else (20, 20, 25), r, border_radius=6)
            if sel:
                pygame.draw.rect(s, (220, 220, 240), r, 2, border_radius=6)
            self.text(f"{i + 1} {labels[sl]}", self.f_s, (110, 110, 110) if empty else (235, 235, 235), r.center, "center")
            x += 134

        w = p.weapon
        pygame.draw.rect(s, (20, 20, 25), (SW - 230, SH - 64, 216, 50), border_radius=8)
        if w:
            self.text(f"{p.mag}", self.f_l, (240, 240, 240) if p.mag else (255, 70, 70), (SW - 150, SH - 39), "midright")
            self.text(f"/ {p.res}", self.f_m, (170, 170, 170), (SW - 140, SH - 39), "midleft")
            if p.rl > 0:
                pygame.draw.rect(s, (60, 60, 60), (SW - 222, SH - 20, 200, 4))
                pygame.draw.rect(s, (240, 200, 80), (SW - 222, SH - 20, 200 * (1 - p.rl), 4))
                self.text("Reloading…", self.f_m, (240, 200, 80), (SW // 2, SH // 2 + 60), "center")
        else:
            self.text(NADE_NAMES[p.slot], self.f_m, (240, 240, 240), (SW - 122, SH - 39), "center")

        mx, my = mouse
        if w:
            dist = math.hypot(mx / ZOOM + self.cam[0] - p.x, my / ZOOM + self.cam[1] - p.y)
            gap = max(4, math.tan(p.spread()) * dist * ZOOM)
            col = (80, 255, 120)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = (mx + dx * gap, my + dy * gap), (mx + dx * (gap + 10), my + dy * (gap + 10))
                pygame.draw.line(s, (0, 0, 0), a, b, 4)
                pygame.draw.line(s, col, a, b, 2)
            pygame.draw.circle(s, col, (mx, my), 1)
        else:
            pygame.draw.circle(s, (255, 255, 255), (mx, my), 4, 1)
        if fx.hitmark > 0:
            for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                pygame.draw.line(s, (255, 255, 255), (mx + dx * 6, my + dy * 6), (mx + dx * 13, my + dy * 13), 2)
