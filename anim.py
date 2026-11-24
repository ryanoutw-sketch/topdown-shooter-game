"""
畫面動畫（只在畫面端執行，不影響遊戲判定）：
  入場標題動畫、畫面切換的圓形收合、回合開始的橫幅與 3-2-1 倒數、
  回合結束的電影黑邊與勝負橫幅、整場結算的彩帶與數字累加。
回合開始的凍結時間與回合結束的慢動作由主機計時、放在快照裡，所以兩端會同步。
所有長度都在 config.py 的「動畫」區。
"""
import math
import random

import pygame

from config import SW, SH, WIN_ROUNDS, INTRO_TIME, IRIS_TIME, FREEZE_TIME, CT_COL, T_COL, TEAM_NAMES
from map_data import spawn_where
from utils import font, team_col, text_surface, fit_width

GOLD = (240, 200, 90)
INK = (8, 8, 12)


# ---------------- 緩動函數（t 從 0 到 1）
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease_out_cubic(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in_cubic(t):
    t = clamp(t)
    return t ** 3


def ease_in_out(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_out_back(t, s=1.7):
    t = clamp(t) - 1
    return 1 + t * t * ((s + 1) * t + s)


class Animator:
    def __init__(self, view, sounds):
        self.v = view
        self.s = view.s
        self.snd = sounds
        self.t = self.dt = 0.0
        self.intro_on, self.intro_t, self.intro_played = True, 0.0, set()
        self.iris = None  # (開始時間, 切換前最後一張畫面)
        self.overlay = pygame.Surface((SW, SH), pygame.SRCALPHA)
        self.band = pygame.Surface((SW, 230), pygame.SRCALPHA)
        self.prev_st = None
        self.prev_freeze = 0.0
        self.prev_count = None
        self.go_t = self.banner_t = self.over_t = None
        self.end_t0 = 0.0
        self.score_before = [0, 0]
        self.confetti = []
        self.f_huge, self.f_big, self.f_title = font(150, True), font(84, True), font(62, True)
        self.f_l, self.f_m, self.f_s = font(40, True), font(24, True), font(18)

    # ---------------- 共用
    def play(self, name):
        s = self.snd.get(name)
        if s:
            s.play()

    def tick(self, dt):
        self.dt = dt
        self.t += dt
        if self.intro_on:
            self.intro_t += dt

    def text(self, txt, fnt, col, center, alpha=1.0, scale=1.0, shadow=True):
        if alpha <= 0.01 or scale <= 0.01:
            return
        img = fit_width(text_surface(fnt, txt, col), SW - 40)   # 字型較寬的電腦上不超出畫面
        sh = fit_width(text_surface(fnt, txt, (0, 0, 0)), SW - 40) if shadow else None
        if scale != 1.0:
            size = (max(1, int(img.get_width() * scale)), max(1, int(img.get_height() * scale)))
            img = pygame.transform.smoothscale(img, size)
            sh = pygame.transform.smoothscale(sh, size) if sh else None
        if alpha < 1.0:
            img.set_alpha(int(255 * alpha))
            if sh:
                sh.set_alpha(int(200 * alpha))
        r = img.get_rect(center=(int(center[0]), int(center[1])))
        if sh:
            self.s.blit(sh, r.move(3, 3), special_flags=pygame.BLEND_ALPHA_SDL2)
        self.s.blit(img, r, special_flags=pygame.BLEND_ALPHA_SDL2)

    # ---------------- 圓形收合轉場
    def start_iris(self):
        self.iris = (self.t, self.s.copy())

    def draw_iris(self):
        if not self.iris:
            return
        t0, old = self.iris
        e = (self.t - t0) / IRIS_TIME
        if e >= 1:
            self.iris = None
            return
        R0 = math.hypot(SW, SH) / 2 + 10
        if e < 0.5:  # 前半：舊畫面上的圓收合到全黑
            self.s.blit(old, (0, 0))
            r = R0 * (1 - ease_in_cubic(e / 0.5))
        else:        # 後半：新畫面從中心的圓打開
            r = R0 * ease_out_cubic((e - 0.5) / 0.5)
        ov = self.overlay
        ov.fill((*INK, 255))
        if r > 1:
            pygame.draw.circle(ov, (0, 0, 0, 0), (SW // 2, SH // 2), int(r))
        self.s.blit(ov, (0, 0), special_flags=pygame.BLEND_ALPHA_SDL2)
        if 3 < r < R0 - 4:
            pygame.draw.circle(self.s, GOLD, (SW // 2, SH // 2), int(r), 3)

    # ---------------- 入場動畫
    def skip_intro(self):
        if self.intro_on:
            self.intro_on = False
            self.start_iris()

    def draw_intro(self, world):
        s, t = self.s, self.intro_t
        once = self.intro_played
        # 背景：地圖緩慢平移、壓暗
        px = 300 + t * 45
        s.blit(world.map_surf, (0, 0), (px, 260 + t * 12, SW, SH))
        self.overlay.fill((*INK, 205))
        s.blit(self.overlay, (0, 0), special_flags=pygame.BLEND_ALPHA_SDL2)

        cx, cy = SW // 2, SH // 2 - 30
        title = text_surface(self.f_title, "2D TOP DOWN SHOOTING GAME", GOLD)
        tw, th = title.get_size()
        tx, ty = cx - tw // 2, cy - th // 2

        # 準心：從大圈收到標題周圍
        k = ease_out_cubic((t - 0.1) / 1.6)
        rr = int(620 - 360 * k)
        a = int(110 * clamp(t / 0.4))
        ring = (*GOLD, a)
        self.overlay.fill((0, 0, 0, 0))
        pygame.draw.circle(self.overlay, ring, (cx, cy), rr, 2)
        for i in range(4):
            ang = i * math.pi / 2 + t * 0.5
            p1 = (cx + math.cos(ang) * (rr - 18), cy + math.sin(ang) * (rr - 18))
            p2 = (cx + math.cos(ang) * (rr + 22), cy + math.sin(ang) * (rr + 22))
            pygame.draw.line(self.overlay, ring, p1, p2, 3)
        s.blit(self.overlay, (0, 0), special_flags=pygame.BLEND_ALPHA_SDL2)

        # 彈道從左射到右，經過的地方「劃開」出標題
        hx = -120 + (SW + 400) * ease_out_cubic((t - 0.35) / 0.75)
        if t > 0.3 and "whoosh" not in once:
            once.add("whoosh")
            self.play("whoosh")
        reveal = int(clamp(hx - tx, 0, tw))
        if reveal > 0:
            sh = text_surface(self.f_title, "2D TOP DOWN SHOOTING GAME", (0, 0, 0))
            s.blit(sh, (tx + 4, ty + 4), (0, 0, reveal, th), special_flags=pygame.BLEND_ALPHA_SDL2)
            s.blit(title, (tx, ty), (0, 0, reveal, th), special_flags=pygame.BLEND_ALPHA_SDL2)
        if -100 < hx < SW + 300 and t < 1.3:
            for i in range(12):
                seg = 26
                x2 = hx - i * seg
                c = int(255 * (1 - i / 12))
                pygame.draw.line(s, (255, 230 * c // 255 + 25, 140 * c // 255), (x2, cy), (x2 - seg, cy), 4 if i < 3 else 2)
            pygame.draw.circle(s, (255, 250, 220), (int(hx), cy), 6)
        # 標題完全出現：撞擊閃光
        done_t = 0.35 + 0.75 * 0.55
        if t > done_t and "impact" not in once:
            once.add("impact")
            self.play("impact")
        flash = 1 - clamp((t - done_t) / 0.35)
        if t > done_t and flash > 0:
            self.overlay.fill((255, 245, 220, int(120 * flash)))
            s.blit(self.overlay, (0, 0), special_flags=pygame.BLEND_ALPHA_SDL2)

        # 副標題與提示
        sub_a = clamp((t - 1.2) / 0.4)
        self.text("2 - P L A Y E R   O N L I N E", self.f_m, (225, 225, 235), (cx, cy + 62), sub_a)
        self.text("Press any key to skip", self.f_s, (150, 150, 160), (cx, SH - 34), 0.4 + 0.3 * math.sin(t * 4), shadow=False)
        if t >= INTRO_TIME:
            self.skip_intro()

    # ---------------- 每幀依快照更新（偵測狀態切換、倒數音效）
    def update(self, S):
        st = S["st"]
        if self.prev_st is not None and st != self.prev_st and not (self.prev_st == "live" and st == "end"):
            self.start_iris()
        if st != self.prev_st:
            if st == "live":
                self.score_before = list(S["score"])
                self.go_t, self.prev_count = None, None
            elif st == "end":
                self.end_t0, self.banner_t = self.t, None
            elif st == "over":
                self.over_t = self.t
                self.confetti = []
        self.prev_st = st
        if st == "live":
            f = S.get("freeze", 0)
            if f > 0:
                n = math.ceil(f)
                if n != self.prev_count:
                    self.prev_count = n
                    self.play("beep")
            elif self.prev_freeze > 0:
                self.go_t = self.t
                self.play("go")
            self.prev_freeze = f
        else:
            self.prev_freeze = 0.0

    def pan_k(self, S):
        """回合開始時鏡頭從地圖中央平移到自己身上的進度（0→1）。"""
        if S["st"] != "live" or S.get("freeze", 0) <= 0:
            return 1.0
        e = FREEZE_TIME - S["freeze"]
        return ease_in_out((e - 0.45) / 1.4)  # 等圓形轉場打開後才開始掃

    def scores(self, S, me, score=None):
        sc = score or S["score"]
        if S["mode"] == "coop":
            return (sc[0], sc[1]), (CT_COL, T_COL)
        team = S["side"][me]
        enemy = "T" if team == "CT" else "CT"
        return (sc[me], sc[1 - me]), (team_col(team), team_col(enemy))

    # ---------------- 回合開始：橫幅 + 3-2-1 + 開始！
    def draw_round_start(self, S, me):
        f = S.get("freeze", 0)
        if f > 0:
            e = FREEZE_TIME - f
            k_in = ease_out_cubic((e - 0.15) / 0.45)
            k_out = ease_in_cubic((e - 2.35) / 0.4)
            if k_in > 0 and k_out < 1:
                off = -SW * (1 - k_in) + SW * k_out
                team = S["side"][me]
                col = team_col(team)
                self.band.fill((10, 10, 16, 200))
                self.s.blit(self.band, (off, 104), (0, 0, SW, 170), special_flags=pygame.BLEND_ALPHA_SDL2)
                pygame.draw.rect(self.s, col, (off, 104, SW, 4))
                pygame.draw.rect(self.s, col, (off, 270, SW, 4))
                (a, b), _ = self.scores(S, me)
                if S["mode"] == "coop":
                    sub = f"Defenders · Hold off every attacker      Score {a} : {b}"
                else:
                    where = f"{spawn_where(S.get('map'), team)} spawn"
                    sub = f"Your team: {TEAM_NAMES[team]} ({where})      Score {a} : {b}"
                self.text(f"ROUND {S['round']}", self.f_big, (245, 245, 250), (SW / 2 + off, 170))
                self.text(sub, self.f_m, col, (SW / 2 + off, 238))
            n = math.ceil(f)
            frac = 1 - (f - (n - 1))  # 這一秒的進度 0→1
            sc = 1 + 0.9 * (1 - ease_out_back(frac / 0.35))
            alpha = 1 - clamp((frac - 0.75) / 0.25)
            self.text(str(n), self.f_huge, GOLD, (SW / 2, SH / 2 + 110), alpha, sc)
        elif self.go_t is not None and self.t - self.go_t < 0.9:
            k = (self.t - self.go_t) / 0.9
            a = 1 - ease_in_cubic((k - 0.5) / 0.5)
            sc = 0.6 + 0.55 * ease_out_back(k * 2.2)
            self.text("GO!", self.f_huge, (20, 14, 6), (SW / 2 + 5, SH / 2 + 115), a * 0.8, sc, shadow=False)
            self.text("GO!", self.f_huge, (255, 228, 120), (SW / 2, SH / 2 + 110), a, sc)

    # ---------------- 回合結束：電影黑邊 + 勝負橫幅 + 比分跳動
    def draw_end(self, S, me):
        s = self.s
        h = int(58 * ease_out_cubic((self.t - self.end_t0) / 0.4))
        if h > 0:
            pygame.draw.rect(s, (0, 0, 0), (0, 0, SW, h))
            pygame.draw.rect(s, (0, 0, 0), (0, SH - h, SW, h))
        if S.get("slow", 0) > 0:
            return
        if self.banner_t is None:
            self.banner_t = self.t
            if S["mode"] == "coop":
                self.play("round_win" if S["rw"] else "round_lose")
            elif S["rw"] < 0:
                self.play("beep")
            else:
                self.play("round_win" if S["rw"] == me else "round_lose")
        bt = self.t - self.banner_t
        if S["mode"] == "coop":
            big = "Defenders win" if S["rw"] else "Attackers win"
            col = CT_COL if S["rw"] else T_COL
        else:
            big = "Draw" if S["rw"] < 0 else ("You won the round" if S["rw"] == me else "Opponent won the round")
            col = (230, 230, 230) if S["rw"] < 0 else (CT_COL if S["rw"] == me else T_COL)
        k = ease_out_cubic(bt / 0.45)
        w = int(SW * k)
        y0 = SH // 2 - 125
        self.band.fill((10, 10, 16, 220))
        s.blit(self.band, (0, y0), (0, 0, w, 230), special_flags=pygame.BLEND_ALPHA_SDL2)
        pygame.draw.rect(s, col, (0, y0, w, 4))
        pygame.draw.rect(s, col, (SW - w, y0 + 226, w, 4))
        ta = clamp((bt - 0.15) / 0.3)
        self.text(big, self.f_big, col, (SW / 2, y0 + 62), ta)
        self.text(S["reason"], self.f_m, (215, 215, 220), (SW / 2, y0 + 126), ta)
        # 比分：先顯示舊比分，再讓變動的那邊跳成新數字
        (na, nb), (ca, cb) = self.scores(S, me)
        (oa, ob), _ = self.scores(S, me, self.score_before)
        pop = bt > 0.55
        popk = 1 + 0.8 * (1 - ease_out_cubic((bt - 0.55) / 0.35)) if pop else 1.0
        ya = y0 + 182
        self.text(":", self.f_title, (230, 230, 230), (SW / 2, ya - 4), ta)
        self.text(str(na if pop else oa), self.f_title, GOLD if pop and na != oa else ca,
                  (SW / 2 - 70, ya), ta, popk if na != oa else 1.0)
        self.text(str(nb if pop else ob), self.f_title, GOLD if pop and nb != ob else cb,
                  (SW / 2 + 70, ya), ta, popk if nb != ob else 1.0)

    # ---------------- 整場結算：標題彈出、彩帶、數字累加
    def draw_over(self, S, me, is_host):
        s = self.s
        ot = self.t - (self.over_t if self.over_t is not None else self.t)
        if S["mode"] == "coop":
            won = S["score"][0] >= WIN_ROUNDS
        else:
            won = S["score"][me] >= WIN_ROUNDS
        if not self.confetti and ot < 0.1:
            self.play("fanfare" if won else "defeat")
            if won:
                cols = [GOLD, CT_COL, T_COL, (120, 220, 140), (235, 235, 245)]
                self.confetti = [[random.uniform(0, SW), random.uniform(-SH, -20), random.uniform(-40, 40),
                                  random.uniform(80, 200), random.uniform(0, 6.28), random.uniform(-6, 6),
                                  random.choice(cols), random.uniform(6, 12)] for _ in range(170)]
            else:
                self.confetti = [None]  # 標記已播過音效
        s.fill((12, 12, 16))
        for c in self.confetti:
            if c is None:
                continue
            c[0] += (c[2] + math.sin(self.t * 2 + c[4]) * 30) * self.dt
            c[1] += c[3] * self.dt
            c[4] += c[5] * self.dt
            if c[1] > SH + 20:
                c[1] = random.uniform(-80, -20)
            w, h = c[7], c[7] * 0.45 * abs(math.cos(c[4]))
            pts = [(c[0] + dx * math.cos(c[4] * 0.5) - dy * math.sin(c[4] * 0.5),
                    c[1] + dx * math.sin(c[4] * 0.5) + dy * math.cos(c[4] * 0.5))
                   for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]
            pygame.draw.polygon(s, c[6], pts)
        self.text("VICTORY!" if won else "DEFEAT", self.f_big, CT_COL if won else T_COL, (SW / 2, 190),
                  1.0, max(0.01, ease_out_back(ot / 0.6)))
        (a, b), _ = self.scores(S, me)
        self.text(f"Final Score  {a} : {b}", self.f_l, (230, 230, 230), (SW / 2, 290), clamp((ot - 0.4) / 0.4))
        k = ease_out_cubic((ot - 0.7) / 1.0)
        for i, uid in enumerate(S["humans"]):
            kills, deaths = S["stats"][uid]
            line = f"{S['names'][uid]}    Kills {round(kills * k)}   Deaths {round(deaths * k)}"
            self.text(line, self.f_m, (210, 210, 215), (SW / 2, 360 + i * 42), clamp((ot - 0.6 - i * 0.15) / 0.3))
        hint = "Enter Play again · ESC Lobby" if is_host else "Waiting for the host to start a rematch…"
        self.text(hint, self.f_m, (200, 200, 205), (SW / 2, 520), clamp((ot - 1.6) / 0.4) * (0.7 + 0.3 * math.sin(self.t * 3)))
