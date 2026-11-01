"""
2D Top Down Shooting Game — 單機版 — 與 NPC 對戰 (Python + pygame)

安裝:  py -m pip install pygame
執行:  py cs_offline.py

操作:
  WASD 移動 / Shift 靜步（更準）/ 滑鼠瞄準 / 左鍵射擊或投擲
  1 主武器  2 手槍  3 高爆手榴彈  4 煙霧彈  5 燃燒彈  滾輪切換  Q 切回上一把
  R 換彈  ESC 回主選單
規則:
  你是防守方，在上方出生；NPC 是進攻方，從下方進攻。
  殲滅所有敵人或撐過回合時間即勝，先拿 5 回合獲勝。
  煙霧會擋住視線（敵我都看不到），也能撲滅燃燒彈的火。
"""
import heapq
import math
import random
from array import array

import pygame

SW, SH = 1280, 720
FPS = 60
TILE = 40
MW, MH = 50, 38
ROUND_TIME = 115
WIN_ROUNDS = 5
R = 13  # 角色半徑

# ------------------------------------------------------------------ 地圖（類 Dust2）
FLOORS = [
    (19, 2, 12, 6),   # CT 出生點
    (12, 3, 7, 4),    # CT → B
    (2, 2, 10, 11),   # B 點
    (31, 3, 5, 4),    # CT → A
    (36, 2, 12, 11),  # A 點
    (23, 8, 4, 20),   # 中路
    (19, 25, 4, 4),   # T 坡道 → 中路
    (18, 29, 14, 7),  # T 出生點
    (32, 31, 12, 3),  # A 大道（橫）
    (40, 13, 4, 18),  # A 大道（直）
    (38, 26, 8, 7),   # A 大門
    (27, 15, 7, 3),   # 中路 → A 小道
    (31, 11, 3, 4),
    (31, 10, 5, 3),
    (6, 30, 12, 3),   # B 洞（橫）
    (5, 13, 4, 20),   # B 洞（直）
    (9, 19, 14, 3),   # 中門 → B
    (3, 22, 7, 5),    # B 洞內室
]
CRATES = [(39, 5, 2, 2), (44, 8, 2, 2), (37, 10, 1, 1), (4, 5, 2, 2), (8, 9, 2, 2), (24, 17, 1, 1),
          (41, 22, 1, 1), (22, 31, 2, 1), (28, 33, 1, 2), (21, 4, 1, 1), (28, 5, 2, 1), (6, 24, 1, 1),
          (42, 28, 2, 1),
          (23, 9, 2, 1), (26, 9, 1, 1)]  # 中門：只留一格門縫
CT_SPAWN = (19, 2, 12, 6)
T_SPAWN = (19, 30, 12, 5)
ROUTES = [
    [(37, 32), (41, 24), (41, 15), (41, 7)],          # A 大道
    [(25, 25), (30, 16), (32, 12), (39, 9)],          # 中路轉 A 小道
    [(12, 31), (7, 27), (7, 16), (7, 7)],             # B 洞
    [(25, 25), (25, 12), (25, 5)],                    # 中路直衝 CT
    [(25, 25), (15, 20), (7, 15), (6, 7)],            # 中門轉 B
]

# ------------------------------------------------------------------ 武器
WEAPONS = {
    "pistol": dict(name="USP-S 手槍", dmg=34, rate=0.17, mag=12, res=48, reload=1.6, spread=0.012,
                   move=0.05, recoil=0.03, speed=245, pellets=1, range=1400, auto=False, snd="shot", length=14),
    "smg": dict(name="MP7 衝鋒槍", dmg=24, rate=0.075, mag=30, res=120, reload=2.0, spread=0.03,
                move=0.035, recoil=0.012, speed=238, pellets=1, range=1200, auto=True, snd="shot", length=18),
    "m4": dict(name="M4A4 步槍", dmg=32, rate=0.092, mag=30, res=90, reload=2.4, spread=0.007,
               move=0.10, recoil=0.017, speed=218, pellets=1, range=2200, auto=True, snd="rifle", length=22),
    "ak": dict(name="AK-47 步槍", dmg=38, rate=0.1, mag=30, res=90, reload=2.5, spread=0.009,
               move=0.12, recoil=0.025, speed=212, pellets=1, range=2200, auto=True, snd="rifle", length=22),
    "shotgun": dict(name="Nova 霰彈槍", dmg=17, rate=0.85, mag=8, res=32, reload=2.8, spread=0.10,
                    move=0.03, recoil=0.0, speed=222, pellets=9, range=650, auto=False, snd="shotgun", length=20),
    "awp": dict(name="AWP 狙擊槍", dmg=115, rate=1.45, mag=5, res=30, reload=3.6, spread=0.0015,
                move=0.28, recoil=0.0, speed=185, pellets=1, range=2800, auto=False, snd="awp", length=28),
}
PRIMARIES = ["smg", "m4", "ak", "shotgun", "awp"]
NADE_NAMES = {"he": "高爆手榴彈", "smoke": "煙霧彈", "molotov": "燃燒彈"}
SLOTS = ["primary", "pistol", "he", "smoke", "molotov"]

DIFFS = {
    1: dict(name="簡單", bots=3, react=(0.6, 1.0), err=0.06, turn=4.0, burst=(3, 5)),
    2: dict(name="普通", bots=5, react=(0.35, 0.65), err=0.035, turn=6.0, burst=(4, 7)),
    3: dict(name="困難", bots=5, react=(0.18, 0.38), err=0.017, turn=9.0, burst=(5, 9)),
}
BOT_NAMES = ["Gus", "Kilo", "Raven", "Vex", "Bishop", "Nomad", "Sable"]

CT_COL = (80, 140, 235)
T_COL = (225, 140, 55)


def font(size, bold=False):
    return pygame.font.SysFont(
        "microsoftjhenghei,microsoftjhengheiui,microsoftyahei,pmingliu,notosanscjktc,notosanscjksc,"
        "notosanscjk,wenquanyizenhei,arialunicodems,arial", size, bold=bold)


def ang_diff(a, b):
    return (b - a + math.pi) % math.tau - math.pi


def seg_point_dist(x1, y1, x2, y2, px, py):
    dx, dy = x2 - x1, y2 - y1
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L))
    return math.hypot(x1 + dx * t - px, y1 + dy * t - py)


def tile_center(t):
    return t[0] * TILE + TILE / 2, t[1] * TILE + TILE / 2


