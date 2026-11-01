# 2D Top Down Shooting Game — 雙人連線版

## 執行

```
py -m pip install -r requirements.txt        # 第一次才需要
py topdown_shooter.py --host                            # 主機（可加 --name 小明）
py topdown_shooter.py --join 192.168.50.112             # 另一台加入
```

主機在大廳：**M** 切換合作／對戰、**1/2/3** 選難度、**Enter** 開始、**ESC** 離開。

## 檔案結構

依「想改什麼 → 看哪個檔」排列：

| 檔案 | 內容 | 什麼時候會看它 |
|---|---|---|
| `topdown_shooter.py` | 程式入口：參數、主機迴圈、加入者迴圈、連線/斷線處理 | 想了解整體流程、改啟動參數 |
| `config.py` | **所有可調數值**：畫面、回合時間、勝利回合數、武器（傷害/射速/視野…）、NPC 難度、合作模式減弱、回血、視野、顏色 | 平衡遊戲最常改這裡 |
| `map_data.py` | 地圖格局：地板、箱子、出生點、NPC 進攻路線 | 改地圖 |
| **主機端（遊戲規則）** | | |
| `game.py` | 回合流程、開槍判定、傷害、投擲物、回血、玩家輸入、送出快照 | 改規則、勝負條件 |
| `bots.py` | NPC AI：A* 尋路、反應/瞄準/掃射、追蹤、丟手榴彈、躲火 | 改 NPC 行為 |
| `units.py` | 角色與投擲物的資料 | 加角色屬性 |
| **共用** | | |
| `grid.py` | 地圖碰撞、視線、移動、煙霧與燃燒彈區域 | 改碰撞或煙霧/火的範圍 |
| `network.py` | 連線收發（JSON） | 網路問題 |
| `sounds.py` | 音效（程式合成） | 改聲音 |
| `utils.py` | 小工具：角度、幾何、字型、IP、視野半徑 | |
| **畫面端** | | |
| `client.py` | pygame 初始化、讀鍵鼠、輸入打包、本機移動預測、防誤射 | 改操作手感 |
| `client_world.py` | 把主機快照轉成可畫的物件、預先畫好地圖底圖 | |
| `client_fx.py` | 特效與音效播放（火花、彈道、震動、受傷紅光） | 改特效 |
| `view.py` | 畫面總管：鏡頭、可見判定、戰爭迷霧圓形遮罩 | 改視角/迷霧 |
| `view_world.py` | 畫地圖上的東西：角色、火、煙、彈道、迷霧 | 改角色外觀 |
| `view_hud.py` | HUD：小地圖、比分、擊殺紀錄、血量、武器欄、彈藥、準心 | 改介面 |
| `view_menus.py` | 大廳、選槍、結算畫面 | 改選單 |

## 架構重點

- **主機是唯一的真相**：所有判定（命中、傷害、NPC）只在主機的 `game.py` 執行。
  每一幀主機把整個狀態打包成「快照」送給加入者，自己也用同一份快照畫畫面。
- **事件**：開槍、爆炸、受傷等一次性的東西放在快照的 `ev` 裡，兩端的 `client_fx.py` 依事件播特效和音效。
- **加入者的移動**在自己電腦上先算（`client.py` 的 `local_motion`），再回報位置給主機檢查，所以不會有網路延遲的頓挫。
- 依賴方向：`topdown_shooter.py → client/game → view*/bots/grid → config/map_data/utils`，`config.py` 與 `map_data.py` 不依賴任何其他檔案。

## 常見調整

| 想做的事 | 改哪裡 |
|---|---|
| 某把槍的傷害、射速、視野 | `config.py` → `WEAPONS` |
| NPC 強弱 | `config.py` → `DIFFS`、`COOP_BOT` |
| 回血速度 | `config.py` → `REGEN_DELAY`、`REGEN_RATE`（不能超過任何槍的 DPS，程式會檢查） |
| 畫面縮放 | `config.py` → `ZOOM` |
| 幾回合獲勝、回合時間 | `config.py` → `WIN_ROUNDS`、`ROUND_TIME` |
| 地圖 | `map_data.py` |

## 其他

- `legacy/cs_offline.py`：早期的單機版（單一檔案，只能一個人打 NPC），執行 `py legacy/cs_offline.py`。

## 協作流程（Git）

```
git pull                      # 開始改之前先拿最新版
git checkout -b 功能名稱       # 每個功能開一個分支
git add -A
git commit -m "說明改了什麼"
git push -u origin 功能名稱     # 推上去後在 GitHub 開 Pull Request 合併
```
