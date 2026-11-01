"""
選單畫面：大廳（模式/難度/玩家）、選槍畫面、整場結算、訊息畫面。
"""
import pygame

from config import SW, SH, MW, MH, WIN_ROUNDS, WEAPONS, PRIMARIES, DIFFS, MODE_NAMES, CT_COL, T_COL
from utils import team_col


class MenuMixin:
    # ---------------- 選單畫面
    def lobby(self, S, me, is_host, mouse, ip, port):
        s = self.s
        s.fill((22, 20, 18))
        self.text("2D TOP DOWN SHOOTING GAME", self.f_xl, (230, 190, 90), (SW // 2, 80), "center")
        self.text("雙人連線版", self.f_m, (220, 220, 220), (SW // 2, 135), "center")
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
                self.text(f"{k} {d['name']}（{d['bots']} 個 NPC）", self.f_s, (240, 240, 240), r.center, "center")
                acts.append((r, ("diff", k)))
            self.text("合作模式 NPC 已減弱（傷害 65%、反應較慢、槍法較差）· 兩人合作時 NPC 會多 2 個",
                      self.f_s, (170, 170, 170), (SW // 2, 330), "center")
        else:
            self.text("每回合交換攻守：防守方在上方出生，進攻方在下方出生", self.f_s, (170, 170, 170), (SW // 2, 287), "center")

        y = 380
        for uid in (0, 1):
            connected = uid == 0 or S["conn"]
            label = f"{S['names'][uid]}{'（主機）' if uid == 0 else ''}{'  ← 你' if uid == me else ''}"
            pygame.draw.rect(s, (30, 32, 40), (SW // 2 - 300, y, 600, 48), border_radius=8)
            pygame.draw.circle(s, (90, 220, 110) if connected else (110, 110, 110), (SW // 2 - 270, y + 24), 8)
            self.text(label if connected else "等待玩家 2 連線…", self.f_m, (235, 235, 235), (SW // 2 - 245, y + 24), "midleft")
            y += 60
        if is_host:
            self.text(f"對方執行：py cs_online.py --join {ip}    （port {port}）", self.f_m, (230, 200, 90), (SW // 2, 530), "center")
            hint = "M 切換模式 · 1/2/3 難度 · Enter 開始 · ESC 離開"
            if S["mode"] == "coop" and not S["conn"]:
                hint = "M 切換模式 · 1/2/3 難度 · Enter 單人開始（或等玩家 2）· ESC 離開"
        else:
            hint = "已連線，等待主機開始…  ·  ESC 離開"
        self.text(hint, self.f_m, (210, 210, 210), (SW // 2, 590), "center")
        if S.get("notice"):
            self.text(S["notice"], self.f_m, (255, 110, 90), (SW // 2, 650), "center")
        return acts

    def buy_menu(self, w, me, mouse, my_pick):
        s, S = self.s, w.s
        s.blit(pygame.transform.smoothscale(w.map_surf, (SW, int(SW * MH / MW))), (0, -100))
        ov = pygame.Surface((SW, SH), pygame.SRCALPHA)
        ov.fill((10, 12, 18, 215))
        s.blit(ov, (0, 0))
        team = S["side"][me]
        self.text(f"第 {S['round'] + 1} 回合 — 選擇主武器", self.f_xl, (240, 240, 240), (SW // 2, 60), "center")
        if S["mode"] == "coop":
            sub = f"比分  防守方（你們） {S['score'][0]} : {S['score'][1]} 進攻方（NPC）"
        else:
            role = "防守方（上方出生）" if team == "CT" else "進攻方（下方出生）"
            sub = f"比分  你 {S['score'][me]} : {S['score'][1 - me]} 對手      本回合你是 {role}"
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
            stats = [("傷害", min(1.0, wp["dmg"] * wp["pellets"] / 120)), ("射速", min(1.0, 0.07 / wp["rate"])),
                     ("精準", 1 - min(1.0, (wp["spread"] + wp["move"] * 0.3) / 0.11)), ("機動", (wp["speed"] - 170) / 80),
                     ("視野", (wp["view"] - 380) / 480)]
            sx = r.x + 270
            for name, v in stats:
                self.text(name, self.f_s, (180, 180, 180), (sx, r.centery), "midleft", shadow=False)
                pygame.draw.rect(s, (60, 60, 70), (sx + 42, r.centery - 5, 66, 10))
                pygame.draw.rect(s, (110, 200, 120) if name != "視野" else (110, 170, 240),
                                 (sx + 42, r.centery - 5, 66 * max(0.05, min(1.0, v)), 10))
                sx += 114
            rects.append(r)
        status = []
        for uid in S["humans"]:
            done = uid in S["picks"] or (uid == me and my_pick)
            status.append(f"{S['names'][uid]} {'✔ 已選' if done else '… 選擇中'}")
        self.text("    ".join(status), self.f_m, (230, 230, 230), (SW // 2, SH - 78), "center")
        self.text("視野依手上的槍決定（拿投擲物時看主武器）· 附帶 USP-S、高爆、煙霧、燃燒彈各一 · 按 1–5 或點擊選擇",
                  self.f_s, (200, 200, 200), (SW // 2, SH - 36), "center")
        return rects

    def over(self, S, me, is_host):
        s = self.s
        s.fill((15, 15, 18))
        if S["mode"] == "coop":
            won = S["score"][0] >= WIN_ROUNDS
            a, b = S["score"]
        else:
            won = S["score"][me] >= WIN_ROUNDS
            a, b = S["score"][me], S["score"][1 - me]
        self.text("勝利！" if won else "戰敗", self.f_xl, CT_COL if won else T_COL, (SW // 2, 200), "center")
        self.text(f"最終比分  {a} : {b}", self.f_l, (230, 230, 230), (SW // 2, 290), "center")
        y = 360
        for uid in S["humans"]:
            k, d = S["stats"][uid]
            self.text(f"{S['names'][uid]}    擊殺 {k}   陣亡 {d}", self.f_m, (210, 210, 210), (SW // 2, y), "center")
            y += 40
        hint = "Enter 再來一場 · ESC 回大廳" if is_host else "等待主機決定是否再來一場…"
        self.text(hint, self.f_m, (200, 200, 200), (SW // 2, 520), "center")

    def message(self, lines):
        self.s.fill((22, 20, 18))
        for i, ln in enumerate(lines):
            self.text(ln, self.f_l if i == 0 else self.f_m, (235, 235, 235), (SW // 2, SH // 2 - 40 + i * 56), "center")
