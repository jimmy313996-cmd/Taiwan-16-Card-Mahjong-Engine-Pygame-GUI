# 🀄 Taiwan 16-Card Mahjong Engine & Pygame GUI (台灣 16 張麻將遊戲與自動化對戰系統)

本專案是一套基於 **Python (OOP)** 與 **Pygame** 開發的正統台灣 16 張麻將遊戲與自動化對戰系統。採用經典的 **MVC (Model-View-Controller)** 架構設計，完整實作了麻將的底層規則、複雜狀態機（State Machine）、智慧型防禦 AI 決策，以及嚴謹的台數與籌碼結算系統。
<img width="1152" height="648" alt="download" src="https://github.com/user-attachments/assets/79949bf3-7469-4061-ba82-2786d2323cbe" />



---

## 🌟 核心特色亮點 (Key Features)

1. **嚴密的台灣麻將規則引擎 (`mahjong_engine.py`)**：
   - 支援 144 張牌動態洗牌、起手 16 張發牌、補花機制。
   - 完整支援吃、碰、大明槓、暗槓、補槓、搶槓胡、槓上開花、海底撈月、河底撈魚、七搶一、八仙過海等特殊規則。
   - 內建過水限制（Guo-Shui）與宣告聽牌後的鎖死機制。

2. **MVC 架構與多執行緒 GUI 通訊 (`mahjong_controller.py`, `mahjong_gui_a.py`)**：
   - 採用 **MVC 模式**，將純後端遊戲邏輯與 Pygame 圖形介面徹底解耦。
   - 透過多執行緒與阻塞式等待機制（`_wait_for_gui`），完美處理問答式互動（如詢問玩家是否碰、槓、胡、吃牌組合）。

3. **防禦型智慧 AI 大腦 (`cpu_choose_discard`)**：
   - CPU 具備動態威脅評估能力，能根據牌海殘張、對手副露（Melds）與聽牌狀態，自動在 **「進攻 (ATTACK)」** 與 **「防守/撤退 (DEFEND)」** 模式間切換。
   - 嚴格的防呆攔截機制，確保吃牌動作符合「僅限上家」等合法距離與牌型檢核。

4. **精準台數計算模組 (`TaiCalculator`)**：
   - 自動化計算門清自摸、三元牌、四喜、清一色、字一色、花牌及莊家連拉台數。
   - 實現完整的跨局籌碼轉移、連莊移莊、風圈推進與破產機制（Bankruptcy Detection）。

---

## 📂 專案檔案架構 (Project Structure)

```text
├── config.py             # 視窗配置、麻將牌尺寸、顏色庫與畫面安全區座標常數
├── mahjong_engine.py     # 核心邏輯層 (Model)：包含 Tile、Player、MahjongGame、TaiCalculator
├── mahjong_controller.py # 控制層 (Controller)：處理滑鼠懸停 (Hover)、點擊與事件分流
└── mahjong_gui_a.py      # 視圖與主程式 (View)：Pygame 圖形介面渲染、圖像載入與 Match 循環管理
```

---

## ⚙️ 技術堆疊 (Tech Stack)
* **Language**: Python 3.x
* **Library**: Pygame (2D 遊戲介面渲染與事件處理)
* **Design Pattern**: MVC (Model-View-Controller), Object-Oriented Programming (OOP)
* **Algorithms**: 狀態機 (State Machine)、遞迴牌型拆解與胡牌判定、牌海殘張風險評估

---

## 🚀 快速開始與執行 (Getting Started)

### 1. 環境需求
確保您的電腦已安裝 Python 3.8+ 與 Pygame 套件。

### 2. 安裝依賴
```bash
pip install pygame
```

### 3. 準備素材
在專案根目錄建立名為 `麻將圖` (`TILE_DIR`) 的資料夾，並放入對應編號的牌面圖片（如 `101.png` ~ `608.png` 及 `back.png`）。

### 4. 執行遊戲
```bash
python mahjong_gui_a.py
```

---

## 🧠 技術實作亮點剖析

### 1. 遊戲狀態機與非同步通訊
為了解決純後端引擎在等待玩家點擊按鈕時容易卡死主迴圈的問題，玩家類別（`HumanPlayer`）設計了狀態標籤 (`ui_state`) 與阻塞等待迴圈：
```python
def _wait_for_gui(self):
    self.gui_response = "WAITING"
    while self.gui_response == "WAITING":
        time.sleep(0.1) # 讓出 CPU 資源給 GUI 線程
    response = self.gui_response
    self.ui_state = "idle"
    return response
```

### 2. 智慧型 CPU 風險防禦演算法
CPU 在每次切牌時，會綜合計算全場已見牌（Visible Counts）、河牌歷史與對手威脅副露：
- 當全場進入聽牌階段或後期，CPU 會自動提高安全牌權重，捨棄危險張，展現高擬真度的對局策略。

---

## 👨‍💻 作者 (Author)
* 徐子育 (初階 Python 後端工程師轉職者)
* 專注於後端邏輯架構、系統狀態機設計與 AI 協同開發。歡迎交流與指教！
