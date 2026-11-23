"""
地圖畫風：把地圖格子畫成一張底圖（遊戲開始或換地圖時畫一次，之後重複使用）。
  desert   沙漠：沙色地板、土牆、木箱
  italian  義大利小鎮：紅陶瓦屋頂、石板路、廣場大石板、室內木地板、牆邊爬藤，
           以及物件（fountain 噴泉、coffin 石棺、car 老爺車、cart 推車、barrel 木桶、
           hay 乾草、planter 花台、tomb 墓碑、crate 木箱）
底圖使用固定的 32-bit 格式、半透明圖層用 BLEND_ALPHA_SDL2 疊上，macOS 上顯示才會正確。
"""
import math
import random

import pygame

from config import MW, MH, TILE

T = TILE


def _new_surface():
    surf = pygame.Surface((MW * TILE, MH * TILE), 0, 32, (16711680, 65280, 255, 0))
    surf.fill((0, 0, 0))
    return surf


def _tint_spawns(surf, mp):
    for rect, col in ((mp["ct_spawn"], (70, 130, 255, 24)), (mp["t_spawn"], (255, 130, 40, 24))):
        x, y, w, h = rect
        sub = pygame.Surface((w * TILE, h * TILE), pygame.SRCALPHA)
        sub.fill(col)
        surf.blit(sub, (x * TILE, y * TILE), special_flags=pygame.BLEND_ALPHA_SDL2)


def render_map(g):
    """依地圖的 theme 畫底圖。g 是 MapGrid（有 grid 與 mp）。"""
    surf = render_italian(g) if g.mp.get("theme") == "italian" else render_desert(g)
    _tint_spawns(surf, g.mp)
    return surf


# ================================================================ 沙漠
def render_desert(g):
    surf = _new_surface()
    rnd = random.Random(42)
    for ty in range(MH):
        for tx in range(MW):
            r = pygame.Rect(tx * TILE, ty * TILE, TILE, TILE)
            k = g.grid[ty][tx]
            if k == 0:
                v = rnd.randint(-8, 8)
                surf.fill((196 + v, 172 + v, 124 + v), r)
                pygame.draw.rect(surf, (184, 160, 114), r, 1)
            elif k == 1:
                surf.fill((112, 92, 68), r)
            else:
                surf.fill((150, 108, 60), r)
                pygame.draw.rect(surf, (95, 65, 35), r.inflate(-4, -4), 3)
                pygame.draw.line(surf, (95, 65, 35), r.topleft, r.bottomright, 3)
                pygame.draw.line(surf, (95, 65, 35), r.topright, r.bottomleft, 3)
    for ty in range(MH):
        for tx in range(MW):
            if g.grid[ty][tx] == 0:
                x, y = tx * TILE, ty * TILE
                if g.tile_solid(tx, ty - 1):
                    pygame.draw.rect(surf, (160, 138, 96), (x, y, TILE, 7))
                if g.tile_solid(tx - 1, ty):
                    pygame.draw.rect(surf, (172, 150, 106), (x, y, 5, TILE))
            elif g.grid[ty][tx] == 1 and not g.tile_solid(tx, ty + 1):
                pygame.draw.rect(surf, (90, 72, 52), (tx * TILE, ty * TILE + TILE - 6, TILE, 6))
    return surf


# ================================================================ 義大利小鎮
def inside(rects, tx, ty):
    return any(x <= tx < x + w and y <= ty < y + h for x, y, w, h in rects)


# ---------------- 色票（義大利小鎮）
ROOF = (178, 84, 52); ROOF_D = (138, 60, 38); ROOF_L = (206, 112, 72)
PLASTER = (232, 214, 178); PLASTER_D = (196, 172, 134)
STONE_GAP = (126, 112, 98); STONE = (186, 170, 148)
FLAG_GAP = (150, 136, 118); FLAG = (205, 190, 166)
WOOD = (146, 98, 62); WOOD_D = (112, 72, 44)
GREEN = (86, 128, 58); GREEN_D = (58, 92, 40); GREEN_L = (122, 162, 76)


