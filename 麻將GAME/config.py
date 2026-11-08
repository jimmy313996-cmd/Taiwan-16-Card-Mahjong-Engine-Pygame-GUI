class UIConfig:
    FPS = 60
    SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 800
    
    # 麻將牌尺寸
    TILE_WIDTH, TILE_HEIGHT = 45, 60
    DISCARD_SCALE = 0.7
    
    # 預算縮小版尺寸 (供副露與海底牌使用)
    SMALL_W = int(TILE_WIDTH * DISCARD_SCALE)
    SMALL_H = int(TILE_HEIGHT * DISCARD_SCALE)
    
    # 座標預算 (避免在繪圖迴圈中重複計算)
    MY_HAND_Y = SCREEN_HEIGHT - TILE_HEIGHT - 20
    MY_MELD_X_START = SCREEN_WIDTH - 130  # 副露從右邊開始排
    
    # ================= 新增：玩家資訊與分數安全區座標 =================
    # 將資訊文字推到手牌上方或螢幕邊角，避免與牌重疊
    INFO_MY_Y = MY_HAND_Y - 35             # 玩家資訊顯示在手牌正上方 35 像素處
    INFO_OPP_TOP_Y = 20                    # 對家 (上方 CPU) 資訊顯示在最頂端
    INFO_OPP_LEFT_X = 20                   # 上家 (左側 CPU) 資訊靠最左
    INFO_OPP_RIGHT_X = SCREEN_WIDTH - 150  # 下家 (右側 CPU) 資訊靠最右
    # =================================================================
    
    # 顏色庫
    COLOR_BG = (34, 139, 34) # 經典麻將桌綠
    COLOR_BTN = (200, 200, 200)
    COLOR_TEXT = (255, 255, 255) # 白色文字



    