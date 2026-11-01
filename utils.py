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
