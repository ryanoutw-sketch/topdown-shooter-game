"""
選單畫面：大廳（模式/難度/玩家）、選槍畫面、訊息畫面。（整場結算畫面在 anim.py）
"""
import pygame

from config import SW, SH, MW, MH, WEAPONS, PRIMARIES, DIFFS, MODE_NAMES
from utils import team_col


class MenuMixin:
    # ---------------- 選單畫面
    def lobby(self, S, me, is_host, mouse, ip, port):
        s = self.s
        s.fill((22, 20, 18))
        self.text("2D TOP DOWN SHOOTING GAME", self.f_xl, (230, 190, 90), (SW // 2, 80), "center")
        self.text("2-PLAYER ONLINE", self.f_m, (220, 220, 220), (SW // 2, 135), "center")
        acts = []
        for i, m in enumerate(("coop", "pvp")):
            r = pygame.Rect(SW // 2 - 410 + i * 420, 180, 400, 64)
            sel = S["mode"] == m
            pygame.draw.rect(s, (60, 66, 84) if sel else (34, 36, 44), r, border_radius=10)
            if sel:
                pygame.draw.rect(s, (230, 200, 90), r, 2, border_radius=10)
            self.text(MODE_NAMES[m], self.f_m, (240, 240, 240), r.center, "center")
            acts.append((r, ("mode", m)))
        if S["mode"] == "coop":
            for i, k in enumerate((1, 2, 3)):
                d = DIFFS[k]
                r = pygame.Rect(SW // 2 - 410 + i * 280, 262, 260, 50)
                sel = S["diff"] == k
                pygame.draw.rect(s, (60, 66, 84) if sel else (34, 36, 44), r, border_radius=10)
                if sel:
                    pygame.draw.rect(s, (230, 200, 90), r, 2, border_radius=10)
                self.text(f"{k}  {d['name']}  ({d['bots']} NPCs)", self.f_s, (240, 240, 240), r.center, "center")
                acts.append((r, ("diff", k)))
            self.text("Co-op NPCs are weakened (65% damage, slower reactions, worse aim) · 2 extra NPCs with two players",
                      self.f_s, (170, 170, 170), (SW // 2, 330), "center")
        else:
            self.text("Sides swap every round: Defenders spawn at the top, Attackers at the bottom", self.f_s, (170, 170, 170), (SW // 2, 287), "center")

        y = 380
        for uid in (0, 1):
            connected = uid == 0 or S["conn"]
            label = f"{S['names'][uid]}{' (Host)' if uid == 0 else ''}{'  ← You' if uid == me else ''}"
            pygame.draw.rect(s, (30, 32, 40), (SW // 2 - 300, y, 600, 48), border_radius=8)
            pygame.draw.circle(s, (90, 220, 110) if connected else (110, 110, 110), (SW // 2 - 270, y + 24), 8)
            self.text(label if connected else "Waiting for Player 2…", self.f_m, (235, 235, 235), (SW // 2 - 245, y + 24), "midleft")
            y += 60
        if is_host:
            self.text(f"Other player runs:  py topdown_shooter.py --join {ip}    (port {port})", self.f_m, (230, 200, 90), (SW // 2, 530), "center")
            hint = "M Switch mode · 1/2/3 Difficulty · Enter Start · ESC Quit"
            if S["mode"] == "coop" and not S["conn"]:
                hint = "M Switch mode · 1/2/3 Difficulty · Enter Start solo (or wait for P2) · ESC Quit"
        else:
            hint = "Connected — waiting for the host to start…  ·  ESC Quit"
        self.text(hint, self.f_m, (210, 210, 210), (SW // 2, 590), "center")
        if S.get("notice"):
            self.text(S["notice"], self.f_m, (255, 110, 90), (SW // 2, 650), "center")
        return acts

    def buy_menu(self, w, me, mouse, my_pick):
        s, S = self.s, w.s
        bg = getattr(self, "_buy_bg", None)
        if bg is None:  # 背景（縮小的地圖＋暗色遮罩）只畫一次，之後重複使用
            bg = pygame.Surface((SW, SH), 0, 32, (16711680, 65280, 255, 0))
            bg.fill((10, 12, 18))
            bg.blit(pygame.transform.smoothscale(w.map_surf, (SW, int(SW * MH / MW))), (0, -100))
            ov = pygame.Surface((SW, SH), pygame.SRCALPHA)
            ov.fill((10, 12, 18, 215))
            bg.blit(ov, (0, 0), special_flags=pygame.BLEND_ALPHA_SDL2)
            self._buy_bg = bg
        s.blit(bg, (0, 0))
        team = S["side"][me]
        self.text(f"Round {S['round'] + 1} — Choose Your Primary", self.f_xl, (240, 240, 240), (SW // 2, 60), "center")
        if S["mode"] == "coop":
            sub = f"Score  Defenders (you) {S['score'][0]} : {S['score'][1]} Attackers (NPC)"
        else:
            role = "Defenders (top spawn)" if team == "CT" else "Attackers (bottom spawn)"
            sub = f"Score  You {S['score'][me]} : {S['score'][1 - me]} Opponent      This round: {role}"
        self.text(sub, self.f_m, team_col(team), (SW // 2, 118), "center")
        rects = []
        for i, key in enumerate(PRIMARIES):
            wp = WEAPONS[key]
            r = pygame.Rect(SW // 2 - 420, 160 + i * 80, 840, 68)
            hover = r.collidepoint(mouse)
            pygame.draw.rect(s, (55, 65, 90) if hover else (28, 32, 42), r, border_radius=10)
            if key == my_pick:
                pygame.draw.rect(s, (230, 200, 90), r, 3, border_radius=10)
            self.text(f"{i + 1}", self.f_l, (230, 200, 90), (r.x + 36, r.centery), "center")
            self.text(wp["name"], self.f_m, (240, 240, 240), (r.x + 70, r.centery), "midleft")
            stats = [("Dmg", min(1.0, wp["dmg"] * wp["pellets"] / 120)), ("Rate", min(1.0, 0.07 / wp["rate"])),
                     ("Aim", 1 - min(1.0, (wp["spread"] + wp["move"] * 0.3) / 0.11)), ("Move", (wp["speed"] - 170) / 80),
                     ("View", (wp["view"] - 380) / 480)]
            # stats 起點：武器名結束後至少留 16px，且不低於固定欄位寬度。
            # 每一組的血條都接在實際文字寬度後面，避免固定間距蓋住標籤。
            name_end = r.x + 70 + self.f_m.size(wp["name"])[0]
            sx = max(r.x + 270, name_end + 16)
            bar_w = 54
            for name, v in stats:
                label = self.text(name, self.f_s, (180, 180, 180), (sx, r.centery), "midleft", shadow=False)
                bar_x = label.right + 6
                pygame.draw.rect(s, (60, 60, 70), (bar_x, r.centery - 5, bar_w, 10))
                pygame.draw.rect(s, (110, 200, 120) if name != "View" else (110, 170, 240),
                                 (bar_x, r.centery - 5, bar_w * max(0.05, min(1.0, v)), 10))
                sx = bar_x + bar_w + 6
            rects.append(r)
        status = []
        for uid in S["humans"]:
            done = uid in S["picks"] or (uid == me and my_pick)
            status.append(f"{S['names'][uid]} {'✔ Ready' if done else '… Choosing'}")
        self.text("    ".join(status), self.f_m, (230, 230, 230), (SW // 2, SH - 78), "center")
        self.text("Vision depends on the gun in hand (grenades use your primary) · Includes USP-S, HE, Smoke, Molotov · Press 1–5 or click",
                  self.f_s, (200, 200, 200), (SW // 2, SH - 36), "center")
        return rects

    def message(self, lines):
        self.s.fill((22, 20, 18))
        for i, ln in enumerate(lines):
            self.text(ln, self.f_l if i == 0 else self.f_m, (235, 235, 235), (SW // 2, SH // 2 - 40 + i * 56), "center")