# ------------------------------------------------------------------ 音效
def synth_sounds():
    init = pygame.mixer.get_init()
    if not init or abs(init[1]) != 16:
        return {}
    sr, _, ch = init
    rnd = random.Random(3)

    def mk(fn, dur, vol):
        n = int(sr * dur)
        a = array("h", (int(max(-1.0, min(1.0, fn(i / sr))) * 30000) for i in range(n)))
        b = array("h", bytes(2 * n * ch))
        for c in range(ch):
            b[c::ch] = a
        s = pygame.mixer.Sound(buffer=b.tobytes())
        s.set_volume(vol)
        return s

    def noise_shot(decay, tone, tone_amp):
        state = {"y": 0.0}

        def f(t):
            state["y"] += (rnd.uniform(-1, 1) - state["y"]) * 0.6
            return (state["y"] * 1.4 + math.sin(math.tau * tone * t) * tone_amp) * math.exp(-t * decay)
        return f

    def boom_fn():
        state = {"y": 0.0}

        def f(t):
            state["y"] += (rnd.uniform(-1, 1) - state["y"]) * (0.3 * math.exp(-t * 3) + 0.02)
            return (state["y"] * 2.5 + math.sin(math.tau * (40 + 50 * math.exp(-t * 5)) * t) * 0.8) * math.exp(-t * 3)
        return f

    try:
        pygame.mixer.set_num_channels(40)
        return {
            "shot": mk(noise_shot(30, 220, 0.4), 0.15, 0.25),
            "rifle": mk(noise_shot(20, 120, 0.6), 0.22, 0.3),
            "shotgun": mk(noise_shot(10, 80, 0.7), 0.4, 0.4),
            "awp": mk(noise_shot(7, 60, 0.9), 0.6, 0.5),
            "boom": mk(boom_fn(), 1.1, 0.8),
            "hit": mk(lambda t: math.sin(math.tau * 1400 * t) * math.exp(-t * 60), 0.06, 0.25),
            "click": mk(lambda t: (1 if (t * 900) % 1 < 0.5 else -1) * math.exp(-t * 80) * 0.6, 0.05, 0.4),
            "throw": mk(lambda t: rnd.uniform(-1, 1) * math.sin(math.pi * t / 0.18) * 0.5, 0.18, 0.3),
            "smoke": mk(lambda t: rnd.uniform(-1, 1) * math.exp(-t * 2.5) * 0.5, 1.2, 0.35),
            "fire": mk(lambda t: rnd.uniform(-1, 1) * math.exp(-t * 1.5) * 0.6
                       + math.sin(math.tau * 70 * t) * math.exp(-t * 6) * 0.5, 1.0, 0.45),
        }
    except pygame.error:
        return {}


# ------------------------------------------------------------------ 物件
class Unit:
    def __init__(self, x, y, team, primary, bot, name):
        self.x, self.y, self.team, self.bot, self.name = x, y, team, bot, name
        self.hp = 100.0
        self.alive = True
        self.angle = math.pi / 2 if team == "CT" else -math.pi / 2
        self.guns = {"primary": primary, "pistol": "pistol"}
        self.mag = {k: WEAPONS[w]["mag"] for k, w in self.guns.items()}
        self.res = {k: WEAPONS[w]["res"] for k, w in self.guns.items()}
        self.nades = {"he": 1, "smoke": 1, "molotov": 1}
        self.slot, self.last_slot = "primary", "pistol"
        self.cd = self.reload_t = self.recoil = self.moving = 0.0
        self.walking = False
        # NPC 用
        self.path, self.goal_tile, self.repath = [], None, 0.0
        self.route, self.react, self.lost_t = [], None, 99.0
        self.last_known = self.heard = self.hunt = None
        self.hunt_t = self.strafe_t = self.pause = self.stuck_t = self.nade_cd = 0.0
        self.strafe_dir, self.burst, self.burst_len = 0, 0, 5

    @property
    def weapon(self):
        return WEAPONS[self.guns[self.slot]] if self.slot in self.guns else None


class Nade:
    def __init__(self, kind, x, y, vx, vy, owner):
        self.kind, self.x, self.y, self.vx, self.vy, self.owner = kind, x, y, vx, vy, owner
        self.age = 0.0
        self.done = False


