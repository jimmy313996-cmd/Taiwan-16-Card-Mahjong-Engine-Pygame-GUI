import pygame
import sys
import os
import threading
import time
from config import UIConfig
from mahjong_controller import MahjongController
from mahjong_engine import (
    MahjongGame, HumanPlayer, MahjongPlayer, ALL_UNIQUE_TILES, 
    total_card_dict, BASE_IDS, Tile, TaiCalculator
)

# 初始化 Pygame
pygame.init()
pygame.font.init()

screen = pygame.display.set_mode((UIConfig.SCREEN_WIDTH, UIConfig.SCREEN_HEIGHT))
pygame.display.set_caption("Taiwan 16-Card Mahjong (MVC Version)")
clock = pygame.time.Clock()

TILE_DIR = "麻將圖"
ui_font = pygame.font.SysFont(['microsoftjhenghei', 'simhei'], 24)

tile_images = {}
small_tile_images = {}

def load_tile_images():
    """載入所有麻將圖片，並同時產生正常版與海底縮小版"""
    back_path = os.path.join(TILE_DIR, "back.png")
    if os.path.exists(back_path):
        img = pygame.image.load(back_path).convert_alpha()
        tile_images["back"] = pygame.transform.scale(img, (UIConfig.TILE_WIDTH, UIConfig.TILE_HEIGHT))
        tile_images["back_rotated"] = pygame.transform.rotate(tile_images["back"], 90)
        
        small_back = pygame.transform.scale(img, (UIConfig.SMALL_W, UIConfig.SMALL_H))
        small_tile_images["back"] = small_back
        small_tile_images["back_left"] = pygame.transform.rotate(small_back, -90)
        small_tile_images["back_right"] = pygame.transform.rotate(small_back, 90)
        small_tile_images["back_top"] = pygame.transform.rotate(small_back, 180)

    ids_to_load = (list(range(101, 110)) + list(range(201, 210)) +
                   list(range(301, 310)) + list(range(401, 405)) +
                   list(range(501, 504)) + list(range(601, 609)))
    
    for tile_id in ids_to_load:
        file_path = os.path.join(TILE_DIR, f"{tile_id}.png")
        if os.path.exists(file_path):
            img = pygame.image.load(file_path).convert_alpha()
            base_img = pygame.transform.scale(img, (UIConfig.TILE_WIDTH, UIConfig.TILE_HEIGHT))
            tile_images[tile_id] = base_img
            
            small_img = pygame.transform.scale(img, (UIConfig.SMALL_W, UIConfig.SMALL_H))
            small_tile_images[tile_id] = small_img
            small_tile_images[f"{tile_id}_left"] = pygame.transform.rotate(small_img, -90)
            small_tile_images[f"{tile_id}_right"] = pygame.transform.rotate(small_img, 90)
            small_tile_images[f"{tile_id}_top"] = pygame.transform.rotate(small_img, 180)

