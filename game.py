"""
主機端的遊戲邏輯（只在主機執行，是唯一的「真相」）：
回合流程、開槍判定、傷害、投擲物、回血、玩家輸入處理，以及每幀送給雙方的快照。
NPC 的行為在 bots.py。
"""
import math
import random

from bots import BotMixin
from config import (DIFFS, COOP_BOT, ROUND_TIME, WIN_ROUNDS, BOT_NAMES, PRIMARIES, NADES, SLOTS,
                    WEAPONS, R, TILE, REGEN_DELAY, REGEN_RATE)
from grid import MapGrid, Smoke, Fire
from map_data import CT_HUMAN_SPOTS, T_HUMAN_SPOTS, T_SPAWN, ROUTES
from units import Unit, Nade
from utils import tile_center


class Game(BotMixin, MapGrid):
    def __init__(self):
        super().__init__()
        self.mode, self.diff = "coop", 2
        self.names = ["P1", "P2"]
        self.humans = [0]
        self.state = "lobby"
        self.notice = ""
        self.reset_match()

    @property
    def D(self):
        d = dict(DIFFS[self.diff])
        if self.mode == "coop":
            d["react"] = tuple(r * COOP_BOT["react"] for r in d["react"])
            d["err"] += COOP_BOT["err"]
            d["turn"] *= COOP_BOT["turn"]
        return d

    def reset_match(self):
        self.score = [0, 0]          # 合作: [CT, NPC]；對戰: [P1, P2]
        self.stats = [[0, 0], [0, 0]]  # 每位玩家 [擊殺, 陣亡]
        self.round = 0
        self.picks = {}
        self.units, self.nades, self.smokes, self.fires, self.feed = [], [], [], [], []
        self.fire_tiles = set()
        self.events = []
        self.timer, self.end_t, self.rw, self.reason = ROUND_TIME, 0.0, None, ""
        self.next_id = 1

    def begin_match(self):
        self.reset_match()
        self.notice = ""
        self.state = "buy"

    def to_lobby(self, notice=""):
        self.reset_match()
        self.state = "lobby"
        self.notice = notice

    def human_team(self, uid, rnd):
        if self.mode == "coop":
            return "CT"
        return "CT" if (uid == 0) == (rnd % 2 == 1) else "T"

    def ev(self, *a):
        self.events.append(list(a))

    # ---------------- 回合
    def start_round(self):
        self.round += 1
        self.units = []
        used = {"CT": 0, "T": 0}
        for uid in sorted(self.humans):
            team = self.human_team(uid, self.round)
            spot = (CT_HUMAN_SPOTS if team == "CT" else T_HUMAN_SPOTS)[used[team]]
            used[team] += 1
            self.units.append(Unit(uid, *tile_center(spot), team, self.picks.get(uid, "m4"), False, self.names[uid]))
        if self.mode == "coop":
            n = min(len(BOT_NAMES), self.D["bots"] + 2 * (len(self.humans) - 1))
            spots = random.sample(self.free_tiles(T_SPAWN), n)
            routes = random.sample(ROUTES, len(ROUTES))
            names = random.sample(BOT_NAMES, n)
            pool = ["ak", "ak", "smg", "shotgun", "m4"] + (["awp"] if self.D["bots"] >= 5 else [])
            for i, t in enumerate(spots):
                b = Unit(10 + i, *tile_center(t), "T", random.choice(pool), True, names[i])
                b.route = [tile_center(w) for w in routes[i % 3 if i < 3 else i % len(routes)]]
                b.nade_cd = random.uniform(5, 20)
                self.units.append(b)
        self.nades, self.smokes, self.fires = [], [], []
        self.fire_tiles = set()
        self.picks = {}
        self.timer = ROUND_TIME
        self.state = "live"

    def end_round(self, rw, reason):
        if self.mode == "coop":
            self.score[0 if rw else 1] += 1
        elif rw >= 0:
            self.score[rw] += 1
        self.rw, self.reason = rw, reason
        self.state = "end"
        self.end_t = 3.5

    def check_end(self):
        alive_h = [u for u in self.units if not u.bot and u.alive]
        if self.mode == "coop":
            bots = sum(1 for u in self.units if u.bot and u.alive)
            if not alive_h:
                self.end_round(False, "防守方全滅")
            elif bots == 0:
                self.end_round(True, "敵人全數殲滅")
            elif self.timer <= 0:
                self.end_round(True, "時間到，守住了")
        else:
            if len(alive_h) == 1:
                self.end_round(alive_h[0].uid, "擊倒對手")
            elif not alive_h:
                self.end_round(-1, "同歸於盡")
            elif self.timer <= 0:
                self.end_round(-1, "時間到")

    def drop_player(self, uid):
        if uid in self.humans:
            self.humans.remove(uid)
        self.picks.pop(uid, None)
        for u in self.units:
            if u.uid == uid and u.alive:
                u.alive, u.hp = False, 0

    # ---------------- 戰鬥
    def spread(self, u):
        w = u.weapon
        s = w["spread"] + w["move"] * u.moving + u.recoil
        return s + (self.D["err"] if u.bot else 0)

    def try_fire(self, u):
        w = u.weapon
        if not w or u.cd > 0 or u.reload_t > 0:
            return False
        if u.mag[u.slot] <= 0:
            self.start_reload(u)
            if not u.bot:
                self.ev("click", u.uid)
            u.cd = 0.25
            return False
        u.mag[u.slot] -= 1
        u.cd = w["rate"]
        sp = self.spread(u)
        for _ in range(w["pellets"]):
            self.hitscan(u, u.angle + random.uniform(-sp, sp) * (0.6 if w["pellets"] == 1 else 1), w)
        u.recoil = min(0.18, u.recoil + w["recoil"])
        L = R + w["length"]
        self.ev("shot", round(u.x + math.cos(u.angle) * L), round(u.y + math.sin(u.angle) * L), w["snd"])
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
        t = R + 2
        while t < w["range"] and not self.solid(u.x + dx * t, u.y + dy * t):
            t += 5
        best, best_t = None, t
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
        ex, ey = round(u.x + dx * best_t), round(u.y + dy * best_t)
        self.ev("tr", round(u.x + dx * (R + 6)), round(u.y + dy * (R + 6)), ex, ey)
        if best:
            self.damage(best, w["dmg"], u, w["name"])
            self.ev("blood", ex, ey)
        elif t < w["range"]:
            self.ev("wall", ex, ey)

    def damage(self, v, dmg, attacker, wname, marker=True):
        if not v.alive:
            return
        if attacker and attacker.bot and self.mode == "coop":
            dmg *= COOP_BOT["dmg"]
        v.hp -= dmg
        v.since_hit = 0.0
        if not v.bot:
            self.ev("hurt", v.uid, round(dmg, 1))
        if marker and attacker and not attacker.bot and attacker is not v and attacker.team != v.team:
            self.ev("hm", attacker.uid)
        if v.bot and attacker and not attacker.bot:
            v.last_known = (attacker.x, attacker.y)
        if v.hp <= 0:
            v.hp = 0
            v.alive = False
            self.feed = (self.feed + [[attacker.name, attacker.team, wname, v.name, v.team, 5.0]])[-5:]
            self.ev("death", round(v.x), round(v.y))
            if not v.bot:
                self.stats[v.uid][1] += 1
            if not attacker.bot and attacker.team != v.team:
                self.stats[attacker.uid][0] += 1

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
        self.ev("snd", "throw", round(u.x), round(u.y))

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
            x, y = round(n.x), round(n.y)
            if n.kind == "he" and n.age > 1.6:
                self.explode(n)
            elif n.kind == "smoke" and (sp < 5 and n.age > 0.6 or n.age > 3):
                n.done = True
                s = Smoke(x, y, self.next_id)
                self.next_id += 1
                self.smokes.append(s)
                self.fires = [f for f in self.fires if math.hypot(f.x - s.x, f.y - s.y) > s.RMAX + f.RAD * 0.3]
                self.ev("snd", "smoke", x, y)
            elif n.kind == "molotov" and (sp < 40 or n.age > 1.8):
                n.done = True
                if any(s.blocking and math.hypot(s.x - x, s.y - y) < s.r for s in self.smokes):
                    self.ev("fizz", x, y)
                else:
                    self.fires.append(Fire(x, y, n.owner, self, self.next_id))
                    self.next_id += 1
                    self.ev("snd", "fire", x, y)
        self.nades = [n for n in self.nades if not n.done]

    def explode(self, n):
        n.done = True
        RAD = 175
        for u in self.units:
            d = math.hypot(u.x - n.x, u.y - n.y)
            if u.alive and d < RAD and self.los(n.x, n.y, u.x, u.y, smoke=False):
                self.damage(u, 98 * (1 - d / RAD), n.owner, "高爆手榴彈")
        self.ev("boom", round(n.x), round(n.y))

    def update_world(self, dt):
        for s in self.smokes:
            s.age += dt
        self.smokes = [s for s in self.smokes if s.age < s.DUR]
        for f in self.fires:
            f.age += dt
            for u in self.units:
                if u.alive and math.hypot(u.x - f.x, u.y - f.y) < f.RAD and self.los(f.x, f.y, u.x, u.y, smoke=False):
                    self.damage(u, f.DPS * dt, f.owner, "燃燒彈", marker=False)
        self.fires = [f for f in self.fires if f.age < f.DUR]
        self.fire_tiles = {(int(px // TILE), int(py // TILE)) for f in self.fires for px, py, _ in f.points}
        for f in self.feed:
            f[5] -= dt
        self.feed = [f for f in self.feed if f[5] > 0]

    # ---------------- 共用
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
        if slot == u.slot or slot not in SLOTS:
            return
        if slot in NADES and u.nades[slot] <= 0:
            return
        u.last_slot, u.slot = u.slot, slot
        u.reload_t = 0
        u.cd = max(u.cd, 0.3)

    # ---------------- 玩家
    def update_human(self, p, inp, dt):
        self.tick_unit(p, dt)
        p.since_hit += dt
        if p.since_hit > REGEN_DELAY and p.hp < 100:
            p.hp = min(100.0, p.hp + REGEN_RATE * dt)
        if not inp:
            p.moving += (0 - p.moving) * min(1.0, dt * 10)
            return
        for c in inp.get("cmds", []):
            if c[0] == "slot":
                self.switch(p, c[1])
            elif c[0] == "last":
                self.switch(p, p.last_slot)
            elif c[0] == "reload":
                self.start_reload(p)
            elif c[0] == "wheel":
                avail = [sl for sl in SLOTS if sl in p.guns or p.nades.get(sl, 0) > 0]
                i = avail.index(p.slot) if p.slot in avail else 0
                self.switch(p, avail[(i - int(c[1])) % len(avail)])
        mx, my = inp.get("mx", p.x + 1), inp.get("my", p.y)
        p.angle = math.atan2(my - p.y, mx - p.x)
        dx = inp.get("d", 0) - inp.get("a", 0)
        dy = inp.get("s", 0) - inp.get("w", 0)
        walking = inp.get("sh", 0)
        speed = (p.weapon or WEAPONS["pistol"])["speed"] * (0.5 if walking else 1)
        target = 0.0
        if dx or dy:
            target = 0.4 if walking else 1.0
        if inp.get("rnd") == self.round and "px" in inp:
            # 加入者在自己電腦上先算好移動（沒有網路延遲），主機只做合理性檢查
            nx, ny = inp["px"], inp["py"]
            if math.hypot(nx - p.x, ny - p.y) < 120 and not self.blocked(nx, ny):
                p.x, p.y = nx, ny
        elif dx or dy:
            n = math.hypot(dx, dy)
            self.move_unit(p, dx / n * speed * dt, dy / n * speed * dt)
        p.moving += (target - p.moving) * min(1.0, dt * 10)

        if p.slot in NADES:
            if inp.get("click") and p.cd <= 0:
                kind = p.slot
                self.throw(p, kind, mx, my)
                if p.nades[kind] <= 0:
                    p.slot = "primary"
                p.cd = 0.5
        else:
            w = p.weapon
            if (w["auto"] and inp.get("held")) or inp.get("click"):
                self.try_fire(p)


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
    def update(self, dt, inputs):
        if self.state == "buy":
            for uid, inp in inputs.items():
                if inp and uid in self.humans and inp.get("pick") in PRIMARIES:
                    self.picks[uid] = inp["pick"]
            if self.humans and all(h in self.picks for h in self.humans):
                self.start_round()
            return
        if self.state not in ("live", "end"):
            return
        self.update_world(dt)
        if self.state == "end":
            self.end_t -= dt
            if self.end_t <= 0:
                self.state = "over" if max(self.score) >= WIN_ROUNDS else "buy"
            return
        self.timer -= dt
        for u in self.units:
            if u.alive:
                if u.bot:
                    self.update_bot(u, dt)
                else:
                    self.update_human(u, inputs.get(u.uid), dt)
        self.separate()
        self.update_nades(dt)
        self.check_end()

    def snapshot(self, connected):
        nxt = self.round if self.state in ("live", "end") else self.round + 1
        snap = {
            "st": self.state, "mode": self.mode, "diff": self.diff, "round": self.round,
            "timer": round(self.timer, 2), "score": self.score, "rw": self.rw, "reason": self.reason,
            "humans": self.humans, "picks": list(self.picks), "stats": self.stats, "names": self.names,
            "side": [self.human_team(0, nxt), self.human_team(1, nxt)], "conn": connected, "notice": self.notice,
            "u": [u.ser() for u in self.units],
            "n": [[n.kind, round(n.x), round(n.y)] for n in self.nades],
            "sm": [[s.id, s.x, s.y, round(s.age, 2)] for s in self.smokes],
            "fi": [[f.id, f.x, f.y, round(f.age, 2)] for f in self.fires],
            "feed": [[f[0], f[1], f[2], f[3], f[4], round(f[5], 1)] for f in self.feed],
            "ev": self.events,
        }
        self.events = []
        return snap
