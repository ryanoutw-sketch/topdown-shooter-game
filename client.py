"""
兩端共用的「畫面 + 本機輸入」：
pygame 初始化、讀鍵盤滑鼠、把輸入打包送給主機、套用快照、
加入者的本機移動預測與其他角色平滑、選槍後防誤射。
"""
import math

import pygame

from client_fx import FX
from client_world import World
from config import SW, SH, PORT, ZOOM, VW, VH, WEAPONS, PRIMARIES, SLOTS
from sounds import synth_sounds
from view import View


def setup(caption):
    pygame.mixer.pre_init(22050, -16, 2, 256)
    pygame.init()
    screen = pygame.display.set_mode((SW, SH))
    pygame.display.set_caption(caption)
    pygame.key.stop_text_input()  # 關閉輸入法（注音/IME 開著時 WASD 會被吃掉或卡住）
    return screen, pygame.time.Clock(), synth_sounds()


def poll():
    """回傳 (quit, keys_down, clicked, wheel)。"""
    quit_, keys, clicked, wheel = False, [], False, 0
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            quit_ = True
        elif e.type == pygame.KEYDOWN:
            keys.append(e.key)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            clicked = True
        elif e.type == pygame.MOUSEWHEEL:
            wheel += e.y
    return quit_, keys, clicked, wheel


def build_input(view, state, keys_down, clicked, wheel, mouse, rects):
    """把本機鍵鼠轉成送給主機的輸入。"""
    k = pygame.key.get_pressed()
    inp = {"w": int(k[pygame.K_w]), "a": int(k[pygame.K_a]), "s": int(k[pygame.K_s]), "d": int(k[pygame.K_d]),
           "sh": int(k[pygame.K_LSHIFT] or k[pygame.K_RSHIFT]),
           "mx": round(mouse[0] / ZOOM + view.cam[0], 1), "my": round(mouse[1] / ZOOM + view.cam[1], 1),
           "held": int(pygame.mouse.get_pressed()[0]), "click": clicked, "cmds": []}
    if state == "buy":
        pick = None
        for key in keys_down:
            if pygame.K_1 <= key <= pygame.K_5:
                pick = PRIMARIES[key - pygame.K_1]
        if clicked and rects:
            for i, r in enumerate(rects):
                if r.collidepoint(mouse):
                    pick = PRIMARIES[i]
        inp["pick"] = pick
        inp["click"] = False
    elif state == "live":
        for key in keys_down:
            if pygame.K_1 <= key <= pygame.K_5:
                inp["cmds"].append(["slot", SLOTS[key - pygame.K_1]])
            elif key == pygame.K_q:
                inp["cmds"].append(["last"])
            elif key == pygame.K_r:
                inp["cmds"].append(["reload"])
        if wheel:
            inp["cmds"].append(["wheel", wheel])
    return inp


class _Pos:
    def __init__(self, x, y):
        self.x, self.y = x, y


class Screen:
    """兩端共用的「畫面 + 本機輸入」狀態。"""

    def __init__(self, screen, sounds, me):
        self.view = View(screen)
        self.world = World()
        self.fx = FX(sounds)
        self.me = me
        self.rects = []
        self.my_pick = None
        self.last_round = -1
        self.fire_lock = True  # 回合開始後要先放開左鍵一次才能開槍（避免選槍那一下被當成射擊）
        self.predict = me != 0   # 加入者才需要
        self.pred = None
        self.targets, self.disp = {}, {}

    def feed(self, snaps):
        """套用收到的所有快照（事件全部處理，畫面用最後一張）。"""
        if not snaps:
            return
        self.world.apply(snaps[-1])
        self.targets = {u.uid: (u.x, u.y) for u in self.world.units}
        S = self.world.s
        if S["round"] != self.last_round:
            self.last_round = S["round"]
            self.fx.reset()
        if S["st"] != "buy":
            self.my_pick = None
        cx, cy = self.view.cam
        listener = (cx + VW / 2, cy + VH / 2)
        for sn in snaps:
            self.fx.process(sn["ev"], self.me, listener)

    def local_motion(self, dt, inp):
        """加入者：自己的移動在本機立即計算；其他人的位置做平滑，避免封包忽快忽慢造成頓挫。"""
        w, S = self.world, self.world.s
        if not self.predict or not S:
            return
        p = w.unit(self.me)
        if S["st"] != "live" or not p or not p.alive:
            self.pred = None
        else:
            if self.pred is None or math.hypot(self.pred.x - p.x, self.pred.y - p.y) > 90:
                self.pred = _Pos(p.x, p.y)  # 回合開始或被主機拉回
            dx = inp["d"] - inp["a"]
            dy = inp["s"] - inp["w"]
            if dx or dy:
                walking = inp["sh"]
                speed = (p.weapon or WEAPONS["pistol"])["speed"] * (0.5 if walking else 1)
                n = math.hypot(dx, dy)
                w.move_unit(self.pred, dx / n * speed * dt, dy / n * speed * dt)
            p.x, p.y = self.pred.x, self.pred.y
        kk = min(1.0, dt * 18)
        disp = {}
        for u in w.units:
            if u.uid == self.me:
                continue
            tx, ty = self.targets.get(u.uid, (u.x, u.y))
            d = self.disp.get(u.uid)
            if d and math.hypot(d[0] - tx, d[1] - ty) < 80:
                d = (d[0] + (tx - d[0]) * kk, d[1] + (ty - d[1]) * kk)
            else:
                d = (tx, ty)
            disp[u.uid] = d
            u.x, u.y = d
        self.disp = disp

    def draw(self, dt, mouse, is_host, ip="", port=PORT):
        v, w = self.view, self.world
        S = w.s
        self.rects = []
        if S is None:
            v.message(["連線中…"])
            return
        st = S["st"]
        pygame.mouse.set_visible(st not in ("live", "end"))
        if st == "lobby":
            self.rects = v.lobby(S, self.me, is_host, mouse, ip, port)
        elif st == "buy":
            self.rects = v.buy_menu(w, self.me, mouse, self.my_pick)
        elif st == "over":
            v.over(S, self.me, is_host)
        else:
            self.fx.update(dt, w.fires)
            focus = v.camera(w, self.me, mouse, self.fx)
            v.draw_world(w, self.fx, self.me, mouse)
            v.draw_hud(w, self.fx, self.me, mouse, focus)

    def make_input(self, keys_down, clicked, wheel, mouse, dt=0.0):
        S = self.world.s
        st = S["st"] if S else "lobby"
        inp = build_input(self.view, st, keys_down, clicked, wheel, mouse,
                          self.rects if st == "buy" else None)
        if inp.get("pick"):
            self.my_pick = inp["pick"]
        if st != "live":
            self.fire_lock = True
        elif self.fire_lock:
            if not inp["held"]:
                self.fire_lock = False
            inp["held"], inp["click"] = 0, False
        self.local_motion(dt, inp)
        if self.pred is not None:
            inp["px"], inp["py"] = round(self.pred.x, 1), round(self.pred.y, 1)
            inp["rnd"] = S["round"]
        return inp