# --- GUI 按鈕類別 ---
class Button:
    def __init__(self, x, y, width, height, text, action_value, color=(70, 130, 180), hover_color=(100, 149, 237)):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action_value = action_value
        self.color = color
        self.hover_color = hover_color
        self.font = pygame.font.SysFont(['microsoftjhenghei', 'simhei'], 28)

    def draw(self, screen, mouse_pos):
        current_color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
        pygame.draw.rect(screen, current_color, self.rect, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), self.rect, width=2, border_radius=8)
        text_surf = self.font.render(self.text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

def get_active_buttons(human_player):
    """根據玩家目前的狀態，回傳對應的按鈕列表"""
    buttons = []
    if human_player.ui_state == "idle" or human_player.ui_state == "discard":
        return buttons

    btn_width, btn_height = 100, 50
    gap = 20
    start_y = UIConfig.SCREEN_HEIGHT - 160
    center_x = UIConfig.SCREEN_WIDTH // 2

    if human_player.ui_state == "wait_peng":
        buttons.append(Button(center_x - btn_width - gap//2, start_y, btn_width, btn_height, "碰", True, color=(200, 50, 50), hover_color=(250, 80, 80)))
        buttons.append(Button(center_x + gap//2, start_y, btn_width, btn_height, "過", False))
    elif human_player.ui_state == "wait_gang":
        buttons.append(Button(center_x - btn_width - gap//2, start_y, btn_width, btn_height, "槓", True, color=(200, 50, 50), hover_color=(250, 80, 80)))
        buttons.append(Button(center_x + gap//2, start_y, btn_width, btn_height, "過", False))
    elif human_player.ui_state == "wait_chow":
        options = human_player.ui_action_data.get('options', [])
        total_btns = len(options) + 1
        total_width = (total_btns * btn_width) + ((total_btns - 1) * gap)
        start_x = center_x - (total_width // 2)
        for i, opt in enumerate(options):
            label = "吃(左)" if opt == 'left' else "吃(中)" if opt == 'middle' else "吃(右)"
            buttons.append(Button(start_x + i * (btn_width + gap), start_y, btn_width, btn_height, label, opt, color=(50, 150, 50), hover_color=(80, 200, 80)))
        buttons.append(Button(start_x + len(options) * (btn_width + gap), start_y, btn_width, btn_height, "過", "pass"))
    elif human_player.ui_state == "wait_hu":
        buttons.append(Button(center_x - btn_width - gap//2, start_y, btn_width, btn_height, "胡", True, color=(200, 50, 50), hover_color=(250, 80, 80)))
        buttons.append(Button(center_x + gap//2, start_y, btn_width, btn_height, "過", False))
    elif human_player.ui_state == "wait_zimo":
        buttons.append(Button(center_x - btn_width - gap//2, start_y, btn_width, btn_height, "自摸", True, color=(200, 50, 50), hover_color=(250, 80, 80)))
        buttons.append(Button(center_x + gap//2, start_y, btn_width, btn_height, "過", False))
    elif human_player.ui_state == "round_end":
        buttons.append(Button(center_x - btn_width - gap//2, start_y, btn_width, btn_height, "下一局", "next_round", color=(218, 165, 32), hover_color=(255, 215, 0)))
        # 新增結束測試按鈕 (灰色系)
        buttons.append(Button(center_x + gap//2, start_y, btn_width, btn_height, "結束測試", "end_test", color=(100, 100, 100), hover_color=(150, 150, 150)))
    return buttons

class MahjongRenderer:
    def __init__(self, screen, font, tile_images, small_tile_images):
        self.screen = screen
        self.font = font
        self.tile_images = tile_images
        self.small_tile_images = small_tile_images

    def draw_all(self, match, human_player, hovered_index=-1, active_buttons=None, mouse_pos=(0,0)):
        self.screen.fill(UIConfig.COLOR_BG)
        
        # 防呆：如果當下沒有遊戲實例，只畫背景就返回
        if not getattr(match, 'current_game', None):
            return
            
        self.draw_river(match)
        self.draw_opponents(match)
        self.draw_self_hand(human_player, hovered_index)
        self.draw_center_info(match)
        
        if active_buttons:
            for btn in active_buttons:
                btn.draw(self.screen, mouse_pos)

    def draw_self_hand(self, human_player, hovered_index):
        start_x = (UIConfig.SCREEN_WIDTH - (16 * UIConfig.TILE_WIDTH)) // 2
        start_y = UIConfig.MY_HAND_Y

        # 花牌
        flower_start_y = start_y - UIConfig.TILE_HEIGHT - 10
        for i, tile in enumerate(human_player.flower_cards):
            if tile.id in self.tile_images:
                self.screen.blit(self.tile_images[tile.id], (start_x + i * UIConfig.TILE_WIDTH, flower_start_y))

        # 手牌
        for i, tile in enumerate(human_player.hand_card):
            if tile.id in self.tile_images:
                y_offset = -15 if i == hovered_index else 0
                x_pos = start_x + i * UIConfig.TILE_WIDTH
                
                is_draw_turn = (len(human_player.hand_card) % 3 == 2)
                is_last_tile = (i == len(human_player.hand_card) - 1)
                is_newly_drawn = (human_player.last_drawn_tile is not None and tile.id == human_player.last_drawn_tile.id)
                
                if is_draw_turn and is_last_tile and is_newly_drawn:
                    x_pos += 20  
                    
                self.screen.blit(self.tile_images[tile.id], (x_pos, start_y + y_offset))

        # 副露
        current_meld_x = UIConfig.MY_MELD_X_START
        for meld in human_player.melds_card:
            tiles_to_draw = self._get_meld_ids(meld)
            meld_width = len(tiles_to_draw) * UIConfig.SMALL_W
            current_meld_x -= meld_width
            
            draw_x = current_meld_x
            for t_id in tiles_to_draw:
                meld_y = start_y + (UIConfig.TILE_HEIGHT - UIConfig.SMALL_H) - 10
                if t_id == 'back' and 'back' in self.small_tile_images:
                    self.screen.blit(self.small_tile_images['back'], (draw_x, meld_y))
                elif t_id in self.small_tile_images:
                    self.screen.blit(self.small_tile_images[t_id], (draw_x, meld_y))
                draw_x += UIConfig.SMALL_W  
            current_meld_x -= 10

    def draw_opponents(self, match):
        overlap_step = UIConfig.TILE_WIDTH - 12  
        MELD_GAP = 12

        p2_hand_len = len(match.players[2].hand_card)
        p2_hand_w = p2_hand_len * UIConfig.TILE_WIDTH
        p2_meld_w = sum(len(self._get_meld_ids(m)) * UIConfig.SMALL_W + MELD_GAP for m in match.players[2].melds_card)
        p2_total_w = p2_hand_w + p2_meld_w + (40 if p2_meld_w > 0 else 0)
        p2_start_x = (UIConfig.SCREEN_WIDTH - p2_total_w) // 2

        p1_hand_len = len(match.players[1].hand_card)
        p1_hand_h = max(0, p1_hand_len - 1) * overlap_step + UIConfig.TILE_WIDTH if p1_hand_len > 0 else 0
        p1_meld_h = sum(len(self._get_meld_ids(m)) * UIConfig.SMALL_W + MELD_GAP for m in match.players[1].melds_card)
        p1_total_h = p1_hand_h + p1_meld_h + (20 if p1_meld_h > 0 else 0)
        p1_start_y = (UIConfig.SCREEN_HEIGHT - p1_total_h) // 2

        p3_hand_len = len(match.players[3].hand_card)
        p3_hand_h = max(0, p3_hand_len - 1) * overlap_step + UIConfig.TILE_WIDTH if p3_hand_len > 0 else 0
        p3_meld_h = sum(len(self._get_meld_ids(m)) * UIConfig.SMALL_W + MELD_GAP for m in match.players[3].melds_card)
        p3_total_h = p3_hand_h + p3_meld_h + (20 if p3_meld_h > 0 else 0)
        p3_start_y = (UIConfig.SCREEN_HEIGHT - p3_total_h) // 2

        for i in range(len(match.players[3].hand_card)):
            self.screen.blit(self.tile_images.get("back_rotated", pygame.Surface((0,0))), (40, p3_start_y + i * overlap_step))
        for i in range(len(match.players[2].hand_card)):
            self.screen.blit(self.tile_images.get("back", pygame.Surface((0,0))), (p2_start_x + i * UIConfig.TILE_WIDTH, 20))
        for i in range(len(match.players[1].hand_card)):
            self.screen.blit(self.tile_images.get("back_rotated", pygame.Surface((0,0))), (UIConfig.SCREEN_WIDTH - 40 - UIConfig.TILE_HEIGHT, p1_start_y + i * overlap_step))

        p2_meld_x = p2_start_x + p2_hand_w + 40
        for meld in match.players[2].melds_card:
            for t_id in self._get_meld_ids(meld):
                img = self.small_tile_images.get('back_top') if t_id == 'back' else self.small_tile_images.get(f"{t_id}_top")
                if img: self.screen.blit(img, (p2_meld_x, 20))
                p2_meld_x += UIConfig.SMALL_W
            p2_meld_x += MELD_GAP

        p1_meld_y = p1_start_y + p1_hand_h + 20
        for meld in match.players[1].melds_card:
            for t_id in self._get_meld_ids(meld):
                img = self.small_tile_images.get('back_right') if t_id == 'back' else self.small_tile_images.get(f"{t_id}_right")
                if img: self.screen.blit(img, (UIConfig.SCREEN_WIDTH - 40 - UIConfig.TILE_HEIGHT, p1_meld_y))
                p1_meld_y += UIConfig.SMALL_W
            p1_meld_y += MELD_GAP

        p3_meld_y = p3_start_y + p3_hand_h + 20
        for meld in match.players[3].melds_card:
            for t_id in self._get_meld_ids(meld):
                img = self.small_tile_images.get('back_left') if t_id == 'back' else self.small_tile_images.get(f"{t_id}_left")
                if img: self.screen.blit(img, (40, p3_meld_y))
                p3_meld_y += UIConfig.SMALL_W
            p3_meld_y += MELD_GAP

    def draw_center_info(self, match):
        center_x, center_y = UIConfig.SCREEN_WIDTH // 2, UIConfig.SCREEN_HEIGHT // 2
        center_rect_width, center_rect_height = 240, 130
        center_rect = pygame.Rect(center_x - center_rect_width // 2, center_y - center_rect_height // 2, center_rect_width, center_rect_height)
        
        pygame.draw.rect(self.screen, (30, 80, 30), center_rect, border_radius=12)
        pygame.draw.rect(self.screen, (218, 165, 32), center_rect, width=3, border_radius=12)

        wind_names = ["東", "南", "西", "北"]
        current_wind = match.winds[match.current_wind_idx]
        dealer_name = wind_names[match.dealer_index]
        
        round_text = f"{current_wind}風{dealer_name}局 (連{match.dealer_streak})"
        text_round = self.font.render(round_text, True, (255, 255, 255))
        self.screen.blit(text_round, (center_x - text_round.get_width() // 2, center_y - 40))

        if getattr(match, 'current_game', None):
            remaining_tiles = len(match.current_game.deck)
            text_deck = self.font.render(f"剩餘牌數: {remaining_tiles}", True, (255, 215, 0))
            self.screen.blit(text_deck, (center_x - text_deck.get_width() // 2, center_y - 5))

            active_player_name = match.players[match.current_game.current_turn].name
            text_turn = self.font.render(f"目前輪到: {active_player_name}", True, (150, 255, 150))
            self.screen.blit(text_turn, (center_x - text_turn.get_width() // 2, center_y + 30))

        for i, p in enumerate(match.players):
            text_surf = self.font.render(f"{p.name} : {p.chips}", True, (255, 255, 255))
            
            if i == 0:  
                text_rect = text_surf.get_rect(midbottom=(center_x, UIConfig.INFO_MY_Y))
            elif i == 1:
                text_rect = text_surf.get_rect(midright=(UIConfig.SCREEN_WIDTH - 20, center_y))
            elif i == 2:
                text_rect = text_surf.get_rect(midtop=(center_x, UIConfig.INFO_OPP_TOP_Y))
            elif i == 3:
                text_rect = text_surf.get_rect(midleft=(UIConfig.INFO_OPP_LEFT_X, center_y))
                
            self.screen.blit(text_surf, text_rect)

            if i == match.dealer_index:
                dealer_surf = self.font.render(f"莊家 連{match.dealer_streak}", True, (255, 215, 0))
                
                if i == 0:
                    dealer_rect = dealer_surf.get_rect(midbottom=(text_rect.centerx, text_rect.top - 8))
                elif i == 1:
                    dealer_rect = dealer_surf.get_rect(midright=(text_rect.left - 12, text_rect.centery))
                elif i == 2:
                    dealer_rect = dealer_surf.get_rect(midtop=(text_rect.centerx, text_rect.bottom + 8))
                elif i == 3:
                    dealer_rect = dealer_surf.get_rect(midleft=(text_rect.right + 12, text_rect.centery))
                
                bg_rect = dealer_rect.inflate(16, 8)
                pygame.draw.rect(self.screen, (255, 215, 0), bg_rect, width=2, border_radius=5)
                self.screen.blit(dealer_surf, dealer_rect)

    def draw_river(self, match):
        if not getattr(match, 'current_game', None):
            return
        center_x, center_y = UIConfig.SCREEN_WIDTH // 2, UIConfig.SCREEN_HEIGHT // 2
        history = match.discarded_history
        discard_offsets = {
            0: (center_x - (6 * UIConfig.SMALL_W) // 2, center_y + 80),
            1: (center_x + 200, center_y - (6 * UIConfig.SMALL_W) // 2),
            2: (center_x + (6 * UIConfig.SMALL_W) // 2, center_y - 120),
            3: (center_x - 200 - UIConfig.SMALL_H, center_y + (6 * UIConfig.SMALL_W) // 2)
        }
        discard_counts = {0: 0, 1: 0, 2: 0, 3: 0}
        
        for record in history:
            p_idx = record['player_index']
            tile = record['tile']
            count = discard_counts[p_idx]
            row, col = count // 6, count % 6
            
            dx, dy = 0, 0
            img = None
            if p_idx == 0:
                dx, dy = discard_offsets[0][0] + col * UIConfig.SMALL_W, discard_offsets[0][1] + row * UIConfig.SMALL_H
                img = self.small_tile_images.get(tile.id)
            elif p_idx == 1:
                dx, dy = discard_offsets[1][0] + row * UIConfig.SMALL_H, discard_offsets[1][1] + col * UIConfig.SMALL_W
                img = self.small_tile_images.get(f"{tile.id}_right")
            elif p_idx == 2:
                dx, dy = discard_offsets[2][0] - col * UIConfig.SMALL_W, discard_offsets[2][1] - row * UIConfig.SMALL_H
                img = self.small_tile_images.get(f"{tile.id}_top")
            elif p_idx == 3:
                dx, dy = discard_offsets[3][0] - row * UIConfig.SMALL_H, discard_offsets[3][1] - col * UIConfig.SMALL_W
                img = self.small_tile_images.get(f"{tile.id}_left")
            
            if img: self.screen.blit(img, (dx, dy))
            discard_counts[p_idx] += 1

    def _get_meld_ids(self, meld):
        if meld['type'] in ['peng', 'gang', 'bu_gang']:
            return [meld['tile'].id] * meld.get('count', 3)
        elif meld['type'] == 'an_gang':
            return ['back'] * 4
        elif meld['type'] == 'chow':
            return [t.id for t in meld['tiles']]
        return []

# === 假洗牌發牌輔助函式 ===
def setup_deck_and_deal(players):
    import random
    deck = []
    
    for category, sub_dict in total_card_dict.items():
        base_id = BASE_IDS[category]
        for i, (card_name, count) in enumerate(sub_dict.items(), start=1):
            id_val = base_id + int(card_name) if card_name.isdigit() else base_id + i
            for _ in range(count):
                deck.append(Tile(category, card_name, id_val))
                
    random.shuffle(deck)
    
    for p in players:
        p.reset_for_new_round()
        for _ in range(16):
            p.hand_card.append(deck.pop())
            
        p.check_and_bu_hua(deck)  # 先執行補花替換
        p.hand_card.sort()        # 補花完成後再進行最終排序
        
        p.last_drawn_tile = None  # 清除起手補花的摸牌標記，防止渲染器產生多餘間距
        
    return deck

# === 🔥 新增：MahjongMatch 多局對戰與線程管理者 ===
class MahjongMatch:
    def __init__(self, players):
        self.players = players
        self.winds = ["東", "南", "西", "北"]
        self.current_wind_idx = 0
        self.dealer_index = 0
        self.dealer_streak = 0
        self.current_game = None
        self.discarded_history = []
        self.running = False
        self.thread = None

    def start_match_thread(self):
        self.running = True
        self.thread = threading.Thread(target=self._match_loop, daemon=True)
        self.thread.start()

    def stop_match(self):
        self.running = False

    def _match_loop(self):
        while self.running:
            deck = setup_deck_and_deal(self.players)
            self.current_game = MahjongGame(
                players=self.players,
                deck=deck,
                all_unique_tiles=ALL_UNIQUE_TILES,
                round_wind=self.winds[self.current_wind_idx],
                dealer_index=self.dealer_index,
                dealer_streak=self.dealer_streak
            )
            self.discarded_history = self.current_game.discarded_history

            # 執行單局遊戲迴圈
            while not self.current_game.is_over and self.running:
                try:
                    self.current_game.start_turn()
                except InterruptedError:
                    print("[系統] 收到玩家中斷訊號，停止當前局。")
                    break
                except Exception as e:
                    print(f"[系統] 遊戲運行異常: {e}")
                    break

            if not self.running:
                break

            # 局結束處理（結算與莊家轉換）
            self._handle_round_end()
            # time.sleep(3)   
            human = next((p for p in self.players if getattr(p, 'is_human', False)), None)
            if human:
                human.ui_state = "round_end"
                human._wait_for_gui()  # 引擎線程會在這裡安全地掛起，直到玩家點擊按鈕

    def _handle_round_end(self):
        game = self.current_game
        if not game:
            return

        if game.winner:
            winner_idx = self.players.index(game.winner)
            try:
                is_self_drawn = (game.shooter is None)
                game_context = {
                    'round_wind': self.winds[self.current_wind_idx],
                    'dealer_index': self.dealer_index,
                    'player_index': winner_idx,
                    'is_lever_congenial': getattr(game, 'is_lever_congenial', False),
                    'is_rob_gang': getattr(game, 'is_rob_gang', False),
                    'is_hai_di_lao_yue': getattr(game, 'is_hai_di_lao_yue', False),
                    'is_he_di_lao_yu': getattr(game, 'is_he_di_lao_yu', False),
                    'is_tian_hu': getattr(game, 'is_tian_hu', False),
                    'is_di_hu': getattr(game, 'is_di_hu', False),
                    'is_ren_hu': getattr(game, 'is_ren_hu', False),
                    'is_qi_qiang_yi': getattr(game, 'is_qi_qiang_yi', False),
                    'is_ba_xian_guo_hai': getattr(game, 'is_ba_xian_guo_hai', False)
                }
                winning_tile = getattr(game, 'winning_tile', None)
                tai, details = TaiCalculator.calculate_tai(game.winner, winning_tile, is_self_drawn, game_context)
                print(f"\n🎉 [局結束] 胡牌玩家：{game.winner.name}！共 {tai} 台")
                for name, score in details.items():
                    print(f"   - {name}: {score} 台")
                
                # =================🔥 新增：實體籌碼結算邏輯 =================
                BASE_SCORE = 300  # 底 (可依需求調整，如 100)
                TAI_SCORE = 100   # 每台分數 (可依需求調整，如 20)
                
                # 計算莊家台數：基本莊家 1 台 + (連莊次數 * 2)
                dealer_tai = 1 + (2 * self.dealer_streak)

                if is_self_drawn:
                    print(f"💰 {game.winner.name} 自摸！收三家。")
                    for i, p in enumerate(self.players):
                        if p != game.winner:
                            # 判斷贏家或當前輸家是否為莊家，若是則需加上莊家台
                            extra_tai = dealer_tai if (winner_idx == self.dealer_index or i == self.dealer_index) else 0
                            settlement_tai = tai + extra_tai
                            lose_amount = BASE_SCORE + (settlement_tai * TAI_SCORE)
                            
                            p.chips -= lose_amount
                            game.winner.chips += lose_amount
                            print(f"   💸 {p.name} 賠付 {lose_amount} (包含台數:{tai} + 莊家台:{extra_tai})")
                else:
                    if game.shooter:
                        print(f"🎯 {game.shooter.name} 放槍！單賠給 {game.winner.name}。")
                        shooter_idx = self.players.index(game.shooter)
                        
                        # 判斷贏家或放槍者是否為莊家，若是則需加上莊家台
                        extra_tai = dealer_tai if (winner_idx == self.dealer_index or shooter_idx == self.dealer_index) else 0
                        settlement_tai = tai + extra_tai
                        lose_amount = BASE_SCORE + (settlement_tai * TAI_SCORE)
                        
                        game.shooter.chips -= lose_amount
                        game.winner.chips += lose_amount
                        print(f"   💸 {game.shooter.name} 賠付 {lose_amount} (包含台數:{tai} + 莊家台:{extra_tai})")
                # =========================================================

            except Exception as e:
                print(f"[警告] 計算台數時發生異常: {e}")

            if winner_idx == self.dealer_index:
                self.dealer_streak += 1
                print(f"👑 莊家連莊！連 {self.dealer_streak}")
            else:
                self._rotate_dealer()
        else:
            self.dealer_streak += 1
            print(f"⏸️ 本局流局，莊家連莊！連 {self.dealer_streak}")

    def _rotate_dealer(self):
        self.dealer_index = (self.dealer_index + 1) % 4
        self.dealer_streak = 0
        if self.dealer_index == 0:
            self.current_wind_idx = (self.current_wind_idx + 1) % 4


    def generate_report(self):
        print("\n" + "="*40)
        print("📊 測試結果總結報告 (Match Report)")
        print("="*40)
        
        # 依籌碼多寡排序玩家
        sorted_players = sorted(self.players, key=lambda p: p.chips, reverse=True)
        
        for rank, p in enumerate(sorted_players, 1):
            # 預設起始籌碼為 5000
            profit = p.chips - 5000  
            profit_str = f"+{profit}" if profit > 0 else str(profit)
            print(f"第 {rank} 名: {p.name:<8} | 總籌碼: {p.chips:<6} | 淨利: {profit_str}")
        print("="*40)

# --- 主程式與遊戲迴圈 ---
def main():
    load_tile_images()
    renderer = MahjongRenderer(screen, ui_font, tile_images, small_tile_images)
    
    # 1. 初始化引擎玩家 (Model)
    human = HumanPlayer("玩家")
    cpu1 = MahjongPlayer("CPU_右")
    cpu2 = MahjongPlayer("CPU_對")
    cpu3 = MahjongPlayer("CPU_左")
    
    # 使用 Match 管理多局，並啟動背景引擎
    match = MahjongMatch([human, cpu1, cpu2, cpu3])
    match.start_match_thread()
    
    # 初始化控制器 (Controller)
    controller = MahjongController(human)
    running = True
    
    while running:
        mouse_pos = pygame.mouse.get_pos()
        active_buttons = get_active_buttons(human)

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                human.gui_response = -1 # 解除卡死防護
                match.stop_match()      # 安全停止引擎
                running = False
                
            # 🔥 新增修正處：手動攔截滑鼠左鍵點擊，補足 Controller 漏接的 next_round 指令
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for btn in active_buttons:
                    if btn.rect.collidepoint(event.pos):
                        if btn.action_value == "next_round":
                            human.gui_response = "next_round"
                        elif btn.action_value == "end_test":
                            # 1. 解除引擎卡死並安全中斷[cite: 36]
                            human.gui_response = -1   
                            # 2. 停止背景對戰迴圈
                            match.stop_match()        
                            # 3. 輸出結算報表
                            match.generate_report()   
                            # 4. 關閉 Pygame 視窗
                            running = False
        # 讓原本的 Controller 繼續處理打牌、吃碰槓等一般邏輯
        controller.handle_events(events, active_buttons)

        renderer.draw_all(match, human, hovered_index=controller.hovered_index, active_buttons=active_buttons, mouse_pos=mouse_pos)
        
        pygame.display.flip()
        clock.tick(UIConfig.FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()