class Smoke:
    DUR, RMAX = 16.0, 125

    def __init__(self, x, y):
        self.x, self.y, self.age = x, y, 0.0
        self.puffs = [(random.uniform(0, math.tau), math.sqrt(random.random()) * 0.72,
                       random.uniform(42, 66), random.uniform(-0.3, 0.3), random.randint(150, 185))
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

    def __init__(self, x, y, owner, game):
        self.x, self.y, self.owner, self.age = x, y, owner, 0.0
        self.points = []
        for _ in range(90):
            a, d = random.uniform(0, math.tau), math.sqrt(random.random()) * self.RAD
            px, py = x + math.cos(a) * d, y + math.sin(a) * d
            if not game.solid(px, py) and game.los(x, y, px, py, smoke=False):
                self.points.append((px, py, random.uniform(0, 6.28)))


# ------------------------------------------------------------------ 遊戲
class Game:
    def __init__(self, diff, assets):
        self.D = DIFFS[diff]
        self.A = assets
        self.grid = [[1] * MW for _ in range(MH)]
        for x, y, w, h in FLOORS:
            for yy in range(y, y + h):
                for xx in range(x, x + w):
                    self.grid[yy][xx] = 0
        for x, y, w, h in CRATES:
            for yy in range(y, y + h):
                for xx in range(x, x + w):
                    self.grid[yy][xx] = 2
        self.map_surf = self.render_map()
        self.mini = pygame.transform.smoothscale(self.map_surf, (MW * 4, MH * 4))
        self.score = [0, 0]  # 你, NPC
        self.kills = self.deaths = 0
        self.round = 0
        self.state = "buy"
        self.end_t = 0.0
        self.end_msg = ""
        self.units = []
        self.player = None
        self.primary = "m4"

    # ---------------- 地圖
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

    def render_map(self):
        surf = pygame.Surface((MW * TILE, MH * TILE))
        rnd = random.Random(42)
        for ty in range(MH):
            for tx in range(MW):
                r = pygame.Rect(tx * TILE, ty * TILE, TILE, TILE)
                g = self.grid[ty][tx]
                if g == 0:
                    v = rnd.randint(-8, 8)
                    surf.fill((196 + v, 172 + v, 124 + v), r)
                    pygame.draw.rect(surf, (184, 160, 114), r, 1)
                elif g == 1:
                    surf.fill((112, 92, 68), r)
                else:
                    surf.fill((150, 108, 60), r)
                    pygame.draw.rect(surf, (95, 65, 35), r.inflate(-4, -4), 3)
                    pygame.draw.line(surf, (95, 65, 35), r.topleft, r.bottomright, 3)
                    pygame.draw.line(surf, (95, 65, 35), r.topright, r.bottomleft, 3)
        # 牆邊陰影
        for ty in range(MH):
            for tx in range(MW):
                if self.grid[ty][tx] == 0:
                    x, y = tx * TILE, ty * TILE
                    if self.tile_solid(tx, ty - 1):
                        pygame.draw.rect(surf, (160, 138, 96), (x, y, TILE, 7))
                    if self.tile_solid(tx - 1, ty):
                        pygame.draw.rect(surf, (172, 150, 106), (x, y, 5, TILE))
                elif self.grid[ty][tx] == 1 and not self.tile_solid(tx, ty + 1):
                    pygame.draw.rect(surf, (90, 72, 52), (tx * TILE, ty * TILE + TILE - 6, TILE, 6))
        tint = pygame.Surface((MW * TILE, MH * TILE), pygame.SRCALPHA)
        for rect, col in ((CT_SPAWN, (70, 130, 255, 22)), (T_SPAWN, (255, 130, 40, 22))):
            x, y, w, h = rect
            tint.fill(col, (x * TILE, y * TILE, w * TILE, h * TILE))
        surf.blit(tint, (0, 0))
        return surf

    # ---------------- 回合
    def free_tiles(self, rect):
        x, y, w, h = rect
        return [(tx, ty) for ty in range(y, y + h) for tx in range(x, x + w) if self.grid[ty][tx] == 0]

    def start_round(self, primary):
        self.primary = primary
        self.round += 1
        cx, cy = tile_center((29, 3))
        self.player = Unit(cx, cy, "CT", primary, False, "你")
        self.units = [self.player]
        spots = random.sample(self.free_tiles(T_SPAWN), self.D["bots"])
        routes = random.sample(ROUTES, len(ROUTES))
        names = random.sample(BOT_NAMES, self.D["bots"])
        pool = ["ak", "ak", "smg", "shotgun", "m4"] + (["awp"] if self.D["bots"] >= 5 else [])
        for i, t in enumerate(spots):
            b = Unit(*tile_center(t), "T", random.choice(pool), True, names[i])
            b.route = [tile_center(w) for w in routes[i % 3 if i < 3 else i % len(routes)]]
            b.nade_cd = random.uniform(5, 20)
            self.units.append(b)
        self.nades, self.smokes, self.fires = [], [], []
        self.tracers, self.parts, self.feed = [], [], []
        self.fire_tiles = set()
        self.timer = ROUND_TIME
        self.shake = self.hurt = self.hitmark = 0.0
        self.state = "live"

    def end_round(self, win, msg):
        self.score[0 if win else 1] += 1
        self.state = "end"
        self.end_t = 3.5
        self.end_msg = msg
        self.round_won = win

    # ---------------- 音效
    def play(self, name, x=None, y=None):
        s = self.A["sounds"].get(name)
        if not s:
            return
        ch = s.play()
        if ch and x is not None and self.player:
            d = math.hypot(x - self.player.x, y - self.player.y)
            ch.set_volume(max(0.08, 1 - d / 1700))

    # ---------------- 戰鬥
    def spread(self, u):
        w = u.weapon
        s = w["spread"] + w["move"] * u.moving + u.recoil
        if u.bot:
            s += self.D["err"]
        return s

    def try_fire(self, u):
        w = u.weapon
        if not w or u.cd > 0 or u.reload_t > 0:
            return False
        if u.mag[u.slot] <= 0:
            self.start_reload(u)
            if not u.bot:
                self.play("click")
            u.cd = 0.25
            return False
        u.mag[u.slot] -= 1
        u.cd = w["rate"]
        sp = self.spread(u)
        for _ in range(w["pellets"]):
            self.hitscan(u, u.angle + random.uniform(-sp, sp) * (0.6 if w["pellets"] == 1 else 1), w)
        u.recoil = min(0.18, u.recoil + w["recoil"])
        mx, my = u.x + math.cos(u.angle) * (R + w["length"]), u.y + math.sin(u.angle) * (R + w["length"])
        self.parts.append([mx, my, 0, 0, 0.05, 0.05, (255, 230, 140), 9])
        self.play(w["snd"], u.x, u.y)
        if not u.bot:
            for b in self.units:
                if b.bot and b.alive and math.hypot(b.x - u.x, b.y - u.y) < 1100:
                    b.heard = (u.x, u.y)
        if u.mag[u.slot] == 0:
            self.start_reload(u)
        return True

    def start_reload(self, u):
        w = u.weapon
        if w and u.reload_t <= 0 and u.res[u.slot] > 0 and u.mag[u.slot] < w["mag"]:
            u.reload_t = w["reload"]

    def hitscan(self, u, a, w):
        dx, dy = math.cos(a), math.sin(a)
        t, step = R + 2, 5
        while t < w["range"] and not self.solid(u.x + dx * t, u.y + dy * t):
            t += step
        wall_t = t
        best, best_t = None, wall_t
        for o in self.units:
            if not o.alive or o.team == u.team:
                continue
            fx, fy = o.x - u.x, o.y - u.y
            proj = fx * dx + fy * dy
            if proj < 0 or proj > best_t:
                continue
            perp2 = fx * fx + fy * fy - proj * proj
            if perp2 > R * R:
                continue
            tt = proj - math.sqrt(R * R - perp2)
            if tt < best_t:
                best, best_t = o, tt
        ex, ey = u.x + dx * best_t, u.y + dy * best_t
        self.tracers.append([u.x + dx * (R + 6), u.y + dy * (R + 6), ex, ey, 0.07])
        if best:
            self.damage(best, w["dmg"], u, w["name"])
            for _ in range(5):
                self.spark(ex, ey, (190, 20, 20), 160, 0.4, 4)
        elif t < w["range"]:
            for _ in range(3):
                self.spark(ex, ey, (255, 220, 120), 150, 0.2, 3)

    def damage(self, v, dmg, attacker, wname):
        if not v.alive:
            return
        v.hp -= dmg
        if v is self.player:
            self.hurt = min(1.0, self.hurt + 0.5)
            self.shake = max(self.shake, 4)
        elif attacker is self.player:
            self.hitmark = 0.2
            self.play("hit")
        if v.bot and attacker is self.player and not self.los(v.x, v.y, attacker.x, attacker.y):
            v.heard = (attacker.x, attacker.y)
        if v.bot and attacker is self.player:
            v.last_known = (attacker.x, attacker.y)
        if v.hp <= 0:
            v.hp = 0
            v.alive = False
            self.feed = (self.feed + [[attacker.name, attacker.team, wname, v.name, v.team, 5.0]])[-5:]
            for _ in range(18):
                self.spark(v.x, v.y, (150, 15, 15), 200, 0.7, 5)
            if v is self.player:
                self.deaths += 1
            elif attacker is self.player:
                self.kills += 1

    def spark(self, x, y, col, spd, life, size):
        a, s = random.uniform(0, math.tau), random.uniform(spd * 0.3, spd)
        self.parts.append([x, y, math.cos(a) * s, math.sin(a) * s, life, life, col, size])

    # ---------------- 投擲物
    def throw(self, u, kind, tx, ty):
        if u.nades.get(kind, 0) <= 0:
            return
        u.nades[kind] -= 1
        d = min(650, max(60, math.hypot(tx - u.x, ty - u.y)))
        v = math.sqrt(2 * 500 * d)
        a = math.atan2(ty - u.y, tx - u.x)
        self.nades.append(Nade(kind, u.x + math.cos(a) * (R + 4), u.y + math.sin(a) * (R + 4),
                               math.cos(a) * v, math.sin(a) * v, u))
        self.play("throw", u.x, u.y)

    def update_nades(self, dt):
        for n in self.nades:
            n.age += dt
            sp = math.hypot(n.vx, n.vy)
            if sp > 0:
                ns = max(0.0, sp - 500 * dt)
                n.vx, n.vy = n.vx * ns / sp, n.vy * ns / sp
            nx = n.x + n.vx * dt
            if self.solid(nx, n.y):
                n.vx *= -0.45
            else:
                n.x = nx
            ny = n.y + n.vy * dt
            if self.solid(n.x, ny):
                n.vy *= -0.45
            else:
                n.y = ny
            sp = math.hypot(n.vx, n.vy)
            if n.kind == "he" and n.age > 1.6:
                self.explode(n)
            elif n.kind == "smoke" and (sp < 5 and n.age > 0.6 or n.age > 3):
                n.done = True
                s = Smoke(n.x, n.y)
                self.smokes.append(s)
                self.fires = [f for f in self.fires if math.hypot(f.x - s.x, f.y - s.y) > s.RMAX + f.RAD * 0.3]
                self.play("smoke", n.x, n.y)
            elif n.kind == "molotov" and (sp < 40 or n.age > 1.8):
                n.done = True
                if any(s.blocking and math.hypot(s.x - n.x, s.y - n.y) < s.r for s in self.smokes):
                    for _ in range(12):
                        self.spark(n.x, n.y, (170, 170, 170), 90, 0.6, 7)
                else:
                    self.fires.append(Fire(n.x, n.y, n.owner, self))
                    self.play("fire", n.x, n.y)
        self.nades = [n for n in self.nades if not n.done]

    def explode(self, n):
        n.done = True
        RAD = 175
        for u in self.units:
            d = math.hypot(u.x - n.x, u.y - n.y)
            if u.alive and d < RAD and self.los(n.x, n.y, u.x, u.y, smoke=False):
                self.damage(u, 98 * (1 - d / RAD), n.owner, "高爆手榴彈")
        for _ in range(45):
            self.spark(n.x, n.y, random.choice([(255, 180, 60), (255, 230, 120), (90, 80, 70)]), 420, 0.6, 8)
        self.parts.append([n.x, n.y, 0, 0, 0.12, 0.12, (255, 240, 200), 70])
        if self.player:
            d = math.hypot(self.player.x - n.x, self.player.y - n.y)
            self.shake = max(self.shake, 16 * max(0.0, 1 - d / 700))
        self.play("boom", n.x, n.y)

    def update_fx(self, dt):
        for s in self.smokes:
            s.age += dt
        self.smokes = [s for s in self.smokes if s.age < s.DUR]
        for f in self.fires:
            f.age += dt
            for u in self.units:
                if u.alive and math.hypot(u.x - f.x, u.y - f.y) < f.RAD and self.los(f.x, f.y, u.x, u.y, smoke=False):
                    self.damage(u, f.DPS * dt, f.owner, "燃燒彈")
            if random.random() < dt * 25 and f.points:
                px, py, _ = random.choice(f.points)
                self.parts.append([px, py, random.uniform(-15, 15), -random.uniform(20, 60), 0.6, 0.6, (90, 80, 75), 9])
        self.fires = [f for f in self.fires if f.age < f.DUR]
        self.fire_tiles = set()
        for f in self.fires:
            for px, py, _ in f.points:
                self.fire_tiles.add((int(px // TILE), int(py // TILE)))
        for p in self.parts:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[2] *= 0.9
            p[3] *= 0.9
            p[4] -= dt
        self.parts = [p for p in self.parts if p[4] > 0][-1500:]
        for t in self.tracers:
            t[4] -= dt
        self.tracers = [t for t in self.tracers if t[4] > 0]
        for f in self.feed:
            f[5] -= dt
        self.feed = [f for f in self.feed if f[5] > 0]
        self.shake = max(0.0, self.shake - dt * 30)
        self.hurt = max(0.0, self.hurt - dt * 1.5)
        self.hitmark = max(0.0, self.hitmark - dt)

    # ---------------- 共用狀態
    def tick_unit(self, u, dt):
        u.cd = max(0.0, u.cd - dt)
        u.recoil = max(0.0, u.recoil - dt * 0.35)
        if u.reload_t > 0:
            u.reload_t -= dt
            if u.reload_t <= 0:
                w = u.weapon
                take = min(w["mag"] - u.mag[u.slot], u.res[u.slot])
                u.mag[u.slot] += take
                u.res[u.slot] -= take

    def switch(self, u, slot):
        if slot == u.slot:
            return
        if slot in ("he", "smoke", "molotov") and u.nades[slot] <= 0:
            return
        u.last_slot, u.slot = u.slot, slot
        u.reload_t = 0
        u.cd = max(u.cd, 0.3)

    # ---------------- 玩家
    def update_player(self, dt, keys, mouse_world, held, clicked):
        p = self.player
        if not p.alive:
            return
        self.tick_unit(p, dt)
        p.angle = math.atan2(mouse_world[1] - p.y, mouse_world[0] - p.x)
        dx = keys[pygame.K_d] - keys[pygame.K_a]
        dy = keys[pygame.K_s] - keys[pygame.K_w]
        p.walking = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        speed = (p.weapon or WEAPONS["pistol"])["speed"] * (0.5 if p.walking else 1)
        target = 0.0
        if dx or dy:
            n = math.hypot(dx, dy)
            self.move_unit(p, dx / n * speed * dt, dy / n * speed * dt)
            target = 0.4 if p.walking else 1.0
        p.moving += (target - p.moving) * min(1.0, dt * 10)

        if p.slot in ("he", "smoke", "molotov"):
            if clicked and p.cd <= 0:
                self.throw(p, p.slot, *mouse_world)
                kind = p.slot
                p.slot = "primary" if p.nades[kind] <= 0 else p.slot
                p.cd = 0.5
        else:
            w = p.weapon
            if (w["auto"] and held) or clicked:
                self.try_fire(p)

    # ---------------- NPC
    def astar(self, start, goal):
        if self.tile_solid(*goal):
            for rr in range(1, 4):
                cands = [(goal[0] + i, goal[1] + j) for i in range(-rr, rr + 1) for j in range(-rr, rr + 1)
                         if not self.tile_solid(goal[0] + i, goal[1] + j)]
                if cands:
                    goal = min(cands, key=lambda c: abs(c[0] - goal[0]) + abs(c[1] - goal[1]))
                    break
            else:
                return []
        openh = [(0, start)]
        came, g = {start: None}, {start: 0}
        while openh:
            _, cur = heapq.heappop(openh)
            if cur == goal:
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nx, ny = cur[0] + dx, cur[1] + dy
                if self.tile_solid(nx, ny):
                    continue
                if dx and dy and (self.tile_solid(cur[0] + dx, cur[1]) or self.tile_solid(cur[0], cur[1] + dy)):
                    continue
                ng = g[cur] + (1.414 if dx and dy else 1) + (30 if (nx, ny) in self.fire_tiles else 0)
                if ng < g.get((nx, ny), 1e9):
                    g[(nx, ny)] = ng
                    came[(nx, ny)] = cur
                    heapq.heappush(openh, (ng + math.hypot(goal[0] - nx, goal[1] - ny), (nx, ny)))
        if goal not in came:
            return []
        path, n = [], goal
        while n != start:
            path.append(n)
            n = came[n]
        return path[::-1]

    def clear_line(self, x1, y1, x2, y2):
        a = math.atan2(y2 - y1, x2 - x1)
        ox, oy = -math.sin(a) * (R + 2), math.cos(a) * (R + 2)
        return all(self.los(x1 + k * ox, y1 + k * oy, x2 + k * ox, y2 + k * oy, smoke=False) for k in (-1, 0, 1))

    def bot_goto(self, b, goal, speed, dt):
        gt = (int(goal[0] // TILE), int(goal[1] // TILE))
        if (gt != b.goal_tile or not b.path) and b.repath <= 0:
            b.path = self.astar((int(b.x // TILE), int(b.y // TILE)), gt)
            b.goal_tile = gt
            b.repath = 0.4
        if b.path:
            while len(b.path) > 1 and self.clear_line(b.x, b.y, *tile_center(b.path[1])):
                b.path.pop(0)
            tx, ty = tile_center(b.path[0])
            if math.hypot(tx - b.x, ty - b.y) < 10:
                b.path.pop(0)
        else:
            tx, ty = goal
        d = math.hypot(tx - b.x, ty - b.y)
        if d < 1:
            return 0.0
        moved = self.move_unit(b, (tx - b.x) / d * speed * dt, (ty - b.y) / d * speed * dt)
        if moved < speed * dt * 0.3:
            b.stuck_t += dt
            if b.stuck_t > 0.8:
                b.path, b.stuck_t, b.repath = [], 0.0, 0.0
                self.move_unit(b, random.uniform(-20, 20), random.uniform(-20, 20))
        else:
            b.stuck_t = 0.0
        return math.atan2(ty - b.y, tx - b.x)

    def update_bot(self, b, dt):
        self.tick_unit(b, dt)
        p, D = self.player, self.D
        b.repath -= dt
        b.pause -= dt
        b.nade_cd -= dt
        w = b.weapon
        speed = w["speed"] * 0.9
        moving = False

        # 逃離火焰
        for f in self.fires:
            d = math.hypot(b.x - f.x, b.y - f.y)
            if d < f.RAD + 10:
                k = speed * dt / max(1.0, d)
                self.move_unit(b, (b.x - f.x) * k, (b.y - f.y) * k)
                b.path = []
                moving = True
                break

        dist = math.hypot(p.x - b.x, p.y - b.y)
        sees = p.alive and dist < 1300 and self.los(b.x, b.y, p.x, p.y)
        if sees:
            b.last_known = (p.x, p.y)
            b.lost_t = 0.0
            ta = math.atan2(p.y - b.y, p.x - b.x)
            if b.react is None:
                behind = abs(ang_diff(b.angle, ta)) > 1.8
                b.react = random.uniform(*D["react"]) + (0.35 if behind else 0)
            b.react -= dt
            diff = ang_diff(b.angle, ta)
            b.angle += max(-D["turn"] * dt, min(D["turn"] * dt, diff))
            b.strafe_t -= dt
            if b.strafe_t <= 0:
                b.strafe_dir = random.choice([-1, 0, 0, 1])
                b.strafe_t = random.uniform(0.3, 0.9)
            if not moving:
                px, py = -math.sin(ta), math.cos(ta)
                adv = 0.8 if b.guns["primary"] in ("shotgun", "smg") and dist > 260 else 0
                vx, vy = px * b.strafe_dir + math.cos(ta) * adv, py * b.strafe_dir + math.sin(ta) * adv
                if vx or vy:
                    n = math.hypot(vx, vy)
                    self.move_unit(b, vx / n * speed * 0.8 * dt, vy / n * speed * 0.8 * dt)
                    moving = True
            if b.react <= 0 and abs(ang_diff(b.angle, ta)) < 0.12 and b.pause <= 0 and b.reload_t <= 0:
                if b.slot != "primary" and b.mag["primary"] > 0:
                    b.slot = "primary"
                elif b.mag[b.slot] == 0 and b.res[b.slot] == 0:
                    b.slot = "pistol"
                if self.try_fire(b):
                    b.burst += 1
                    if b.burst >= b.burst_len:
                        b.burst = 0
                        b.burst_len = random.randint(*D["burst"])
                        b.pause = random.uniform(0.25, 0.5)
        else:
            b.lost_t += dt
            if b.lost_t > 1.2:
                b.react = None
            goal = None
            if b.last_known:
                goal = b.last_known
                if math.hypot(goal[0] - b.x, goal[1] - b.y) < 30:
                    b.last_known = None
            elif b.heard:
                goal = b.heard
                if math.hypot(goal[0] - b.x, goal[1] - b.y) < 40:
                    b.heard = None
            elif b.route:
                goal = b.route[0]
                if math.hypot(goal[0] - b.x, goal[1] - b.y) < 50:
                    b.route.pop(0)
            else:
                b.hunt_t -= dt
                if b.hunt_t <= 0 or b.hunt is None:
                    b.hunt = (p.x + random.uniform(-200, 200), p.y + random.uniform(-200, 200))
                    b.hunt_t = 4.0
                goal = b.hunt
            if goal and not moving:
                face = self.bot_goto(b, goal, speed, dt)
                moving = True
                want = math.atan2(b.last_known[1] - b.y, b.last_known[0] - b.x) if b.last_known else face
                b.angle += max(-D["turn"] * dt, min(D["turn"] * dt, ang_diff(b.angle, want)))
            # 丟手榴彈
            if b.last_known and 0.4 < b.lost_t < 4 and b.nade_cd <= 0:
                kx, ky = b.last_known
                d = math.hypot(kx - b.x, ky - b.y)
                kinds = [k for k in ("he", "molotov") if b.nades[k] > 0]
                if kinds and 180 < d < 650 and random.random() < dt * 1.5:
                    self.throw(b, random.choice(kinds), kx + random.uniform(-40, 40), ky + random.uniform(-40, 40))
                    b.nade_cd = random.uniform(6, 12)
            if b.mag[b.slot] < WEAPONS[b.guns[b.slot]]["mag"] * 0.4 and b.lost_t > 2:
                self.start_reload(b)
        target = 1.0 if moving else 0.0
        b.moving += (target - b.moving) * min(1.0, dt * 10)

    def separate(self):
        alive = [u for u in self.units if u.alive]
        for i, a in enumerate(alive):
            for b in alive[i + 1:]:
                dx, dy = b.x - a.x, b.y - a.y
                d = math.hypot(dx, dy)
                if 0 < d < R * 2:
                    push = (R * 2 - d) / 2
                    self.move_unit(a, -dx / d * push, -dy / d * push)
                    self.move_unit(b, dx / d * push, dy / d * push)

    # ---------------- 主更新
    def update(self, dt, keys, mouse_world, held, clicked):
        self.update_fx(dt)
        if self.state == "end":
            self.end_t -= dt
            return
        self.timer -= dt
        self.update_player(dt, keys, mouse_world, held, clicked)
        for b in self.units:
            if b.bot and b.alive:
                self.update_bot(b, dt)
        self.separate()
        self.update_nades(dt)
        bots_alive = sum(1 for u in self.units if u.bot and u.alive)
        if not self.player.alive:
            self.end_round(False, "你陣亡了 — 進攻方獲勝")
        elif bots_alive == 0:
            self.end_round(True, "敵人全數殲滅 — 防守方獲勝")
        elif self.timer <= 0:
            self.end_round(True, "時間到 — 防守方守住了")


# ------------------------------------------------------------------ 繪圖
class View:
    def __init__(self, screen, assets):
        self.s = screen
        self.A = assets
        self.smoke_layer = pygame.Surface((SW, SH), pygame.SRCALPHA)
        self.fx_layer = pygame.Surface((SW, SH), pygame.SRCALPHA)
        self.f_s, self.f_m, self.f_l, self.f_xl = font(18), font(24, True), font(40, True), font(64, True)

    def text(self, t, f, col, pos, anchor="topleft", shadow=True):
        img = f.render(t, True, col)
        r = img.get_rect(**{anchor: pos})
        if shadow:
            sh = f.render(t, True, (0, 0, 0))
            self.s.blit(sh, r.move(2, 2))
        self.s.blit(img, r)
        return r

    def camera(self, g, mouse):
        p = g.player
        cx = p.x - SW / 2 + (mouse[0] - SW / 2) * 0.35
        cy = p.y - SH / 2 + (mouse[1] - SH / 2) * 0.35
        cx = max(0, min(MW * TILE - SW, cx))
        cy = max(0, min(MH * TILE - SH, cy))
        if g.shake > 0:
            cx += random.uniform(-g.shake, g.shake)
            cy += random.uniform(-g.shake, g.shake)
        return cx, cy

    def draw_unit(self, u, cx, cy, is_player):
        x, y = u.x - cx, u.y - cy
        col = CT_COL if u.team == "CT" else T_COL
        if not u.alive:
            pygame.draw.circle(self.s, (70, 50, 40), (x, y), R)
            pygame.draw.line(self.s, (40, 30, 25), (x - 7, y - 7), (x + 7, y + 7), 3)
            pygame.draw.line(self.s, (40, 30, 25), (x + 7, y - 7), (x - 7, y + 7), 3)
            return
        w = u.weapon
        length = R + (w["length"] if w else 6)
        ex, ey = x + math.cos(u.angle) * length, y + math.sin(u.angle) * length
        pygame.draw.line(self.s, (30, 30, 30), (x, y), (ex, ey), 6 if w and w["length"] > 20 else 5)
        pygame.draw.circle(self.s, (20, 20, 20), (x, y), R + 2)
        pygame.draw.circle(self.s, col, (x, y), R)
        pygame.draw.circle(self.s, tuple(min(255, c + 60) for c in col), (x + math.cos(u.angle) * 4,
                                                                         y + math.sin(u.angle) * 4), 6)
        if is_player:
            pygame.draw.circle(self.s, (255, 255, 255), (x, y), R + 4, 2)
        else:
            pygame.draw.rect(self.s, (40, 0, 0), (x - 15, y - R - 10, 30, 4))
            pygame.draw.rect(self.s, (230, 60, 50), (x - 15, y - R - 10, 30 * u.hp / 100, 4))

    def draw_world(self, g, mouse):
        cx, cy = self.camera(g, mouse)
        s = self.s
        s.blit(g.map_surf, (0, 0), (cx, cy, SW, SH))
        p = g.player

        # 燃燒彈
        fx = self.fx_layer
        fx.fill((0, 0, 0, 0))
        t = pygame.time.get_ticks() / 1000
        for f in g.fires:
            fade = min(1.0, (f.DUR - f.age) / 1.0)
            for px, py, ph in f.points:
                pygame.draw.circle(fx, (40, 20, 10, int(90 * fade)), (px - cx, py - cy), 16)
            for px, py, ph in f.points:
                fl = 0.5 + 0.5 * math.sin(t * 13 + ph * 3)
                col = (255, int(110 + 120 * fl), int(30 * fl), int(220 * fade))
                pygame.draw.circle(fx, col, (px - cx + math.sin(t * 7 + ph) * 3, py - cy - fl * 4), 6 + fl * 7)
        s.blit(fx, (0, 0))

        for n in g.nades:
            col = {"he": (60, 90, 50), "smoke": (170, 170, 170), "molotov": (200, 80, 30)}[n.kind]
            pygame.draw.circle(s, (20, 20, 20), (n.x - cx, n.y - cy), 7)
            pygame.draw.circle(s, col, (n.x - cx, n.y - cy), 5)

        for u in g.units:
            if not u.alive:
                self.draw_unit(u, cx, cy, False)
        for u in g.units:
            if u.alive and (u is p or not p.alive or g.los(p.x, p.y, u.x, u.y)):
                self.draw_unit(u, cx, cy, u is p)

        for x1, y1, x2, y2, life in g.tracers:
            pygame.draw.line(s, (255, 240, 170), (x1 - cx, y1 - cy), (x2 - cx, y2 - cy), 2)
        for x, y, vx, vy, life, mx, col, size in g.parts:
            pygame.draw.circle(s, col, (x - cx, y - cy), max(1, size * life / mx))

        # 煙霧
        sl = self.smoke_layer
        sl.fill((0, 0, 0, 0))
        for sm in g.smokes:
            r = sm.r
            for a, d, size, spin, shade in sm.puffs:
                aa = a + spin * sm.age
                px = sm.x + math.cos(aa) * d * r - cx
                py = sm.y + math.sin(aa) * d * r - cy
                pygame.draw.circle(sl, (shade, shade, shade, int(215 * sm.fade)), (px, py), size * r / sm.RMAX)
        s.blit(sl, (0, 0))

        # 投擲預覽
        if p.alive and p.slot in ("he", "smoke", "molotov"):
            mx, my = mouse[0] + cx, mouse[1] + cy
            d = min(650, math.hypot(mx - p.x, my - p.y))
            a = math.atan2(my - p.y, mx - p.x)
            for k in range(0, int(d), 18):
                pygame.draw.circle(s, (255, 255, 255), (p.x + math.cos(a) * k - cx, p.y + math.sin(a) * k - cy), 2)
            pygame.draw.circle(s, (255, 255, 255), (p.x + math.cos(a) * d - cx, p.y + math.sin(a) * d - cy), 10, 2)
        return cx, cy

    def draw_hud(self, g, mouse):
        s, p = self.s, g.player
        if g.hurt > 0:
            ov = pygame.Surface((SW, SH), pygame.SRCALPHA)
            ov.fill((200, 0, 0, int(90 * g.hurt)))
            s.blit(ov, (0, 0))

        # 小地圖
        s.blit(g.mini, (12, 12))
        pygame.draw.rect(s, (0, 0, 0), (12, 12, MW * 4, MH * 4), 2)
        k = 4 / TILE
        for u in g.units:
            if u.alive and (u is p or (p.alive and g.los(p.x, p.y, u.x, u.y))):
                pygame.draw.circle(s, (255, 255, 255) if u is p else T_COL, (12 + u.x * k, 12 + u.y * k), 4 if u is p else 3)
        for sm in g.smokes:
            pygame.draw.circle(s, (200, 200, 200), (12 + sm.x * k, 12 + sm.y * k), sm.r * k)
        for f in g.fires:
            pygame.draw.circle(s, (255, 120, 30), (12 + f.x * k, 12 + f.y * k), f.RAD * k)

        # 上方比分與時間
        tm = max(0, int(g.timer))
        bx = SW // 2
        pygame.draw.rect(s, (20, 20, 25), (bx - 130, 8, 260, 52), border_radius=8)
        self.text(str(g.score[0]), self.f_l, CT_COL, (bx - 95, 34), "center")
        self.text(str(g.score[1]), self.f_l, T_COL, (bx + 95, 34), "center")
        self.text(f"{tm // 60}:{tm % 60:02d}", self.f_l, (255, 80, 80) if tm < 15 else (240, 240, 240), (bx, 34), "center")
        alive = sum(1 for u in g.units if u.bot and u.alive)
        nb = sum(1 for u in g.units if u.bot)
        for i in range(nb):
            pygame.draw.circle(s, T_COL if i < alive else (70, 70, 70), (bx + (i - (nb - 1) / 2) * 18, 72), 6)
        self.text(f"第 {g.round} 回合  ·  先拿 {WIN_ROUNDS} 回合獲勝", self.f_s, (220, 220, 220), (bx, 92), "center")

        # 擊殺紀錄
        y = 14
        for kn, kt, wn, vn, vt, life in reversed(g.feed):
            surf = [(kn, CT_COL if kt == "CT" else T_COL), (f"  [{wn}]  ", (230, 230, 230)),
                    (vn, CT_COL if vt == "CT" else T_COL)]
            imgs = [self.f_s.render(t, True, c) for t, c in surf]
            wsum = sum(i.get_width() for i in imgs)
            x = SW - 14 - wsum
            pygame.draw.rect(s, (0, 0, 0), (x - 8, y - 3, wsum + 16, 28), border_radius=5)
            for i in imgs:
                s.blit(i, (x, y))
                x += i.get_width()
            y += 32

        # 血量
        pygame.draw.rect(s, (20, 20, 25), (14, SH - 64, 230, 50), border_radius=8)
        self.text("+", self.f_l, (240, 240, 240), (36, SH - 39), "center")
        self.text(str(int(math.ceil(p.hp))), self.f_l, (240, 240, 240) if p.hp > 30 else (255, 70, 70), (60, SH - 39), "midleft")
        pygame.draw.rect(s, (60, 60, 60), (130, SH - 44, 100, 10))
        pygame.draw.rect(s, (90, 220, 110) if p.hp > 30 else (240, 70, 60), (130, SH - 44, p.hp, 10))

        # 武器欄
        labels = {"primary": WEAPONS[p.guns["primary"]]["name"], "pistol": WEAPONS["pistol"]["name"],
                  "he": f"高爆 x{p.nades['he']}", "smoke": f"煙霧 x{p.nades['smoke']}",
                  "molotov": f"燃燒 x{p.nades['molotov']}"}
        x = SW // 2 - 330
        for i, sl in enumerate(SLOTS):
            sel = sl == p.slot
            empty = sl in p.nades and p.nades[sl] <= 0
            r = pygame.Rect(x, SH - 46, 128, 34)
            pygame.draw.rect(s, (60, 70, 90) if sel else (20, 20, 25), r, border_radius=6)
            if sel:
                pygame.draw.rect(s, (220, 220, 240), r, 2, border_radius=6)
            self.text(f"{i + 1} {labels[sl]}", self.f_s, (110, 110, 110) if empty else (235, 235, 235), r.center, "center")
            x += 134

        # 彈藥
        w = p.weapon
        pygame.draw.rect(s, (20, 20, 25), (SW - 230, SH - 64, 216, 50), border_radius=8)
        if w:
            self.text(f"{p.mag[p.slot]}", self.f_l, (240, 240, 240) if p.mag[p.slot] else (255, 70, 70),
                      (SW - 150, SH - 39), "midright")
            self.text(f"/ {p.res[p.slot]}", self.f_m, (170, 170, 170), (SW - 140, SH - 39), "midleft")
            if p.reload_t > 0:
                frac = 1 - p.reload_t / w["reload"]
                pygame.draw.rect(s, (60, 60, 60), (SW - 222, SH - 20, 200, 4))
                pygame.draw.rect(s, (240, 200, 80), (SW - 222, SH - 20, 200 * frac, 4))
                self.text("換彈中…", self.f_m, (240, 200, 80), (SW // 2, SH // 2 + 60), "center")
        else:
            self.text(NADE_NAMES[p.slot], self.f_m, (240, 240, 240), (SW - 122, SH - 39), "center")

        # 準心
        mx, my = mouse
        if p.alive:
            if w:
                dist = math.hypot(mx + g.cam[0] - p.x, my + g.cam[1] - p.y)
                gap = max(4, math.tan(g.spread(p)) * dist)
                col = (80, 255, 120)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    pygame.draw.line(s, (0, 0, 0), (mx + dx * gap, my + dy * gap), (mx + dx * (gap + 10), my + dy * (gap + 10)), 4)
                    pygame.draw.line(s, col, (mx + dx * gap, my + dy * gap), (mx + dx * (gap + 10), my + dy * (gap + 10)), 2)
                pygame.draw.circle(s, col, (mx, my), 1)
            else:
                pygame.draw.circle(s, (255, 255, 255), (mx, my), 4, 1)
            if g.hitmark > 0:
                for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                    pygame.draw.line(s, (255, 255, 255), (mx + dx * 6, my + dy * 6), (mx + dx * 13, my + dy * 13), 2)

        if g.state == "end":
            col = CT_COL if g.round_won else T_COL
            pygame.draw.rect(s, (0, 0, 0), (0, SH // 2 - 70, SW, 110))
            self.text(g.end_msg, self.f_xl, col, (SW // 2, SH // 2 - 15), "center")

    def buy_menu(self, g, mouse):
        s = self.s
        s.blit(pygame.transform.smoothscale(g.map_surf, (SW, int(SW * MH / MW))), (0, -100))
        ov = pygame.Surface((SW, SH), pygame.SRCALPHA)
        ov.fill((10, 12, 18, 215))
        s.blit(ov, (0, 0))
        self.text(f"第 {g.round + 1} 回合 — 選擇主武器", self.f_xl, (240, 240, 240), (SW // 2, 70), "center")
        self.text(f"比分  你 {g.score[0]} : {g.score[1]} NPC      擊殺 {g.kills}  陣亡 {g.deaths}",
                  self.f_m, (200, 200, 200), (SW // 2, 130), "center")
        rects = []
        for i, key in enumerate(PRIMARIES):
            w = WEAPONS[key]
            r = pygame.Rect(SW // 2 - 420, 170 + i * 84, 840, 72)
            hover = r.collidepoint(mouse)
            pygame.draw.rect(s, (55, 65, 90) if hover else (28, 32, 42), r, border_radius=10)
            if key == g.primary:
                pygame.draw.rect(s, (230, 200, 90), r, 2, border_radius=10)
            self.text(f"{i + 1}", self.f_l, (230, 200, 90), (r.x + 36, r.centery), "center")
            self.text(w["name"], self.f_m, (240, 240, 240), (r.x + 70, r.centery), "midleft")
            stats = [("傷害", min(1.0, w["dmg"] * w["pellets"] / 120)), ("射速", min(1.0, 0.07 / w["rate"])),
                     ("精準", 1 - min(1.0, (w["spread"] + w["move"] * 0.3) / 0.11)), ("機動", (w["speed"] - 170) / 80)]
            sx = r.x + 330
            for name, v in stats:
                self.text(name, self.f_s, (180, 180, 180), (sx, r.centery), "midleft", shadow=False)
                pygame.draw.rect(s, (60, 60, 70), (sx + 44, r.centery - 5, 80, 10))
                pygame.draw.rect(s, (110, 200, 120), (sx + 44, r.centery - 5, 80 * max(0.05, v), 10))
                sx += 130
            rects.append(r)
        self.text("每回合附帶：USP-S 手槍、高爆手榴彈、煙霧彈、燃燒彈 各一    按 1–5 或點擊選擇",
                  self.f_s, (200, 200, 200), (SW // 2, SH - 40), "center")
        return rects


def main_menu(view, mouse, diff):
    s = view.s
    s.fill((22, 20, 18))
    view.text("2D TOP DOWN SHOOTING GAME", view.f_xl, (230, 190, 90), (SW // 2, 110), "center")
    view.text("單機版 · 與 NPC 對戰", view.f_m, (220, 220, 220), (SW // 2, 170), "center")
    rects = []
    for i, k in enumerate((1, 2, 3)):
        d = DIFFS[k]
        r = pygame.Rect(SW // 2 - 220, 230 + i * 80, 440, 64)
        hover = r.collidepoint(mouse)
        pygame.draw.rect(s, (60, 66, 84) if hover or k == diff else (34, 36, 44), r, border_radius=10)
        view.text(f"{k}  {d['name']}  ({d['bots']} 個敵人)", view.f_m, (240, 240, 240), r.center, "center")
        rects.append((r, k))
    lines = ["WASD 移動 · Shift 靜步 · 滑鼠瞄準 · 左鍵射擊/投擲 · R 換彈",
             "1 主武器 · 2 手槍 · 3 高爆 · 4 煙霧 · 5 燃燒 · 滾輪切換 · Q 上一把",
             "煙霧會擋住雙方視線，也能撲滅火焰 · 移動中射擊會變不準"]
    for i, ln in enumerate(lines):
        view.text(ln, view.f_s, (190, 190, 190), (SW // 2, 500 + i * 30), "center")
    return rects


# ------------------------------------------------------------------ 主程式
def main():
    pygame.mixer.pre_init(22050, -16, 2, 256)
    pygame.init()
    screen = pygame.display.set_mode((SW, SH))
    pygame.display.set_caption("2D Top Down Shooting Game — 單機版")
    pygame.key.stop_text_input()  # 關閉輸入法（注音/IME 開著時 WASD 會被吃掉或卡住）
    clock = pygame.time.Clock()
    assets = {"sounds": synth_sounds()}
    view = View(screen, assets)
    mode, diff, game = "menu", 2, None

    while True:
        dt = min(clock.tick(FPS) / 1000, 0.05)
        mouse = pygame.mouse.get_pos()
        clicked, keys_down, wheel = False, [], 0
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                return
            if e.type == pygame.KEYDOWN:
                keys_down.append(e.key)
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                clicked = True
            if e.type == pygame.MOUSEWHEEL:
                wheel = e.y

        if mode == "menu":
            pygame.mouse.set_visible(True)
            rects = main_menu(view, mouse, diff)
            choice = None
            for k in keys_down:
                if k in (pygame.K_1, pygame.K_2, pygame.K_3):
                    choice = k - pygame.K_0
                if k == pygame.K_ESCAPE:
                    pygame.quit()
                    return
            if clicked:
                for r, k in rects:
                    if r.collidepoint(mouse):
                        choice = k
            if choice:
                diff = choice
                game = Game(diff, assets)
                mode = "game"

        elif mode == "game":
            if pygame.K_ESCAPE in keys_down:
                mode = "menu"
                continue
            if game.state == "buy":
                pygame.mouse.set_visible(True)
                rects = view.buy_menu(game, mouse)
                pick = None
                for k in keys_down:
                    if pygame.K_1 <= k <= pygame.K_5:
                        pick = PRIMARIES[k - pygame.K_1]
                if clicked:
                    for i, r in enumerate(rects):
                        if r.collidepoint(mouse):
                            pick = PRIMARIES[i]
                if pick:
                    game.start_round(pick)
                    clicked = False
            elif game.state == "over":
                pygame.mouse.set_visible(True)
                screen.fill((15, 15, 18))
                won = game.score[0] >= WIN_ROUNDS
                view.text("勝利！" if won else "戰敗", view.f_xl, CT_COL if won else T_COL, (SW // 2, 220), "center")
                view.text(f"最終比分  {game.score[0]} : {game.score[1]}", view.f_l, (230, 230, 230), (SW // 2, 320), "center")
                view.text(f"擊殺 {game.kills}   陣亡 {game.deaths}", view.f_m, (200, 200, 200), (SW // 2, 380), "center")
                view.text("按 Enter 再來一場 · ESC 回主選單", view.f_m, (200, 200, 200), (SW // 2, 470), "center")
                if pygame.K_RETURN in keys_down:
                    game = Game(diff, assets)
            else:
                pygame.mouse.set_visible(False)
                p = game.player
                if game.state == "live" and p.alive:
                    for k in keys_down:
                        if pygame.K_1 <= k <= pygame.K_5:
                            game.switch(p, SLOTS[k - pygame.K_1])
                        elif k == pygame.K_q:
                            game.switch(p, p.last_slot)
                        elif k == pygame.K_r:
                            game.start_reload(p)
                    if wheel:
                        avail = [sl for sl in SLOTS if sl in p.guns or p.nades.get(sl, 0) > 0]
                        i = avail.index(p.slot) if p.slot in avail else 0
                        game.switch(p, avail[(i - wheel) % len(avail)])
                cam = view.camera(game, mouse) if p else (0, 0)
                game.cam = cam
                mw = (mouse[0] + cam[0], mouse[1] + cam[1])
                game.update(dt, pygame.key.get_pressed(), mw, pygame.mouse.get_pressed()[0], clicked)
                view.draw_world(game, mouse)
                view.draw_hud(game, mouse)
                if game.state == "end" and game.end_t <= 0:
                    game.state = "over" if max(game.score) >= WIN_ROUNDS else "buy"
        pygame.display.flip()


if __name__ == "__main__":
    main()
