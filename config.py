"""
所有可以調整的遊戲參數都在這裡：畫面、回合、武器數值、NPC 難度、回血、視野、顏色。
想平衡遊戲（例如改某把槍的傷害或視野）只要改這個檔案。
"""

SW, SH = 1280, 720
FPS = 60
PORT = 5555
TILE = 40
MW, MH = 50, 38
ROUND_TIME = 115
WIN_ROUNDS = 5
R = 13  # 角色半徑

# ---------------- 武器
WEAPONS = {
    "pistol": dict(name="USP-S 手槍", dmg=34, rate=0.17, mag=12, res=48, reload=1.6, spread=0.012,
                   move=0.05, recoil=0.03, speed=245, pellets=1, range=1400, auto=False, snd="shot", length=14, view=520),
    "smg": dict(name="MP7 衝鋒槍", dmg=24, rate=0.075, mag=30, res=120, reload=2.0, spread=0.03,
                move=0.035, recoil=0.012, speed=238, pellets=1, range=1200, auto=True, snd="shot", length=18, view=500),
    "m4": dict(name="M4A4 步槍", dmg=32, rate=0.092, mag=30, res=90, reload=2.4, spread=0.007,
               move=0.10, recoil=0.017, speed=218, pellets=1, range=2200, auto=True, snd="rifle", length=22, view=640),
    "ak": dict(name="AK-47 步槍", dmg=38, rate=0.1, mag=30, res=90, reload=2.5, spread=0.009,
               move=0.12, recoil=0.025, speed=212, pellets=1, range=2200, auto=True, snd="rifle", length=22, view=620),
    "shotgun": dict(name="Nova 霰彈槍", dmg=17, rate=0.85, mag=8, res=32, reload=2.8, spread=0.10,
                    move=0.03, recoil=0.0, speed=222, pellets=9, range=650, auto=False, snd="shotgun", length=20, view=440),
    "awp": dict(name="AWP 狙擊槍", dmg=115, rate=1.45, mag=5, res=30, reload=3.6, spread=0.0015,
                move=0.28, recoil=0.0, speed=185, pellets=1, range=2800, auto=False, snd="awp", length=28, view=840),
}
PRIMARIES = ["smg", "m4", "ak", "shotgun", "awp"]
NADES = ("he", "smoke", "molotov")
NADE_NAMES = {"he": "高爆手榴彈", "smoke": "煙霧彈", "molotov": "燃燒彈"}
SLOTS = ["primary", "pistol", "he", "smoke", "molotov"]

DIFFS = {
    1: dict(name="簡單", bots=3, react=(0.6, 1.0), err=0.06, turn=4.0, burst=(3, 5)),
    2: dict(name="普通", bots=5, react=(0.35, 0.65), err=0.035, turn=6.0, burst=(4, 7)),
    3: dict(name="困難", bots=5, react=(0.18, 0.38), err=0.017, turn=9.0, burst=(5, 9)),
}
# 合作模式 NPC 減弱：傷害倍率、反應時間倍率、額外瞄準誤差、轉身速度倍率
COOP_BOT = dict(dmg=0.65, react=1.4, err=0.02, turn=0.75)

# 回血：受傷後 REGEN_DELAY 秒開始回，每秒 REGEN_RATE。
# 規則：回血速度必須低於任何一把槍的 DPS（最低的是 AWP ≈ 79/秒；合作模式 NPC 打 65% 也有 ≈ 51/秒）
MIN_GUN_DPS = min(w["dmg"] * w["pellets"] / w["rate"] for w in WEAPONS.values())
REGEN_DELAY = 4.0
REGEN_RATE = 6.0
assert REGEN_RATE < MIN_GUN_DPS * COOP_BOT["dmg"], "回血不能超過任何槍的 DPS"

# 視野：畫面縮小顯示更大範圍；戰爭迷霧是圍著玩家的圓，圓外全黑
ZOOM = 0.75
VW, VH = int(SW / ZOOM), int(SH / ZOOM)
# 視野圓半徑由手上的槍決定（WEAPONS 的 view）；拿投擲物時用主武器的視野。圓內的敵人仍會被牆擋住
FOG_EDGE = 70       # 圓邊緣的漸層寬度（螢幕像素）
DARK_ALPHA = 245
TEAM_NAMES = {"CT": "防守方", "T": "進攻方"}

BOT_NAMES = ["Gus", "Kilo", "Raven", "Vex", "Bishop", "Nomad", "Sable"]
MODE_NAMES = {"coop": "合作：一起打 NPC", "pvp": "對戰：1v1 交換攻守"}

CT_COL = (80, 140, 235)
T_COL = (225, 140, 55)