def render_italian(g):
    rnd = random.Random(7)

    s = _new_surface()
    # 1) 屋頂（牆）：紅陶瓦，每棟用不同色差，一排排弧形瓦片
    s.fill(ROOF)
    for ty in range(MH):
        for tx in range(MW):
            if g.grid[ty][tx] != 1:
                continue
            r = pygame.Rect(tx * T, ty * T, T, T)
            blk = ((tx // 6) * 7 + (ty // 5) * 13) % 5
            base = tuple(max(0, min(255, c + (blk - 2) * 6)) for c in ROOF)
            s.fill(base, r)
            for row in range(4):
                y = r.y + row * 10 + 9
                for k in range(4):
                    x = r.x + k * 10 + (5 if row % 2 else 0)
                    pygame.draw.arc(s, ROOF_D, (x - 5, y - 8, 10, 10), math.pi, 2 * math.pi, 2)
            if ty % 10 == 0:
                pygame.draw.line(s, ROOF_L, r.topleft, r.topright, 3)
    # 1b) 一棟棟房子：屋脊（亮線）＋房子之間的分隔（暗線）
    for ty in range(MH):
        for tx in range(MW):
            if g.grid[ty][tx] != 1:
                continue
            x, y = tx * T, ty * T
            if tx % 6 == 0:
                pygame.draw.line(s, (110, 46, 30), (x, y), (x, y + T), 3)
            if ty % 5 == 0:
                pygame.draw.line(s, (110, 46, 30), (x, y), (x + T, y), 3)
            if ty % 5 == 2:
                pygame.draw.line(s, ROOF_L, (x, y + 20), (x + T, y + 20), 4)
                pygame.draw.line(s, ROOF_D, (x, y + 24), (x + T, y + 24), 2)
    # 2) 地面：石板路 / 廣場大石板 / 室內木地板
    for ty in range(MH):
        for tx in range(MW):
            if g.tile_solid(tx, ty) and not any(p[1] <= tx < p[1] + p[3] and p[2] <= ty < p[2] + p[4] for p in g.mp.get("props", [])):
                continue
            r = pygame.Rect(tx * T, ty * T, T, T)
            v = rnd.randint(-7, 7)
            if inside(g.mp.get("indoor", []), tx, ty):
                s.fill(WOOD_D, r)
                for k in range(4):
                    pr = pygame.Rect(r.x, r.y + k * 10, T, 9)
                    s.fill(tuple(c + rnd.randint(-8, 8) for c in WOOD), pr)
                    cut = r.x + rnd.randint(5, 35)
                    pygame.draw.line(s, WOOD_D, (cut, pr.y), (cut, pr.bottom), 1)
            elif inside(g.mp.get("plaza", []), tx, ty):
                s.fill(FLAG_GAP, r)
                for (ox, oy, w, h) in ((1, 1, 18, 18), (21, 1, 18, 18), (1, 21, 18, 18), (21, 21, 18, 18)):
                    c = tuple(max(0, min(255, cc + v + rnd.randint(-6, 6))) for cc in FLAG)
                    pygame.draw.rect(s, c, (r.x + ox, r.y + oy, w, h), border_radius=3)
            else:
                s.fill(STONE_GAP, r)
                for row in range(3):
                    x = r.x + (0 if row % 2 else -6)
                    while x < r.right:
                        w = rnd.randint(10, 16)
                        c = tuple(max(0, min(255, cc + v + rnd.randint(-10, 10))) for cc in STONE)
                        rr = pygame.Rect(x + 1, r.y + row * 13 + 1, w - 2, 11).clip(r)
                        if rr.w > 2:
                            pygame.draw.rect(s, c, rr, border_radius=4)
                        x += w
    # 3) 牆面：屋簷下的米白色外牆 + 投影；牆上爬藤
    for ty in range(MH):
        for tx in range(MW):
            if g.grid[ty][tx] != 0:
                continue
            x, y = tx * T, ty * T
            if g.grid[ty - 1][tx] == 1 if ty > 0 else False:
                s.fill(PLASTER, (x, y, T, 9)); s.fill(PLASTER_D, (x, y + 9, T, 3))
                shade = pygame.Surface((T, 8), pygame.SRCALPHA); shade.fill((0, 0, 0, 45)); s.blit(shade, (x, y + 12), special_flags=pygame.BLEND_ALPHA_SDL2)
            if tx > 0 and g.grid[ty][tx - 1] == 1:
                s.fill(PLASTER_D, (x, y, 5, T))
            if ty + 1 < MH and g.grid[ty + 1][tx] == 1:
                s.fill(ROOF_D, (x, y + T - 4, T, 4))
    for ty in range(1, MH - 1):
        for tx in range(1, MW - 1):
            if g.grid[ty][tx] == 1 and any(g.grid[ty + dy][tx + dx] == 0 for dx, dy in ((0, 1), (1, 0), (-1, 0), (0, -1))) and rnd.random() < 0.09:
                cx, cy = tx * T + rnd.randint(8, 32), ty * T + rnd.randint(8, 32)
                for _ in range(6):
                    pygame.draw.circle(s, rnd.choice([GREEN, GREEN_D, GREEN_L]), (cx + rnd.randint(-11, 11), cy + rnd.randint(-11, 11)), rnd.randint(5, 9))
    # 4) 物件
    for kind, px, py, pw, ph in g.mp.get("props", []):
        R = pygame.Rect(px * T, py * T, pw * T, ph * T)
        sh = pygame.Surface(R.size, pygame.SRCALPHA)
        if kind in ("fountain", "barrel"):
            pygame.draw.circle(sh, (0, 0, 0, 70), (R.w // 2, R.h // 2), min(R.w, R.h) // 2 - 2)
        else:
            pygame.draw.rect(sh, (0, 0, 0, 60), sh.get_rect().inflate(-6, -6), border_radius=8)
        s.blit(sh, R.move(4, 5), special_flags=pygame.BLEND_ALPHA_SDL2)
        if kind == "fountain":
            c = R.center; rad = R.w // 2 - 3
            pygame.draw.circle(s, (150, 140, 126), c, rad + 2)
            pygame.draw.circle(s, (214, 204, 188), c, rad)
            pygame.draw.circle(s, (60, 128, 160), c, rad - 12)
            for k in range(3):
                pygame.draw.circle(s, (120, 184, 210), c, rad - 20 - k * 11, 2)
            pygame.draw.circle(s, (214, 204, 188), c, 13)
            pygame.draw.circle(s, (170, 200, 220), c, 6)
            for a in range(8):
                ang = a * math.pi / 4
                pygame.draw.circle(s, (230, 240, 248), (c[0] + math.cos(ang) * 19, c[1] + math.sin(ang) * 19), 2)
        elif kind == "coffin":
            pygame.draw.rect(s, (120, 116, 110), R.inflate(-4, -10), border_radius=6)
            pygame.draw.rect(s, (168, 164, 156), R.inflate(-10, -16), border_radius=5)
            cx, cy = R.center
            pygame.draw.line(s, (110, 106, 100), (cx - 14, cy), (cx + 14, cy), 3)
            pygame.draw.line(s, (110, 106, 100), (cx - 6, cy - 6), (cx - 6, cy + 6), 3)
        elif kind == "car":
            body = R.inflate(-10, -6)
            for wx, wy in ((body.x - 2, body.y + 8), (body.right - 4, body.y + 8), (body.x - 2, body.bottom - 18), (body.right - 4, body.bottom - 18)):
                pygame.draw.rect(s, (30, 30, 30), (wx, wy, 6, 12), border_radius=2)
            pygame.draw.rect(s, (70, 120, 112), body, border_radius=10)
            pygame.draw.rect(s, (160, 200, 210), (body.x + 4, body.y + 16, body.w - 8, 12), border_radius=4)
            pygame.draw.rect(s, (52, 92, 86), (body.x + 4, body.y + 32, body.w - 8, 22), border_radius=4)
            pygame.draw.rect(s, (225, 220, 170), (body.x + 4, body.y + 3, 6, 4)); pygame.draw.rect(s, (225, 220, 170), (body.right - 10, body.y + 3, 6, 4))
        elif kind == "cart":
            box = R.inflate(-6, -12)
            pygame.draw.rect(s, (118, 78, 46), box, border_radius=4)
            for k in range(1, 4):
                pygame.draw.line(s, (90, 58, 32), (box.x + k * box.w // 4, box.y), (box.x + k * box.w // 4, box.bottom), 2)
            pygame.draw.ellipse(s, (214, 182, 92), box.inflate(-14, -8))
            pygame.draw.rect(s, (40, 30, 22), (box.x + 8, box.y - 5, 10, 5)); pygame.draw.rect(s, (40, 30, 22), (box.right - 18, box.bottom, 10, 5))
        elif kind == "barrel":
            c = R.center
            pygame.draw.circle(s, (96, 60, 34), c, 16); pygame.draw.circle(s, (132, 88, 52), c, 13)
            pygame.draw.circle(s, (70, 60, 52), c, 13, 2); pygame.draw.circle(s, (70, 60, 52), c, 7, 2)
        elif kind == "hay":
            b = R.inflate(-6, -8)
            pygame.draw.rect(s, (200, 166, 78), b, border_radius=7)
            for k in range(b.x + 6, b.right - 3, 7):
                pygame.draw.line(s, (166, 134, 56), (k, b.y + 3), (k - 3, b.bottom - 3), 2)
            pygame.draw.line(s, (120, 90, 40), (b.x + b.w // 3, b.y), (b.x + b.w // 3, b.bottom), 2)
            pygame.draw.line(s, (120, 90, 40), (b.x + 2 * b.w // 3, b.y), (b.x + 2 * b.w // 3, b.bottom), 2)
        elif kind == "planter":
            b = R.inflate(-4, -4)
            pygame.draw.rect(s, (170, 150, 128), b, border_radius=5)
            for _ in range(7):
                pygame.draw.circle(s, rnd.choice([GREEN, GREEN_D, GREEN_L]), (b.centerx + rnd.randint(-9, 9), b.centery + rnd.randint(-9, 9)), rnd.randint(5, 8))
            pygame.draw.circle(s, (220, 80, 90), (b.centerx + 5, b.centery - 4), 3); pygame.draw.circle(s, (240, 200, 90), (b.centerx - 6, b.centery + 5), 3)
        elif kind == "tomb":
            b = R.inflate(-12, -8)
            pygame.draw.rect(s, (150, 148, 142), b, border_radius=8)
            pygame.draw.rect(s, (110, 108, 102), b, 2, border_radius=8)
            pygame.draw.line(s, (100, 98, 94), (b.centerx, b.y + 5), (b.centerx, b.bottom - 5), 2)
            pygame.draw.line(s, (100, 98, 94), (b.centerx - 5, b.y + 10), (b.centerx + 5, b.y + 10), 2)
        else:  # crate
            b = R.inflate(-4, -4)
            pygame.draw.rect(s, (150, 104, 58), b); pygame.draw.rect(s, (96, 64, 34), b, 3)
            pygame.draw.line(s, (96, 64, 34), b.topleft, b.bottomright, 3); pygame.draw.line(s, (96, 64, 34), b.topright, b.bottomleft, 3)
    return s
