"""
NPC 的 AI（混入 Game 使用）：A* 尋路、看到敵人後的反應/瞄準/掃射、
追蹤最後位置、丟手榴彈、躲火焰。
"""
import heapq
import math
import random

from config import TILE, R, WEAPONS
from utils import ang_diff, tile_center


class BotMixin:
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
            return b.angle
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
        D = self.D
        b.repath -= dt
        b.pause -= dt
        b.nade_cd -= dt
        speed = b.weapon["speed"] * 0.9
        moving = False

        for f in self.fires:  # 逃離火焰
            d = math.hypot(b.x - f.x, b.y - f.y)
            if d < f.RAD + 10:
                k = speed * dt / max(1.0, d)
                self.move_unit(b, (b.x - f.x) * k, (b.y - f.y) * k)
                b.path = []
                moving = True
                break

        enemies = [u for u in self.units if u.alive and u.team != b.team]
        tgt, dist = None, 1e9
        for e in enemies:
            d = math.hypot(e.x - b.x, e.y - b.y)
            if d < 1300 and d < dist and self.los(b.x, b.y, e.x, e.y):
                tgt, dist = e, d

        if tgt:
            b.last_known = (tgt.x, tgt.y)
            b.lost_t = 0.0
            ta = math.atan2(tgt.y - b.y, tgt.x - b.x)
            if b.react is None:
                behind = abs(ang_diff(b.angle, ta)) > 1.8
                b.react = random.uniform(*D["react"]) + (0.35 if behind else 0)
            b.react -= dt
            b.angle += max(-D["turn"] * dt, min(D["turn"] * dt, ang_diff(b.angle, ta)))
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
            elif enemies:
                b.hunt_t -= dt
                if b.hunt_t <= 0 or b.hunt is None:
                    e = random.choice(enemies)
                    b.hunt = (e.x + random.uniform(-200, 200), e.y + random.uniform(-200, 200))
                    b.hunt_t = 4.0
                goal = b.hunt
            if goal and not moving:
                face = self.bot_goto(b, goal, speed, dt)
                moving = True
                want = math.atan2(b.last_known[1] - b.y, b.last_known[0] - b.x) if b.last_known else face
                b.angle += max(-D["turn"] * dt, min(D["turn"] * dt, ang_diff(b.angle, want)))
            if b.last_known and 0.4 < b.lost_t < 4 and b.nade_cd <= 0:  # 丟手榴彈
                kx, ky = b.last_known
                d = math.hypot(kx - b.x, ky - b.y)
                kinds = [k for k in ("he", "molotov") if b.nades[k] > 0]
                if kinds and 180 < d < 650 and random.random() < dt * 1.5:
                    self.throw(b, random.choice(kinds), kx + random.uniform(-40, 40), ky + random.uniform(-40, 40))
                    b.nade_cd = random.uniform(6, 12)
            if b.mag[b.slot] < WEAPONS[b.guns[b.slot]]["mag"] * 0.4 and b.lost_t > 2:
                self.start_reload(b)
        b.moving += ((1.0 if moving else 0.0) - b.moving) * min(1.0, dt * 10)
