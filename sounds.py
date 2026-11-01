"""
音效：程式即時合成，不需要任何音檔。
"""
import math
import random
from array import array

import pygame


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
