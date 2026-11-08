import pygame
from config import UIConfig 

class MahjongController:
    def __init__(self, human_player):
        self.human_player = human_player
        self.hovered_index = -1  # 記錄目前滑鼠懸停在哪張牌上

    def handle_events(self, events, active_buttons):
        """處理所有 Pygame 事件，並接收當前啟動的按鈕"""
        mouse_pos = pygame.mouse.get_pos()
        
        # 1. 處理滑鼠懸停特效 (Hover)
        self._update_hover_state(mouse_pos)

        # 2. 處理點擊事件
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # 左鍵點擊
                self._handle_click(mouse_pos, active_buttons)

    def _update_hover_state(self, mouse_pos):
        """計算滑鼠目前懸停在哪張手牌上"""
        mouse_x, mouse_y = mouse_pos
        num_tiles = len(self.human_player.hand_card)
        start_x = (UIConfig.SCREEN_WIDTH - (16 * UIConfig.TILE_WIDTH)) // 2
        start_y = UIConfig.MY_HAND_Y
        
        self.hovered_index = -1
        
        # 如果不是出牌狀態，就不顯示懸停浮起特效
        if self.human_player.ui_state != "discard":
            return

        # 簡單的碰撞偵測
        if start_y <= mouse_y <= start_y + UIConfig.TILE_HEIGHT:
            for i in range(num_tiles):
                tile_x = start_x + i * UIConfig.TILE_WIDTH
                
                # 處理抽牌時的間隙
                is_draw_turn = (num_tiles % 3 == 2)
                if is_draw_turn and i == num_tiles - 1:
                    tile_x += 20
                    
                if tile_x <= mouse_x <= tile_x + UIConfig.TILE_WIDTH:
                    self.hovered_index = i
                    break

    def _handle_click(self, mouse_pos, active_buttons):
        """根據目前的 ui_state 分流處理點擊事件"""
        ui_state = self.human_player.ui_state

        if ui_state == "discard":
            # 如果玩家點擊了手牌，且 hovered_index 有抓到目標
            if self.hovered_index != -1:
                self.human_player.gui_response = self.hovered_index
                
        elif ui_state.startswith("wait_"):
            # 判斷是否點擊了「碰、槓、吃、過」按鈕
            for btn in active_buttons:
                if btn.rect.collidepoint(mouse_pos):
                    self.human_player.gui_response = btn.action_value
                    break