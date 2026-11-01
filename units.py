"""
主機端的遊戲物件：角色（玩家與 NPC 共用）與飛行中的投擲物。
"""
import math

from config import WEAPONS, REGEN_DELAY


class Unit:
    def __init__(self, uid, x, y, team, primary, bot, name):
        self.uid, self.x, self.y, self.team, self.bot, self.name = uid, x, y, team, bot, name
        self.hp = 100.0
        self.alive = True
        self.angle = math.pi / 2 if team == "CT" else -math.pi / 2
        self.guns = {"primary": primary, "pistol": "pistol"}
        self.mag = {k: WEAPONS[w]["mag"] for k, w in self.guns.items()}
        self.res = {k: WEAPONS[w]["res"] for k, w in self.guns.items()}
        self.nades = {"he": 1, "smoke": 1, "molotov": 1}
        self.slot, self.last_slot = "primary", "pistol"
        self.cd = self.reload_t = self.recoil = self.moving = 0.0
        self.since_hit = 99.0
        # NPC 用
        self.path, self.goal_tile, self.repath = [], None, 0.0
        self.route, self.react, self.lost_t = [], None, 99.0
        self.last_known = self.heard = self.hunt = None
        self.hunt_t = self.strafe_t = self.pause = self.stuck_t = self.nade_cd = 0.0
        self.strafe_dir, self.burst, self.burst_len = 0, 0, 5

    @property
    def weapon(self):
        return WEAPONS[self.guns[self.slot]] if self.slot in self.guns else None

    def ser(self):
        w = self.weapon
        return [self.uid, self.name, self.team, int(self.bot), round(self.x, 1), round(self.y, 1),
                round(self.angle, 3), round(self.hp, 1), int(self.alive), self.guns["primary"], self.slot,
                self.mag.get(self.slot, 0), self.res.get(self.slot, 0),
                round(self.reload_t / w["reload"], 2) if (w and self.reload_t > 0) else 0,
                self.nades["he"], self.nades["smoke"], self.nades["molotov"],
                round(self.moving, 2), round(self.recoil, 3),
                int(not self.bot and self.since_hit > REGEN_DELAY and self.hp < 100)]


class Nade:
    def __init__(self, kind, x, y, vx, vy, owner):
        self.kind, self.x, self.y, self.vx, self.vy, self.owner = kind, x, y, vx, vy, owner
        self.age = 0.0
        self.done = False
