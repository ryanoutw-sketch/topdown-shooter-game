"""
本機特效與音效：依主機送來的事件產生火花、彈道、震動、受傷紅光。
"""
import math
import random


class FX:
    """本機特效與音效，由事件驅動。"""

    def __init__(self, sounds):
        self.sounds = sounds
        self.parts, self.tracers = [], []
        self.shake = self.hurt = self.hitmark = 0.0

    def play(self, name, x=None, y=None, listener=None):
        s = self.sounds.get(name)
        if not s:
            return
        ch = s.play()
        if ch and x is not None and listener:
            d = math.hypot(x - listener[0], y - listener[1])
            ch.set_volume(max(0.08, 1 - d / 1700))

    def spark(self, x, y, col, spd, life, size, n=1):
        for _ in range(n):
            a, s = random.uniform(0, math.tau), random.uniform(spd * 0.3, spd)
            self.parts.append([x, y, math.cos(a) * s, math.sin(a) * s, life, life, col, size])

    def process(self, evs, me, listener):
        for e in evs:
            k = e[0]
            if k == "shot":
                self.parts.append([e[1], e[2], 0, 0, 0.05, 0.05, (255, 230, 140), 9])
                self.play(e[3], e[1], e[2], listener)
            elif k == "tr":
                self.tracers.append([e[1], e[2], e[3], e[4], 0.07])
            elif k == "blood":
                self.spark(e[1], e[2], (190, 20, 20), 160, 0.4, 4, 5)
            elif k == "wall":
                self.spark(e[1], e[2], (255, 220, 120), 150, 0.2, 3, 3)
            elif k == "death":
                self.spark(e[1], e[2], (150, 15, 15), 200, 0.7, 5, 18)
            elif k == "fizz":
                self.spark(e[1], e[2], (170, 170, 170), 90, 0.6, 7, 12)
            elif k == "boom":
                x, y = e[1], e[2]
                for _ in range(45):
                    self.spark(x, y, random.choice([(255, 180, 60), (255, 230, 120), (90, 80, 70)]), 420, 0.6, 8)
                self.parts.append([x, y, 0, 0, 0.12, 0.12, (255, 240, 200), 70])
                if listener:
                    d = math.hypot(listener[0] - x, listener[1] - y)
                    self.shake = max(self.shake, 16 * max(0.0, 1 - d / 700))
                self.play("boom", x, y, listener)
            elif k == "snd":
                self.play(e[1], e[2], e[3], listener)
            elif k == "click" and e[1] == me:
                self.play("click")
            elif k == "hurt" and e[1] == me:
                self.hurt = min(1.0, self.hurt + e[2] / 60)
                if e[2] > 5:
                    self.shake = max(self.shake, 4)
            elif k == "hm" and e[1] == me:
                self.hitmark = 0.2
                self.play("hit")

    def update(self, dt, fires):
        for f in fires:
            if random.random() < dt * 25 and f.points:
                px, py, _ = random.choice(f.points)
                self.parts.append([px, py, random.uniform(-15, 15), -random.uniform(20, 60), 0.6, 0.6, (90, 80, 75), 9])
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
        self.shake = max(0.0, self.shake - dt * 30)
        self.hurt = max(0.0, self.hurt - dt * 1.5)
        self.hitmark = max(0.0, self.hitmark - dt)

    def reset(self):
        self.parts, self.tracers = [], []
        self.shake = self.hurt = self.hitmark = 0.0
