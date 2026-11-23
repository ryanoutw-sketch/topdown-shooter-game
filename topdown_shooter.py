"""
2D Top Down Shooting Game — 雙人連線版 (Python + pygame)

安裝:  py -m pip install pygame
主機:  py topdown_shooter.py --host                     （可加 --name 小明）
加入:  py topdown_shooter.py --join 192.168.50.112      （可加 --name 阿華）

模式（主機在大廳選，M 切換）:
  合作：兩人都是防守方，一起對抗 NPC 進攻方（主機可以不等玩家 2，直接單人開打）
  對戰：1v1，每回合交換攻守
  地圖（主機在大廳按 G 切換）：Dunes 沙漠圖、Old Town 小鎮圖

操作:
  WASD 移動 / Shift 靜步（更準）/ 滑鼠瞄準 / 左鍵射擊或投擲
  1 主武器  2 手槍  3 高爆手榴彈  4 煙霧彈  5 燃燒彈  滾輪切換  Q 切回上一把  R 換彈
  主機：ESC 回大廳；加入者：ESC 離開
  先拿 5 回合獲勝。煙霧會擋住視線，也能撲滅燃燒彈的火。

各檔案用途見 README.md。
"""
import argparse
import socket
import threading

import pygame

from client import Screen, poll, setup
from config import FPS, PORT
from game import Game
from map_data import MAP_ORDER
from network import Net
from utils import local_ip


def run_host(port, name):
    screen, clock, sounds = setup("2D Top Down Shooting Game — Host")
    game = Game()
    game.names[0] = name or "P1"
    ui = Screen(screen, sounds, 0)
    ip = local_ip()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", port))
    srv.listen(1)
    holder = {"net": None}

    def accept_loop():
        while True:
            try:
                conn, _ = srv.accept()
            except OSError:
                return
            cur = holder["net"]
            if cur and cur.alive:
                conn.close()
                continue
            holder["net"] = Net(conn)

    threading.Thread(target=accept_loop, daemon=True).start()
    remote = {}  # 玩家 2 最後的持續性輸入（按鍵、滑鼠位置）

    while True:
        dt = min(clock.tick(FPS) / 1000, 0.05)
        quit_, keys_down, clicked, wheel = poll()
        if quit_:
            break
        if ui.anim.intro_on and (keys_down or clicked):  # 入場動畫：任意鍵跳過（這一下不當成其他操作）
            ui.anim.skip_intro()
            keys_down, clicked = [], False
        mouse = pygame.mouse.get_pos()

        # ---- 連線狀態
        net = holder["net"]
        connected = bool(net and net.alive)
        if connected and 1 not in game.humans:
            game.humans.append(1)
            game.names[1] = "P2"
            game.notice = ""
            remote = {}
        if not connected and 1 in game.humans:
            game.drop_player(1)
            if game.mode == "pvp" and game.state != "lobby":
                game.to_lobby("Player 2 disconnected")
            else:
                game.notice = "Player 2 disconnected"
        r_inp = None
        if connected:
            got, agg = False, {"click": False, "cmds": []}
            for m in net.drain():
                if m.get("t") == "hello":
                    game.names[1] = str(m.get("name") or "P2")[:12]
                elif m.get("t") == "in":
                    got = True
                    for key in ("w", "a", "s", "d", "sh", "mx", "my", "held", "px", "py", "rnd"):
                        if key in m:
                            remote[key] = m[key]
                    agg["click"] = agg["click"] or bool(m.get("click"))
                    agg["cmds"] += m.get("cmds", [])
                    if m.get("pick"):
                        agg["pick"] = m["pick"]
            r_inp = dict(remote, **agg) if (got or remote) else None

        # ---- 主機自己的大廳 / 結算操作
        st = game.state
        if pygame.K_ESCAPE in keys_down:
            if st == "lobby":
                break
            game.to_lobby()
            ui.fx.reset()
        elif st == "lobby":
            acts = [a for r, a in ui.rects if clicked and r.collidepoint(mouse)]
            for key in keys_down:
                if key == pygame.K_m:
                    acts.append(("mode", "pvp" if game.mode == "coop" else "coop"))
                elif key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    acts.append(("diff", key - pygame.K_0))
                elif key == pygame.K_g:  # 切換地圖
                    acts.append(("map", MAP_ORDER[(MAP_ORDER.index(game.map_id) + 1) % len(MAP_ORDER)]))
                elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    acts.append(("start", None))
            for kind, val in acts:
                if kind == "mode":
                    game.mode = val
                elif kind == "diff":
                    game.diff = val
                elif kind == "map":
                    game.set_map(val)
                elif kind == "start":
                    if game.mode == "pvp" and not connected:
                        game.notice = "Versus mode needs Player 2 to connect"
                    else:
                        game.begin_match()
        elif st == "over" and any(k in (pygame.K_RETURN, pygame.K_KP_ENTER) for k in keys_down):
            game.begin_match()

        # ---- 模擬 + 廣播
        local = ui.make_input(keys_down, clicked, wheel, mouse)
        game.update(dt, {0: local, 1: r_inp})
        snap = game.snapshot(connected)
        if connected:
            net.send(snap)
        ui.feed([snap])
        ui.draw(dt, mouse, True, ip, port)
        pygame.display.flip()

    if holder["net"]:
        holder["net"].close()
    srv.close()
    pygame.quit()


def run_client(host, port, name):
    try:
        sock = socket.create_connection((host, port), timeout=5)
    except OSError as e:
        print(f"Cannot connect to {host}:{port} → {e}\nMake sure the host is running --host and the firewall allows TCP {port}")
        return
    net = Net(sock)
    net.send({"t": "hello", "name": name or "P2"})
    screen, clock, sounds = setup("2D Top Down Shooting Game — Client")
    ui = Screen(screen, sounds, 1)

    while True:
        dt = min(clock.tick(FPS) / 1000, 0.05)
        quit_, keys_down, clicked, wheel = poll()
        if ui.anim.intro_on and (keys_down or clicked):  # 入場動畫：任意鍵跳過
            ui.anim.skip_intro()
            keys_down, clicked = [], False
        if quit_ or pygame.K_ESCAPE in keys_down:
            break
        mouse = pygame.mouse.get_pos()
        if not net.alive:
            pygame.mouse.set_visible(True)
            ui.view.message(["Disconnected from host", "Press ESC to quit"])
            pygame.display.flip()
            continue
        ui.feed(net.drain())
        inp = ui.make_input(keys_down, clicked, wheel, mouse, dt)
        ui.draw(dt, mouse, False)
        inp["t"] = "in"
        net.send(inp)
        pygame.display.flip()

    net.close()
    pygame.quit()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="2D Top Down Shooting Game — 2-player online")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--host", action="store_true", help="host a game")
    g.add_argument("--join", metavar="IP", help="IP address of the host to join")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--name", default="", help="display name")
    args = ap.parse_args()
    if args.host:
        run_host(args.port, args.name)
    else:
        run_client(args.join, args.port, args.name)
