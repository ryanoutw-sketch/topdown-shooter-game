"""
共用的小工具函式：角度、幾何、字型、顏色、IP、視野半徑。
"""
import math
import socket

import pygame

from config import TILE, CT_COL, T_COL, WEAPONS


def team_col(team):
    return CT_COL if team == "CT" else T_COL


def font(size, bold=False):
    try:
        return pygame.font.SysFont(
            "microsoftjhenghei,microsoftjhengheiui,microsoftyahei,pmingliu,hiraginosansgb,stheitimedium,"
            "pingfangtc,pingfangsc,notosanscjktc,notosanscjksc,notosanscjk,wenquanyizenhei,arialunicodems,arial",
            size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size)


def text_surface(fnt, text, color):
    """Render text，確保回傳 per-pixel alpha surface（SRCALPHA）。
    pygame.font.render() 在某些 macOS SDL2 路徑下會回傳無 alpha channel 的 surface，
    需手動轉換為 SRCALPHA，才能讓 BLEND_ALPHA_SDL2 正確合成。
    """
    surf = fnt.render(text, True, color)
    if surf.get_masks()[3] == 0:
        # 無 alpha channel：轉成 per-pixel alpha
        alpha = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        alpha.blit(surf, (0, 0))
        return alpha
    return surf


def fit_width(surf, max_w):
    """文字太寬時等比例縮小到 max_w（不同電腦字型寬度不同，避免超出框或疊到旁邊）。"""
    if max_w and surf.get_width() > max_w > 0:
        k = max_w / surf.get_width()
        return pygame.transform.smoothscale(surf, (int(max_w), max(1, int(surf.get_height() * k))))
    return surf


def ang_diff(a, b):
    return (b - a + math.pi) % math.tau - math.pi


def seg_point_dist(x1, y1, x2, y2, px, py):
    dx, dy = x2 - x1, y2 - y1
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L))
    return math.hypot(x1 + dx * t - px, y1 + dy * t - py)


def tile_center(t):
    return t[0] * TILE + TILE / 2, t[1] * TILE + TILE / 2


def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def view_r(u):
    """角色目前的視野半徑（u 需要有 weapon 與 primary）。"""
    w = u.weapon or WEAPONS[u.primary]
    return w["view"]
