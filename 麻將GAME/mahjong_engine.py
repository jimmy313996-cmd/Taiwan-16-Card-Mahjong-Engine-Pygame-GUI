import random
import time  # 🌟 新增：用於 GUI 阻擋等待
from collections import Counter
import threading

total_card_dict = {
    'cake': {'1': 4, '2': 4, '3': 4, '4': 4, '5': 4, '6': 4, '7': 4, '8': 4, '9': 4},
    'strip': {'1': 4, '2': 4, '3': 4, '4': 4, '5': 4, '6': 4, '7': 4, '8': 4, '9': 4},
    'tenthousand': {'1': 4, '2': 4, '3': 4, '4': 4, '5': 4, '6': 4, '7': 4, '8': 4, '9': 4},
    'FlowerPlaque': {'spring': 1, 'summer': 1, 'autumn': 1, 'winter': 1, 'plum': 1, 'orchid': 1, 'bamboo': 1, 'chrysanthemum': 1},
    'wind': {'east': 4, 'south': 4, 'west': 4, 'north': 4}, 
    'threeyuan': {'mid': 4, 'rich': 4, 'white': 4}         
}

# ==================== 🎴 全域輔助變數 ====================
BASE_IDS = {
    'cake': 100, 'strip': 200, 'tenthousand': 300,
    'wind': 400, 'threeyuan': 500, 'FlowerPlaque': 600
}


class Tile:# id排序查詢
    def __init__(self, category, value, id_val):
        self.category = category  
        self.value = value
        self.id = id_val
    
    def __repr__(self):# 印出牌的樣子
        return f'{self.value}-{self.category}'    

    def __lt__(self, other):# 讓牌物件可以直接用 < 來比較大小
        return self.id < other.id
    
    def __eq__(self, other):# 讓牌物件可以直接用 == 來比較是否相同
        if not isinstance(other, Tile):
            return False
        return self.id == other.id

# ==================== 🎴 全域不重複牌模板 (用於聽牌判定與 CPU 預測) ====================
def generate_all_unique_tiles():
    unique_tiles = []
    for category, sub_dict in total_card_dict.items():
        base_id = BASE_IDS[category]
        for i, (card_name, _) in enumerate(sub_dict.items(), start=1):
            id_val = base_id + int(card_name) if card_name.isdigit() else base_id + i
            unique_tiles.append(Tile(category, card_name, id_val))
    return unique_tiles

ALL_UNIQUE_TILES = generate_all_unique_tiles()

# ==================== 🎴 1. 玩家類別（注入 GUI 狀態標籤與等待機制） ====================
class MahjongPlayer:
    def __init__(self, name, starting_chips=5000, difficulty="advanced", playstyle="balanced"):
        self.name = name
        self.chips = starting_chips  
        self.difficulty = difficulty       
        self.playstyle = playstyle   
        self.hand_card = []   
        self.melds_card = []  
        self.flower_cards = [] 
        self.is_guo_shui = False        
        self.is_declared_ting = False    
        self.last_drawn_tile = None      

        # 🌟 ================= GUI 專屬通訊變數 ================= 🌟
        self.ui_state = "idle"            # 當前狀態："idle"(閒置), "discard"(等打牌), "meld"(等碰槓), "chow"(等吃牌)
        self.ui_action_data = None        # 傳遞給 GUI 的額外資料 (例如：可以吃牌的組合、要碰的那張牌)
        self.gui_response = None          # 用來接收 GUI (滑鼠點擊) 傳回來的決策結果
        # =========================================================

    def reset_for_new_round(self):
        """🧹 每局結束後，徹底清空手牌與副露"""
        self.hand_card = []
        self.melds_card = []
        self.flower_cards = []
        self.is_guo_shui = False
        self.is_declared_ting = False
        self.last_drawn_tile = None
        self.ui_state = "idle"
        self.ui_action_data = None
        self.gui_response = None

    def draw_tile(self, deck):
        if deck:
            tile = deck.pop()
            self.hand_card.append(tile)
            # self.hand_card.sort()  # 🌟 刪除或註解這行，讓新牌保留在最右側
            return tile
        return None

    def check_and_bu_hua(self, deck):
        last_drawn = None 
        while True:
            flower_tiles = [tile for tile in self.hand_card if tile.category == 'FlowerPlaque']
            if not flower_tiles:
                break
            for tile in flower_tiles:
                self.hand_card.remove(tile)
                self.flower_cards.append(tile)
                print(f"🌸 {self.name} 補花！公開花牌：【{tile}】")
                if deck:
                    new_tile = deck.pop()
                    self.hand_card.append(new_tile)
                    last_drawn = new_tile 
                    print(f"✨ {self.name} 補花摸到：【{new_tile}】")
            # self.hand_card.sort() # 🌟 刪除或註解這行
        return last_drawn # 回傳最後一張有效牌

    def discard_tile(self, tile_index):
        popped_tile = self.hand_card.pop(tile_index)
        self.hand_card.sort() # 🌟 新增：玩家打完牌後，才將剩餘的手牌重新排序
        return popped_tile

    def check_peng(self, discarded_tile): 
        same_cards_count = sum(1 for tile in self.hand_card if tile.id == discarded_tile.id)
        return same_cards_count >= 2

    def peng(self, tile): 
        for _ in range(2):
            self.hand_card.remove(tile)
        self.melds_card.append({'type': 'peng', 'tile': tile, 'count': 3})
        self.hand_card.sort()          # 🌟 新增排序
        self.last_drawn_tile = None    # 🌟 清除摸牌標記
    
    def check_gang(self, discarded_tile):
        same_cards_count = sum(1 for tile in self.hand_card if tile.id == discarded_tile.id)
        return same_cards_count == 3

    def gang(self, tile): 
            for _ in range(3):
                self.hand_card.remove(tile)
            self.melds_card.append({'type': 'gang', 'tile': tile, 'count': 4})
            self.hand_card.sort()          # 🌟 新增排序
            self.last_drawn_tile = None    # 🌟 清除摸牌標記

    # def check_self_gang(self):
    #     id_counts = {}
    #     for tile in self.hand_card:
    #         id_counts[tile.id] = id_counts.get(tile.id, 0) + 1
    #     for tile_id, count in id_counts.items():
    #         if count == 4:
    #             target_tile = next(tile for tile in self.hand_card if tile.id == tile_id)
    #             return {'type': 'an_gang', 'tile': target_tile}
    #     for tile in self.hand_card:
    #         for meld in self.melds_card:
    #             if meld['type'] == 'peng' and meld['tile'].id == tile.id:
    #                 return {'type': 'bu_gang', 'tile': tile}
    #     return None

    def execute_self_gang(self, gang_info):
            tile = gang_info['tile']
            if gang_info['type'] == 'an_gang':
                for _ in range(4):
                    self.hand_card.remove(tile)
                self.melds_card.append({'type': 'an_gang', 'tile': tile, 'count': 4})
                print(f"🔒 {self.name} 執行了【暗槓】: {tile}")
            elif gang_info['type'] == 'bu_gang':
                self.hand_card.remove(tile)
                for meld in self.melds_card:
                    if meld['type'] == 'peng' and meld['tile'].id == tile.id:
                        meld['type'] = 'bu_gang'
                        meld['count'] = 4
                        break
                print(f"➕ {self.name} 執行了【補槓】: {tile}")
            self.hand_card.sort()          # 🌟 新增排序
            self.last_drawn_tile = None    # 🌟 清除摸牌標記

    def check_chow(self, discarded_tile):
        target_id = discarded_tile.id
        if target_id >= 400: return []
        hand_ids = {tile.id for tile in self.hand_card}
        rank = target_id % 100 
        can_chow_combinations = []
        if rank >= 3:
            if (target_id - 2) in hand_ids and (target_id - 1) in hand_ids: can_chow_combinations.append('right')
        if 2 <= rank <= 8:
            if (target_id - 1) in hand_ids and (target_id + 1) in hand_ids: can_chow_combinations.append('middle')
        if rank <= 7:
            if (target_id + 1) in hand_ids and (target_id + 2) in hand_ids: can_chow_combinations.append('left')
        return can_chow_combinations

    def execute_chow(self, discarded_tile, chow_type):
        target_id = discarded_tile.id
        if chow_type == 'right': needed_ids = [target_id - 2, target_id - 1]
        elif chow_type == 'middle': needed_ids = [target_id - 1, target_id + 1]
        elif chow_type == 'left': needed_ids = [target_id + 1, target_id + 2]
        else: return False

        removed_tiles = []
        for n_id in needed_ids:
            for tile in self.hand_card:
                if tile.id == n_id:
                    self.hand_card.remove(tile)
                    removed_tiles.append(tile)
                    break 
        meld_combination = removed_tiles + [discarded_tile]
        meld_combination.sort(key=lambda x: x.id)  
        self.melds_card.append({'type': 'chow', 'tiles': meld_combination})
        print(f"【系統】{self.name} 執行了吃牌！組合為: {meld_combination}")
        self.hand_card.sort()          # 🌟 新增排序
        self.last_drawn_tile = None    # 🌟 清除摸牌標記
        return True

    def cpu_choose_discard(self, visible_counts, river_ids, all_possible_tiles=None, opponents=None):
        """ 🧠 智慧型 CPU 打牌大腦 """
        tile_scores = []
        hand_counts = Counter(t.id for t in self.hand_card)
        total_discarded = len(river_ids)
        
        threat_suits = set()
        is_anyone_ting = False
        
        if opponents:
            for opp in opponents:
                if opp.is_declared_ting:
                    is_anyone_ting = True
                    
                suit_counts = {'cake': 0, 'strip': 0, 'tenthousand': 0}
                for meld in opp.melds_card:
                    if meld['type'] == 'chow':
                        cat = meld['tiles'][0].category  
                    else:
                        cat = meld['tile'].category      
                        
                    if cat in suit_counts:
                        suit_counts[cat] += 1
                for suit, count in suit_counts.items():
                    if count >= 2: 
                        threat_suits.add(suit)

        is_late_game = total_discarded > 36 or is_anyone_ting 
        
        is_ting = getattr(self, 'is_ting', False)
        if not is_ting and hasattr(self, 'check_ting'):
            if all_possible_tiles:
                is_ting = bool(self.check_ting(all_possible_tiles))
            else:
                is_ting = False 
            
        if is_late_game and not is_ting:
            current_mode = "DEFEND"   
        elif is_late_game and is_ting:
            current_mode = "RUSH"     
        else:
            current_mode = "ATTACK"   
            
        atk_multiplier = 1.0
        def_multiplier = 1.0
        if getattr(self, 'playstyle', 'balanced') == "aggressive":
            atk_multiplier = 1.5
            def_multiplier = 0.4
        elif getattr(self, 'playstyle', 'balanced') == "conservative":
            atk_multiplier = 0.8
            def_multiplier = 1.8
            
        for idx, tile in enumerate(self.hand_card):
            t_id = tile.id
            is_honor = (t_id >= 400) 
            
            danger_score = 0
            seen_count = visible_counts.get(t_id, 0)
            if t_id in river_ids:            danger_score -= river_ids.count(t_id) * 15 
            if seen_count == 4:              danger_score -= 50
            elif is_honor and seen_count>=2: danger_score -= 30 
            if not is_honor:
                num = t_id % 10
                if num in [4, 5, 6]: danger_score += 15 
                elif num in [1, 9]:  danger_score += 2  
            else:
                danger_score += 5 
            if seen_count == 0: danger_score += 30 
            
            if tile.category in threat_suits:
                danger_score += 40 
                
            if is_anyone_ting and seen_count == 0:
                danger_score += 50 

            attack_score = 0
            if hand_counts[t_id] == 2: attack_score -= 25  
            elif hand_counts[t_id] >= 3: attack_score -= 45  

            if hand_counts[t_id] == 1:
                if is_honor: attack_score += 40  
                else:
                    rank = t_id % 100
                    # 嚴格校驗邊界，利用 rank 阻擋跨花色查詢
                    has_neighbor_1 = ((rank < 9 and t_id + 1 in hand_counts) or 
                                      (rank > 1 and t_id - 1 in hand_counts))
                    has_neighbor_2 = ((rank < 8 and t_id + 2 in hand_counts) or 
                                      (rank > 2 and t_id - 2 in hand_counts))
                    
                    if has_neighbor_1: attack_score -= 20  
                    elif has_neighbor_2: attack_score -= 10  
                    else:
                        num = t_id % 10
                        if num in [1, 9]: attack_score += 30  
                        elif num in [2, 8]: attack_score += 25  
                        else: attack_score += 20  

            random_noise = random.uniform(-5.0, 5.0)

            if current_mode == "DEFEND":
                final_weight = -(danger_score * def_multiplier) + (attack_score * 0.1 * atk_multiplier) + random_noise
            elif current_mode == "RUSH":
                final_weight = (attack_score * atk_multiplier) - (danger_score * 0.1 * def_multiplier) + random_noise
            else: 
                final_weight = (attack_score * atk_multiplier) - (danger_score * 0.2 * def_multiplier) + random_noise
                
            tile_scores.append((idx, final_weight, tile, danger_score))
            
        tile_scores.sort(key=lambda x: x[1], reverse=True)
        chosen_idx = tile_scores[0][0]
        chosen_tile = tile_scores[0][2]
        chosen_danger = tile_scores[0][3]
        
        if current_mode == "DEFEND":
            if chosen_danger > 10:
                print(f" 🛡️  [{self.name}] 進入防守狀態！但忍痛打出：{chosen_tile}")
            else:
                print(f" 🛡️  [{self.name}] 察覺危險，選擇縮！跟打安全牌：{chosen_tile}")
                
        return chosen_idx

    def check_self_gang(self, ignore_ids=None):
        if ignore_ids is None:
            ignore_ids = []
            
        id_counts = {}
        for t in self.hand_card:
            id_counts[t.id] = id_counts.get(t.id, 0) + 1
            
        # 1. 檢查暗槓（排除已拒絕的 ID）
        for tile_id, count in id_counts.items():
            if count == 4 and tile_id not in ignore_ids:
                target_tile = next(t for t in self.hand_card if t.id == tile_id)
                return {'type': 'an_gang', 'tile': target_tile}
                
        # 2. 檢查補槓（排除已拒絕的 ID）
        for t in self.hand_card:
            if t.id in ignore_ids:
                continue
            for meld in self.melds_card:
                # 確保這裡的變數名稱一致使用 t，避免找不到 tile 的 UnboundLocalError
                if meld['type'] == 'peng' and meld['tile'].id == t.id:
                    return {'type': 'bu_gang', 'tile': t}
                    
        return None

    def cpu_should_meld(self, tile, action,  visible_counts, chow_type=None):
        if self.difficulty == "normal":
            return True  
            
        base_potential = self._calculate_hand_potential(self.hand_card, visible_counts)
        simulated_hand = list(self.hand_card)
        
        if action in ['peng', 'gang']:
            remove_count = 2 if action == 'peng' else 3
            count = 0
            for t in list(simulated_hand):
                if t.id == tile.id and count < remove_count:
                    simulated_hand.remove(t)
                    count += 1
        elif action == 'chow':
            target_id = tile.id
            if chow_type == 'right': needed_ids = [target_id - 2, target_id - 1]
            elif chow_type == 'middle': needed_ids = [target_id - 1, target_id + 1]
            elif chow_type == 'left': needed_ids = [target_id + 1, target_id + 2]
            else: return False
            
            for n_id in needed_ids:
                for t in list(simulated_hand):
                    if t.id == n_id:
                        simulated_hand.remove(t)
                        break
                        
        after_potential = self._calculate_hand_potential(simulated_hand, visible_counts)
        
        meld_bonus = 0
        if action == 'peng': meld_bonus = 20    
        elif action == 'gang': meld_bonus = 25  
        elif action == 'chow': meld_bonus = 12  
        
        is_currently_concealed = not any(m['type'] in ['peng', 'chow', 'bu_gang', 'gang'] for m in self.melds_card)
        if is_currently_concealed:
            meld_bonus -= 12  
            
        return (after_potential + meld_bonus) >= base_potential
    

    def _calculate_hand_potential(self, simulated_hand, visible_counts):
        hand_ids = [tile.id for tile in simulated_hand]
        id_counts = Counter(hand_ids)
        potential_score = 0
        
        for t_id, count in id_counts.items():
            remaining_in_wild = max(0, 4 - visible_counts.get(t_id, 0))
            if count >= 3:
                potential_score += 40  
            elif count == 2:
                potential_score += remaining_in_wild * 4  
            elif count == 1:
                potential_score += remaining_in_wild * 1  
            
            if t_id < 400:
                if (t_id + 1) in id_counts:
                    rem_left = max(0, 4 - visible_counts.get(t_id - 1, 0)) if (t_id % 100) > 1 else 0
                    rem_right = max(0, 4 - visible_counts.get(t_id + 2, 0)) if (t_id % 100) < 8 else 0
                    potential_score += (rem_left + rem_right) * 2
                
                if (t_id + 2) in id_counts:
                    rem_mid = max(0, 4 - visible_counts.get(t_id + 1, 0))
                    potential_score += rem_mid * 1.5
                    
        return potential_score
    
    def check_hu(self, new_tile=None):
        test_ids = [tile.id for tile in self.hand_card]
        if new_tile: test_ids.append(new_tile.id)
        if len(test_ids) % 3 != 2: return False
        
        counts = {}
        for t_id in test_ids: counts[t_id] = counts.get(t_id, 0) + 1
        
        is_concealed = not any(m['type'] in ['peng', 'chow', 'bu_gang', 'gang'] for m in self.melds_card)
        if is_concealed and len(test_ids) == 17:
            pairs_in_hand = sum(1 for c in counts.values() if c == 2)
            quads_in_hand = sum(1 for c in counts.values() if c == 4)
            if pairs_in_hand + quads_in_hand * 2 == 8:
                return True 

        for t_id, count in counts.items():
            if count >= 2:
                temp_counts = counts.copy()
                temp_counts[t_id] -= 2
                if self._can_form_melds(temp_counts): return True
        return False

    def _can_form_melds(self, counts):
        first_id = None
        for t_id in sorted(counts.keys()):
            if counts[t_id] > 0:
                first_id = t_id
                break
        if first_id is None: return True
        if counts[first_id] >= 3:
            counts[first_id] -= 3
            if self._can_form_melds(counts): return True
            counts[first_id] += 3 
        if first_id < 400:
            if counts.get(first_id + 1, 0) > 0 and counts.get(first_id + 2, 0) > 0:
                counts[first_id] -= 1
                counts[first_id + 1] -= 1
                counts[first_id + 2] -= 1
                if self._can_form_melds(counts): return True
                counts[first_id] += 1
                counts[first_id + 1] += 1
                counts[first_id + 2] += 1
        return False
    
    def check_ting(self, all_possible_tiles):
        ting_list = []
        for tile in all_possible_tiles:
            if self.check_hu(tile): ting_list.append(tile)
        return ting_list
    
    def choose_chow_option(self, tile, chow_options, visible_counts=None):
        if not chow_options:
            return None
            
        v_counts = visible_counts if visible_counts else {}
        base_potential = self._calculate_hand_potential(self.hand_card, v_counts)
        
        best_option = None
        max_score = -999
        target_id = tile.id
        
        for opt_type in chow_options:
            simulated_hand = self.hand_card.copy()
            
            if opt_type == 'right':    needed_ids = [target_id - 2, target_id - 1]
            elif opt_type == 'middle': needed_ids = [target_id - 1, target_id + 1]
            elif opt_type == 'left':   needed_ids = [target_id + 1, target_id + 2]
            else: continue
                
            success = True
            for n_id in needed_ids:
                match_tile = next((t for t in simulated_hand if t.id == n_id), None)
                if match_tile:
                    simulated_hand.remove(match_tile)
                else:
                    success = False
                    break
            
            if not success: continue
                
            score = self._calculate_hand_potential(simulated_hand, v_counts)
            score += 12 
            
            if score > max_score:
                max_score = score
                best_option = opt_type
                
        if max_score >= base_potential:
            return best_option
        return None
    

    

class HumanPlayer(MahjongPlayer):
    def __init__(self, name, starting_chips=5000, difficulty="human", playstyle="balanced"):
        super().__init__(name, starting_chips, difficulty, playstyle)
        self.is_human = True
        # GUI 專屬通訊變數
        self.ui_state = "idle"            
        self.ui_action_data = None        
        self.gui_response = None          
        self.gui_response = "WAITING"     # 🌟 初始狀態改為 "WAITING"
        

    def _wait_for_gui(self):
        """共用的等待 GUI 回應函式，避免畫面卡死"""
        self.gui_response = "WAITING"    # 🌟 重置為 "WAITING"
        while self.gui_response == "WAITING":
            time.sleep(0.1) # 讓出 CPU 資源給 GUI 線程
        
        response = self.gui_response
        self.gui_response = "WAITING"    # 🌟 重置為 "WAITING"
        self.ui_state = "idle"
        self.ui_action_data = None
        return response

    def cpu_choose_discard(self, visible_counts, river_ids, all_possible_tiles=None, opponents=None):
        """等待 GUI 點擊手牌打出"""
        self.ui_state = "discard"
        print(f"\n[系統] 等待 {self.name} 出牌...")
        return self._wait_for_gui() # 預期 GUI 傳回 int (手牌 index)

    def cpu_should_meld(self, tile, action, visible_counts=None):
        """等待 GUI 按下碰/槓按鈕"""
        if action == 'chow': return False
        self.ui_state = f"wait_{action}"
        self.ui_action_data = tile
        print(f"\n[系統] 等待 {self.name} 決定是否 {action} 【{tile}】...")
        return self._wait_for_gui() # 預期 GUI 傳回 bool (True/False)

    def choose_chow_option(self, tile, chow_options, visible_counts=None):
        """等待 GUI 選擇吃牌組合"""
        if not chow_options: return None
        self.ui_state = "wait_chow"
        self.ui_action_data = {'tile': tile, 'options': chow_options}
        print(f"\n[系統] 等待 {self.name} 決定如何吃 【{tile}】...")
        res = self._wait_for_gui()
        # 🌟 只要傳回的是 "pass"、False 或 None，都統一處理為不吃牌 (回傳 None)
        if res in ["pass", False, None]:
            return None
        return res

    def cpu_should_self_gang(self, gang_info, visible_counts=None):
        """等待 GUI 玩家按下槓或過按鈕"""
        action_name = "暗槓" if gang_info['type'] == 'an_gang' else "補槓"
        tile = gang_info['tile']
        
        self.ui_state = "wait_gang"  # 沿用現有的 wait_gang 狀態，GUI 會自動畫出按鈕
        self.ui_action_data = tile
        
        print(f"\n[系統] 等待 {self.name} 決定是否 {action_name} 【{tile}】...")
        return self._wait_for_gui()  # 預期 GUI 點擊後傳回 True/False

    def choose_hu_interactively(self, tile):
        """等待 GUI 玩家按下【胡】或【過】按鈕 (別人放槍時)"""
        self.ui_state = "wait_hu"
        self.ui_action_data = tile
        print(f"\n[系統] 等待 {self.name} 決定是否 胡 【{tile}】...")
        # 預期 GUI 點擊【胡】傳回 True，點擊【過】傳回 False
        return self._wait_for_gui() 

    def choose_zimo_interactively(self):
        """等待 GUI 玩家按下【自摸】按鈕 (自己摸到時)"""
        self.ui_state = "wait_zimo"
        self.ui_action_data = self.last_drawn_tile
        print(f"\n[系統] 等待 {self.name} 點擊自摸按鈕...")
        # 預期 GUI 點擊【自摸】傳回 True
        return self._wait_for_gui()

    def _wait_for_gui(self):
        self.gui_response = "WAITING"
        while self.gui_response == "WAITING":
            time.sleep(0.1) 
        
        response = self.gui_response
        self.gui_response = "WAITING"
        self.ui_state = "idle"
        self.ui_action_data = None
        
        # 🌟 新增防護：如果是強迫中斷，直接拋出例外
        if response == -1:
            raise InterruptedError("Game interrupted by user.")
            
        return response

class TaiCalculator:
    @staticmethod
    def _check_pure_chows(tc):
        """[輔助函式] 檢查傳入的牌數計數器 tc 是否能完全拆解為純順子"""
        tc = tc.copy()
        for t_id in sorted(tc.keys()):
            while tc[t_id] > 0:
                if t_id >= 400:  # 字牌/花牌無法組成順子
                    return False
                # 檢查是否有連續的三張牌能組成順子
                if tc.get(t_id + 1, 0) > 0 and tc.get(t_id + 2, 0) > 0:
                    tc[t_id] -= 1
                    tc[t_id + 1] -= 1
                    tc[t_id + 2] -= 1
                else:
                    return False
        return True

    @staticmethod
    def _can_decompose_chows_and_pair(rc):
        """[輔助函式] 檢查剩餘手牌是否能完美拆解成『全順子 + 一個對子（眼睛）』"""
        for t_id in list(rc.keys()):
            if rc[t_id] >= 2:
                tc = rc.copy()
                tc[t_id] -= 2  # 假設這張牌是對子眼睛
                if TaiCalculator._check_pure_chows(tc):
                    return True
        return False

    @staticmethod
    def calculate_tai(player, winning_tile, is_self_drawn, game_context):
        """
        純淨版台數計算器：
        只負責計算「牌型」與「榮譽」台數（如門清、大三元、風牌等）。
        ⚠️ 注意：不包含莊家連拉台數、不計算結算籌碼，將這部分留給結算引擎（預處理空間）處理。
        """
        total_tai = 0
        details = {}
        
        # 1. 融合全場大牌池 (此時 player.hand_card 已經包含胡的那張牌，共計 17 張)
        all_tiles = list(player.hand_card)
        for meld in player.melds_card:
            if meld['type'] in ['peng', 'gang', 'an_gang', 'bu_gang']:
                count = meld.get('count', 3)
                all_tiles.extend([meld['tile']] * count)
            elif meld['type'] == 'chow':
                all_tiles.extend(meld['tiles'])
                
        # 建立純 ID 計數器
        counts = Counter(tile.id for tile in all_tiles)
        hand_counts = Counter(tile.id for tile in player.hand_card)
        
        # 擷取環境變數
        round_wind = game_context.get('round_wind', '東')      # 目前的風圈 (東風圈/南風圈...) -> 影響圈風台
        dealer_index = game_context.get('dealer_index', 0)    # 本局莊家的座位編號 (0~3) -> 用於比對身分與推算門風
        player_index = game_context.get('player_index', 0)    # 當前正要算台的玩家座位編號 (0~3) -> 定位計算主體
        
       
        # 風牌與座位對應表  
        wind_names = ['東', '南', '西', '北']
        wind_ids = {'東': 401, '南': 402, '西': 403, '北': 404}
        # 圈風台
        round_wind_id = wind_ids.get(round_wind, 401)
        if counts[round_wind_id] >= 3:
            total_tai += 1
            details[f"圈風刻 ({round_wind}風)"] = 1
        # 門風台
        seat_wind_name = wind_names[(player_index - dealer_index) % 4]
        seat_wind_id = wind_ids[seat_wind_name]
        if counts[seat_wind_id] >= 3:
            total_tai += 1
            details[f"門風刻 ({seat_wind_name}風)"] = 1
            
        # ==================== 類別二：榮譽大台 (修正字一色) ====================
        # 三元牌 (501:紅中, 502:發財, 503:白板)
        dragon_ids = [501, 502, 503]
        dragon_names = {501: '紅中', 502: '發財', 503: '白板'}
        dragon_triplets = sum(1 for d in dragon_ids if counts[d] >= 3)
        dragon_pairs = sum(1 for d in dragon_ids if counts[d] == 2)

        if dragon_triplets == 3:
            total_tai += 8
            details["大三元"] = 8
        elif dragon_triplets == 2 and dragon_pairs == 1:
            total_tai += 4
            details["小三元"] = 4
        else:
            for d in dragon_ids:
                if counts[d] >= 3:
                    total_tai += 1
                    details[f"箭牌 ({dragon_names[d]})"] = 1
                    
        wind_ids_list = [401, 402, 403, 404]
        wind_triplets = sum(1 for w in wind_ids_list if counts[w] >= 3)
        wind_pairs = sum(1 for w in wind_ids_list if counts[w] == 2)

        if wind_triplets == 4:
            total_tai += 16
            details["大四喜"] = 16
        elif wind_triplets == 3 and wind_pairs == 1:
            total_tai += 8
            details["小四喜"] = 8
            
        # ==================== 類別三：狀態與極限環境台 (全新補齊) ====================
        # 門清判定：副露區除暗槓外沒有公開吃碰過
        is_exposed = any(meld['type'] in ['peng', 'chow', 'bu_gang', 'gang'] for meld in player.melds_card)
        is_concealed = not is_exposed

        if is_concealed and is_self_drawn:
            total_tai += 3
            details["門清自摸"] = 3
        elif is_self_drawn:
            total_tai += 1
            details["自摸"] = 1
        elif is_concealed:
            total_tai += 1
            details["門清"] = 1

        if game_context.get('is_lever_congenial', False):
            total_tai += 1
            details["槓上開花"] = 1
            
        # 1. 【全新補齊】搶槓胡 (1台)
        if game_context.get('is_rob_gang', False):
            total_tai += 1
            details["搶槓胡"] = 1
            
        # 2. 【全新補齊】海底撈月 (1台)
        if game_context.get('is_hai_di_lao_yue', False):
            total_tai += 1
            details["海底撈月"] = 1
            
        # 3. 【全新補齊】河底撈魚 (1台)
        if game_context.get('is_he_di_lao_yu', False):
            total_tai += 1
            details["河底撈魚"] = 1

        # 4. 【全新補齊】人胡 (16台)
        if game_context.get('is_ren_hu', False):
            total_tai += 16
            details["人胡"] = 16

       
        # 5. 宣告聽牌台 (🔥 完美升級版：納入天聽、地聽、咪幾，且不與一般聽牌重複計台)
        if getattr(player, 'is_declared_ting', False):
            if game_context.get('is_tian_hu', False) or game_context.get('is_di_hu', False):
                # 💥 漏洞修復：如果已經是天胡或地胡，就不重複計算天聽/地聽/聽牌
                pass
            elif game_context.get('is_tian_ting', False):
                total_tai += 8
                details["天聽"] = 8
            elif game_context.get('is_di_ting', False):
                total_tai += 4
                details["地聽"] = 4
            elif game_context.get('is_migi_ting', False):
                total_tai += 4
                details["咪幾 (暗聽)"] = 4
            else:
                total_tai += 1
                details["聽牌 (📢宣告聽牌)"] = 1

        # ==================== 類別四：經典手牌牌型台 ====================
        # 1. 嚦咕嚦咕 (八對子)
        pairs_in_hand = sum(1 for c in hand_counts.values() if c == 2)
        quads_in_hand = sum(1 for c in hand_counts.values() if c == 4)
        is_migi = len(player.melds_card) == 0 and (pairs_in_hand + quads_in_hand * 2 == 8)
        
        if is_migi:
            total_tai += 8
            details["嚦咕嚦咕 (八對子)"] = 8
        
        # 2. 天胡 
        if game_context.get('is_tian_hu', False):
            total_tai += 16
            details["天胡"] = 16

        # 3. 地胡
        if game_context.get('is_di_hu', False):
            total_tai += 16
            details["地胡"] = 16
        
        # 4. 碰碰胡
        has_no_exposed_chow = all(meld['type'] != 'chow' for meld in player.melds_card)
        is_pure_triplets = all(c >= 3 or c == 2 for c in counts.values())
        pair_count = sum(1 for c in counts.values() if c == 2)
        if has_no_exposed_chow and is_pure_triplets and (pair_count == 1) and not is_migi:
            total_tai += 4
            details["碰碰胡"] = 4

        # 5.暗刻系列 (三暗刻 2台 / 四暗刻 5台 / 五暗刻 8台)
        # 門清區的暗槓絕對算暗刻
        an_ke_count = sum(1 for m in player.melds_card if m['type'] == 'an_gang')
        for t_id, count in hand_counts.items():
            if count >= 3:
                if not is_self_drawn and winning_tile and t_id == winning_tile.id and count == 3:
                    pass 
                else:
                    an_ke_count += 1
        # 計算暗刻大台
        if an_ke_count == 5:
            total_tai += 8
            details["五暗刻"] = 8
        elif an_ke_count == 4:
            total_tai += 5
            details["四暗刻"] = 5
        elif an_ke_count == 3:
            total_tai += 2
            details["三暗刻"] = 2

        # 6. 【漏洞修復】平胡聽牌型態精準判定 (2台)
        # 條件：全順子、無字、無花、非自摸，且必須是『雙頭聽』。不可聽中洞、單釣、邊張。
        has_honor = any(t_id >= 400 for t_id in counts)
        seat_number = ((player_index - dealer_index) % 4) + 1
        flower_map = {'spring': 1, 'summer': 2, 'autumn': 3, 'winter': 4, 'plum': 1, 'orchid': 2, 'bamboo': 3, 'chrysanthemum': 4}
        flower_tai = sum(1 + (1 if flower_map.get(tile.value) == seat_number else 0) for tile in player.flower_cards)
        
        if not is_self_drawn and not has_honor and flower_tai == 0:
            # 必須全副露都是吃牌，且手牌沒有任何暗刻
            if all(meld['type'] == 'chow' for meld in player.melds_card):
                # if all(c <= 2 for c in hand_counts.values()) and winning_tile:
                if winning_tile:
                    W = winning_tile.id #聽牌id
                    R = W % 10 
                    is_shuang_tou = False #檢查雙頭聽
                    
                    # 🔍 A. 檢查是否可作為雙頭聽的低端 (例如：手牌有 4,5 聽 3,6，胡 3。此時 R=3 <= 6)
                    if R <= 6 and hand_counts[W] >= 1 and hand_counts[W+1] >= 1 and hand_counts[W+2] >= 1:
                        tc = hand_counts.copy()
                        tc[W] -= 1
                        tc[W+1] -= 1
                        tc[W+2] -= 1
                        if TaiCalculator._can_decompose_chows_and_pair(tc):
                            is_shuang_tou = True
                    
                    # 🔍 B. 檢查是否可作為雙頭聽的高端 (例如：手牌有 4,5 聽 3,6，胡 6。此時 R=6 >= 4)
                    if not is_shuang_tou and R >= 4 and hand_counts[W] >= 1 and hand_counts[W-1] >= 1 and hand_counts[W-2] >= 1:
                        tc = hand_counts.copy()
                        tc[W] -= 1
                        tc[W-1] -= 1
                        tc[W-2] -= 1
                        if TaiCalculator._can_decompose_chows_and_pair(tc):
                            is_shuang_tou = True
                            
                    if is_shuang_tou:
                        total_tai += 2
                        details["平胡"] = 2

        # 7. 求人系列
        exposed_meld_count = sum(1 for m in player.melds_card if m['type'] in ['peng', 'gang', 'bu_gang', 'chow'])
        if exposed_meld_count == 5:
            if not is_self_drawn:
                total_tai += 2
                details["全求人"] = 2
            else:
                total_tai += 1
                details["半求人"] = 1

        # 8. 【漏洞修復】花色檢查與字一色判定
        is_zi_yi_se = all(t_id >= 400 for t_id in counts)
        if is_zi_yi_se:
            # 💥 字一色完全成立：排除 len(suits)==0 導致沒台的 Bug
            total_tai += 16
            details["字一色"] = 16
        else:
            suits = set()
            for t_id in counts:
                if 100 <= t_id < 200: suits.add('cake')
                elif 200 <= t_id < 300: suits.add('strip')
                elif 300 <= t_id < 400: suits.add('tenthousand')
            if len(suits) == 1:
                if has_honor:
                    total_tai += 4
                    details["混一色"] = 4
                else:
                    total_tai += 8
                    details["清一色"] = 8
                    
        # ==================== 類別五：花牌台與特殊花牌特大台 ====================
        # 1. 【全新補齊】八仙過海 (8台)
        if len(player.flower_cards) == 8:
            total_tai += 8
            details["八仙過海"] = 8
        # 2. 【全新補齊】七搶一 (8台)
        elif game_context.get('is_qi_qiang_yi', False):
            total_tai += 8
            details["七搶一"] = 8
        # 3. 一般花牌台計算 (若觸發大台，通常不重複計算基本花牌台)
        elif flower_tai > 0:
            total_tai += flower_tai
            details[f"花牌 (共{len(player.flower_cards)}張)"] = flower_tai
        
        # 🔍 【全新新增】檢查一台花（四季、四君子）
        obtained_flowers = {tile.value for tile in player.flower_cards}
        seasons = {'spring', 'summer', 'autumn', 'winter'}
        plants = {'plum', 'orchid', 'bamboo', 'chrysanthemum'}
        
        if seasons.issubset(obtained_flowers):
            total_tai += 2
            details["一台花 (春夏秋冬)"] = 2
        if plants.issubset(obtained_flowers):
            total_tai += 2
            details["一台花 (梅蘭竹菊)"] = 2


        return total_tai, details
    
# ==================== 🕹️ 3. 單局控制引擎（融入全場可見牌計算與起手大牌感知） ====================
class MahjongGame:
    def __init__(self, players, deck, all_unique_tiles, round_wind, dealer_index, dealer_streak):
        self.players = players                  # 傳入四位已初始化好手牌的玩家      
        self.deck = deck                         # 傳入洗好的共享牌堆      
        self.all_unique_tiles = all_unique_tiles # 傳入全域不重複牌模板
        self.discarded_pile = []                 # 牌海
        self.discarded_history = []              # 專給 GUI 用的牌海履歷
        self.current_turn = dealer_index         # 👑 由本局莊家起手摸牌
        self.is_over = False
        self.round_wind = round_wind             # 儲存當前風圈，供前端讀取
        self.winner = None
        self.shooter = None                      # 🎯 記錄放槍者
        self.is_draw = False                     # ⏸️ 記錄是否流局   
        self.is_lever_congenial = False          # 記錄本局是否為槓上開花
        
        # 環境偵測器
        self.dealer_index = dealer_index
        self.discard_count = 0                   # 紀錄全場總打牌次數
        self.has_any_meld = False                # 全場是否有任何人執行過 吃/碰/明槓/暗槓
        self.is_tian_hu = False                  # 天胡標記
        self.is_di_hu = False                    # 地胡標記
        self.is_ren_hu = False                   # 人胡
        self.is_rob_gang = False                 # 搶槓胡
        self.is_hai_di_lao_yue = False           # 海底撈月
        self.is_he_di_lao_yu = False             # 河底撈魚
        self.is_qi_qiang_yi = False              # 七搶一
        self.is_ba_xian_guo_hai = False          # 八仙過海

        
    def next_turn(self):
        self.current_turn = (self.current_turn + 1) % 4

    def get_visible_counts_for_player(self, player):
        """🧮 計算特定玩家視角中，全場所有已經「明牌見光」的牌 ID 總量"""
        visible_ids = []
        # 1. 該玩家自己的私有手牌 + 補花牌
        visible_ids.extend([t.id for t in player.hand_card])
        visible_ids.extend([t.id for t in player.flower_cards])
        # 2. 該玩家自己的副露
        for m in player.melds_card:
            if m['type'] in ['peng', 'gang', 'an_gang', 'bu_gang']:
                visible_ids.extend([m['tile'].id] * m.get('count', 3))
            elif m['type'] == 'chow':
                visible_ids.extend([t.id for t in m['tiles']])
        # 3. 其他玩家在桌面上公開的副露 (排除暗槓)
        for p in self.players:
            if p == player: continue
            for m in p.melds_card:
                if m['type'] in ['peng', 'gang', 'bu_gang']:
                    visible_ids.extend([m['tile'].id] * m.get('count', 3))
                elif m['type'] == 'chow':
                    visible_ids.extend([t.id for t in m['tiles']])
        # 4. 全場牌海
        visible_ids.extend([t.id for t in self.discarded_pile])
        return Counter(visible_ids)

    def print_ting_status_with_rem(self, player):
        """🔮 精準掃描聽牌明細與海底殘張"""
        ting_cards = player.check_ting(self.all_unique_tiles)
        if ting_cards:
            visible_counts = self.get_visible_counts_for_player(player)
            ting_details = []
            for tile in ting_cards:
                rem = max(0, 4 - visible_counts.get(tile.id, 0))
                status_str = f"剩{rem}張" if rem > 0 else "🚨死聽"
                ting_details.append(f"【{tile}】({status_str})")
            print(f"👀 [系統提示] {player.name} 目前聽牌中！聽：{', '.join(ting_details)}")

    def start_turn(self):
        if self.is_over: return

        if len(self.deck) <= 16:
            print(f"\n🛑 ⚠️ 牌堆僅剩 {len(self.deck)} 張底牌！已達台灣麻將海底限制。")
            self.is_over = True
            self.is_draw = True
            return

        active_player = self.players[self.current_turn]
        print(f"\n==================== 輪到 {active_player.name} (剩餘牌數: {len(self.deck)}) ====================")
        
        # 記錄摸牌前的剩餘牌數，用來判定是否為最後一張牌
        deck_len_before_draw = len(self.deck)

        # 1. 玩家摸牌與補花
        drawn_tile = active_player.draw_tile(self.deck)
        print(f"【{active_player.name}】摸牌: {drawn_tile}")
        
        # 接收補花可能產生的新牌
        bu_hua_tile = active_player.check_and_bu_hua(self.deck)

        # 🌟 修復陣列邊界漏洞：安全判定最終有效牌，不再依賴排序後的 [-1]
        actual_tile = bu_hua_tile if bu_hua_tile else drawn_tile
        active_player.last_drawn_tile = actual_tile

        # 🎯【花牌特殊胡牌精準檢查點】
        total_flowers_in_game = sum(len(pl.flower_cards) for pl in self.players)
        # 如果目前有人手上有 7 張花牌，且剛剛是別人摸到第 8 張花牌（或者自己摸到第 7 張，別人有1張等攔截狀況）
        for i, p in enumerate(self.players):
            if len(p.flower_cards) == 8:
                print(f"\n🎉🎉🎉 🌸【{p.name}】💥💥 恭喜觸發特大牌型：八仙過海！！！(自摸) 💥💥 🎉🎉🎉")
                self.is_over = True
                self.winner = p
                self.shooter = None  # 🌟 修正：八仙過海自摸不涉及放槍
                self.is_ba_xian_guo_hai = True
                return
            
            if len(p.flower_cards) == 7 and total_flowers_in_game == 8:
                print(f"\n🎉🎉🎉 🌸【{p.name}】💥💥 恭喜觸發特殊花牌型：七搶一！！！ 💥💥 🎉🎉🎉")
                self.is_over = True
                self.winner = p
                self.shooter = None  # 🌟 修正：七搶一自摸不涉及放槍
                self.is_qi_qiang_yi = True
                # 🌟 修正：如果是別家摸到第8張花，那個人放槍；如果是我自己摸到第7張，持有剩下1張花的人放槍
                if i != self.current_turn:
                    self.shooter = active_player
                else:
                    self.shooter = next(pl for pl in self.players if len(pl.flower_cards) == 1)
                return
            
        # 🎯【自摸檢查點】
        if active_player.check_hu():
            wants_zimo = True
            # 如果是人類玩家，呼叫 GUI 等待自摸點擊
            if hasattr(active_player, 'choose_zimo_interactively'):
                wants_zimo = active_player.choose_zimo_interactively()
            if wants_zimo:
                # 原本的自摸結算與印出邏輯 ...
                if self.discard_count == 0 and self.current_turn == self.dealer_index and not self.has_any_meld:
                    print(f"\n🎉🎉🎉 👑【{active_player.name}】💥💥 天胡！！！ 💥💥 🎉🎉🎉")
                    self.is_tian_hu = True
            # 🌟 修正：自摸判定點，檢查是否為天胡或海底撈月 
            if self.discard_count == 0 and self.current_turn == self.dealer_index and not self.has_any_meld:
                print(f"\n🎉🎉🎉 👑【{active_player.name}】💥💥 天胡！！！ 💥💥 🎉🎉🎉")
                self.is_tian_hu = True
            elif deck_len_before_draw == 17:
                print(f"\n🎉🎉🎉 🌙【{active_player.name}】💥💥 海底撈月自摸！！！ 💥💥 🎉🎉🎉")
                self.is_hai_di_lao_yue = True
            else:
                print(f"\n🎉🎉🎉 💥【{active_player.name}】自摸！！！ 🎉🎉🎉")
                
            self.is_over = True
            self.is_lever_congenial = False
            self.winner = active_player
            self.winning_tile = active_player.last_drawn_tile  
            return
        
        # 🌟【聽牌鎖死判定】
        if active_player.is_declared_ting:
            print(f"🔒 【{active_player.name}】處於宣告聽牌狀態，手牌鎖死！自動打出剛摸到的牌。")
            discard_index = active_player.hand_card.index(active_player.last_drawn_tile)
            discarded_tile = active_player.discard_tile(discard_index)
            self.discarded_pile.append(discarded_tile)
            # 🌟 新增這行：記錄這張牌是哪個座位打的
            self.discarded_history.append({'player_index': self.current_turn, 'tile': discarded_tile})
            self.discard_count += 1
            print(f"【{active_player.name}】打牌: {discarded_tile}")
            # 完成一次常態摸打，解除過水烙印
            if active_player.is_guo_shui:
                active_player.is_guo_shui = False
                print(f"🌊 【{active_player.name}】完成聽牌鎖死下的摸打，解除過水狀態。")
                
            self.print_ting_status_with_rem(active_player)
            self.handle_reactions(discarded_tile, active_player)
            return

        # 2. 循環檢查暗槓或補槓
        declined_gangs = []  # 紀錄本回合已經點選「過」的槓牌 ID
        while True:
            gang_info = active_player.check_self_gang(ignore_ids=declined_gangs)
            if gang_info:
                # 詢問玩家是否要執行這個槓牌
                wants_to_gang = True
                if hasattr(active_player, 'cpu_should_self_gang'):
                    visible_counts = self.get_visible_counts_for_player(active_player)
                    wants_to_gang = active_player.cpu_should_self_gang(gang_info, visible_counts)
                
                # 如果玩家按下了「過」(False)
                if not wants_to_gang:
                    declined_gangs.append(gang_info['tile'].id)
                    continue  # 略過這張牌，繼續檢查手牌中有沒有其他牌可以槓
                
                self.has_any_meld = True 
                
                # 🎯【搶槓胡偵測點】
                if gang_info.get('type') == 'bu_gang':
                    tile = gang_info['tile']
                    rob_claims = []
                    for i in range(4):
                        if i == self.current_turn: continue
                        if self.players[i].check_hu(tile) and not self.players[i].is_guo_shui:
                            distance = (i - self.current_turn) % 4
                            rob_claims.append({'player_index': i, 'distance': distance})
                    
                    if rob_claims:
                        rob_claims.sort(key=lambda x: x['distance'])
                        winner_idx = rob_claims[0]['player_index']
                        rob_player = self.players[winner_idx]                       
                        print(f"\n⚡ 🚨 【{rob_player.name}】攔截宣告：搶槓胡！！！")
                        self.is_over = True
                        self.winner = rob_player
                        self.shooter = active_player 
                        self.winning_tile = tile
                        rob_player.hand_card.append(tile) 
                        rob_player.hand_card.sort()
                        self.is_rob_gang = True
                        return 
                
                # 正式執行槓牌與補牌
                active_player.execute_self_gang(gang_info)
                drawn_tile = active_player.draw_tile(self.deck)
                active_player.check_and_bu_hua(self.deck)
                
                actual_tile = active_player.hand_card[-1]
                active_player.last_drawn_tile = actual_tile
                print(f"【{active_player.name}】槓牌補牌摸到: {actual_tile}")
                
                # 🎯【槓上開花自摸檢查點】
                if active_player.check_hu():
                    print(f"\n🎉🎉🎉 💥【{active_player.name}】槓上開花自摸！！！ 💥 🎉🎉🎉")
                    self.is_over = True
                    self.is_lever_congenial = True 
                    self.winner = active_player
                    self.winning_tile = active_player.last_drawn_tile  
                    return
            else:
                break
                
        # 3. 玩家智慧打牌
        visible_counts = self.get_visible_counts_for_player(active_player)
        river_ids = [t.id for t in self.discarded_pile]
        opponents = [p for p in self.players if p != active_player]
        discard_index = active_player.cpu_choose_discard(visible_counts, river_ids, self.all_unique_tiles, opponents)
        discarded_tile = active_player.discard_tile(discard_index)
        self.discarded_pile.append(discarded_tile)
        # 🌟 新增這行：記錄這張牌是哪個座位打的
        self.discarded_history.append({'player_index': self.current_turn, 'tile': discarded_tile})
        self.discard_count += 1 # 🌟 累加全場打牌計數
        print(f"【{active_player.name}】打牌: {discarded_tile}")
        
        if active_player.is_guo_shui:
            active_player.is_guo_shui = False
            print(f"🌊 【{active_player.name}】已完成常態摸打，解除過水狀態。")

        # 🌟 AI 宣告聽牌決策點
        if not active_player.is_declared_ting:
            ting_cards = active_player.check_ting(self.all_unique_tiles)
            # 進階 CPU 只要打完牌發現自己聽牌，就高調宣告明聽（賺取聽牌台數）
            if ting_cards and active_player.difficulty == "advanced":
                active_player.is_declared_ting = True
                print(f"📢 【{active_player.name}】拍桌大喊：「我聽牌了！」（宣告聽牌，手牌鎖死）")
        
        self.print_ting_status_with_rem(active_player)
        # 4. 處理其他玩家反應
        self.handle_reactions(discarded_tile, active_player)


    def handle_reactions(self, tile, shooter):
        if self.is_over: return
        shooter_index = self.players.index(shooter)
        claims = []  
        could_hu_indices = []
        
        # ==================== 1. 意願收集階段 ====================
        for i in range(4):
            if i == shooter_index: continue
            player = self.players[i]
            distance = (i - shooter_index) % 4 
            
            # 狀態鎖：紀錄該玩家是否已經選擇了胡牌或碰/槓
            has_claimed_hu = False
            has_claimed_peng_gang = False

            # 檢查放槍胡 (優先權 3)
            if player.check_hu(tile):
                could_hu_indices.append(i) 
                if player.is_guo_shui:
                    print(f"🌊 [過水限制] 【{player.name}】能胡這張【{tile}】，但目前處於過水狀態，無法胡牌！")
                else:
                    wants_hu = True
                    if hasattr(player, 'choose_hu_interactively'):
                        wants_hu = player.choose_hu_interactively(tile)
                    elif hasattr(player, 'cpu_should_hu'):
                        wants_hu = player.cpu_should_hu(tile)
                    
                    if wants_hu:
                        claims.append({'player_index': i, 'action': 'hu', 'priority': 3, 'distance': distance})
                        has_claimed_hu = True  # 標記已選擇胡牌
                    else:
                        print(f"👋 【{player.name}】技術上能胡【{tile}】，但主動選擇 Pass 放過！")
            
            # 如果處於宣告聽牌狀態，或是已經宣告胡牌，就不再考慮吃碰槓
            if player.is_declared_ting or has_claimed_hu:
                continue

            # 檢查大明槓 (優先權 2)   
            if player.check_gang(tile):
                if len(self.deck) > 16:
                    visible_counts = self.get_visible_counts_for_player(player)
                    if not hasattr(player, 'cpu_should_meld') or player.cpu_should_meld(tile, 'gang', visible_counts):
                        claims.append({'player_index': i, 'action': 'gang', 'priority': 2, 'distance': distance})
                        has_claimed_peng_gang = True
                
            # 檢查碰牌 (優先權 2)
            # 如果前面已經選擇了槓牌，就不會再詢問碰牌
            if not has_claimed_peng_gang and player.check_peng(tile):
                visible_counts = self.get_visible_counts_for_player(player)
                if not hasattr(player, 'cpu_should_meld') or player.cpu_should_meld(tile, 'peng', visible_counts):
                    claims.append({'player_index': i, 'action': 'peng', 'priority': 2, 'distance': distance})
                    has_claimed_peng_gang = True
                
            # 🌟 嚴格修正：吃牌檢查 (優先權 1)
            # 1. 確保 distance == 1（嚴格限制只能吃上一家的牌）
            # 2. 如果玩家已經宣告要碰/槓，就不需要再詢問吃牌（防呆機制）
            if not has_claimed_peng_gang:
                chow_options = player.check_chow(tile)
                if chow_options:
                    # 🚨 【防線 1：檢查距離是否合法】
                    if distance == 1:
                        visible_counts = self.get_visible_counts_for_player(player)
                        # 利用多型，自動判斷是 CPU 還是人類來選擇吃牌組合
                        chosen_chow = player.choose_chow_option(tile, chow_options, visible_counts)
                        
                        if chosen_chow:
                            # 將人類或 CPU 選好的吃牌方式包裝進 claims 參與競爭
                            claims.append({
                                'player_index': i, 'action': 'chow', 'priority': 1, 
                                'distance': distance, 'options': [chosen_chow]
                            })
                    else:
                        # 🛡️ 捕捉到不合法嘗試！手牌確實能吃，但座位不對
                        # 若想在終端機看到哪些牌被阻擋，可以把下面這行 print 解開註解
                        # print(f"🛡️ [系統防堵] {player.name} 試圖吃非上家 (距離 {distance}) 的 {tile}，已自動阻擋。")
                        pass


        # ==================== 2. 仲裁與執行階段 ====================
        if not claims:
            for idx in could_hu_indices:
                p = self.players[idx]
                if not p.is_guo_shui:
                    p.is_guo_shui = True
                    print(f"🌊 【{p.name}】能胡未胡，正式進入/維持過水狀態！")
            self.next_turn()
            return
            
        claims.sort(key=lambda x: (-x['priority'], x['distance']))
        best_claim = claims[0]
        target_player = self.players[best_claim['player_index']]
        action = best_claim['action']
        
        hu_claimers = {c['player_index'] for c in claims if c['action'] == 'hu'}
        for idx in could_hu_indices:
            if idx not in hu_claimers:
                p = self.players[idx]
                if not p.is_guo_shui:
                    p.is_guo_shui = True
                    print(f"🌊 【{p.name}】能胡未胡（因被截胡、自主Pass、或選擇吃碰槓），正式進入過水狀態！")
        
        if action == 'hu':
            self.is_over = True
            self.winner = target_player
            self.shooter = shooter      
            self.winning_tile = tile        
            target_player.hand_card.append(tile)
            target_player.hand_card.sort()
            self.discarded_pile.pop()
            self.discarded_history.pop()
            
            if self.discard_count == 1 and shooter_index == self.dealer_index and not self.has_any_meld:
                print(f"\n🎉🎉🎉 🌍【{target_player.name}】💥💥 地胡！！！ 💥💥 🎉🎉🎉")
                self.is_di_hu = True
            elif self.discard_count <= 4 and not self.has_any_meld and best_claim['player_index'] != self.dealer_index:
                print(f"\n🎉🎉🎉 👤【{target_player.name}】💥💥 恭喜觸發特殊牌型：人胡！！！ 💥💥 🎉🎉🎉")
                self.is_ren_hu = True
            elif len(self.deck) == 16:
                print(f"\n🎉🎉群 🐟【{target_player.name}】💥💥 河底撈魚！！！ 💥💥 🎉🎉🎉")
                self.is_he_di_lao_yu = True
            return
            
        # 處理吃碰槓的打牌
        self.has_any_meld = True
        self.current_turn = best_claim['player_index']
        
        if action == 'gang':
            target_player.gang(tile)
            self.discarded_pile.pop()
            self.discarded_history.pop()
            while True:
                if len(self.deck) <= 16:
                    break
                target_player.draw_tile(self.deck)
                target_player.check_and_bu_hua(self.deck)
                actual_tile = target_player.hand_card[-1]
                target_player.last_drawn_tile = actual_tile
                print(f'[{target_player.name}] 槓牌補牌摸到: {actual_tile}')
                
                if target_player.check_hu():
                    print(f"\n🎉🎉🎉 💥【{target_player.name}】槓上開花自摸！！！ 💥 🎉🎉🎉")
                    self.is_over = True
                    self.is_lever_congenial = True 
                    self.winner = target_player
                    self.winning_tile = target_player.last_drawn_tile 
                    return
                
                gang_info = target_player.check_self_gang()
                if gang_info:
                    target_player.execute_self_gang(gang_info)
                else:
                    break
        
        elif action == 'peng':
            target_player.peng(tile)
            self.discarded_pile.pop()
            self.discarded_history.pop()
            
        elif action == 'chow':
            # 🚨🚨🚨 【防線 2：執行前強制攔截並回報錯誤】🚨🚨🚨
            # 再次驗證吃牌者與放槍者的相對距離
            actual_dist = (best_claim['player_index'] - shooter_index) % 4
            if actual_dist != 1:
                err_msg = (
                    f"\n======================================================\n"
                    f"💥 [嚴重邏輯異常] 系統捕捉到非法的吃牌動作！\n"
                    f"🛑 吃牌者: {target_player.name} (座位 {best_claim['player_index']})\n"
                    f"🎯 放槍者: {shooter.name} (座位 {shooter_index})\n"
                    f"📏 相對距離: {actual_dist} (1=上家, 2=對家, 3=下家)\n"
                    f"❌ 錯誤：吃牌必須為上家 (距離 1)！引擎已強制攔截，放棄吃牌並換下一家。\n"
                    f"======================================================"
                )
                print(err_msg)
                
                # 🛠️ 修正核心：移除 raise RuntimeError
                # 改為推進回合，讓遊戲能繼續順暢進行
                self.next_turn()
                return  
            
            # 若無異常，才正式執行吃牌
            chosen_chow = best_claim['options'][0]  
            target_player.execute_chow(tile, chosen_chow)
            self.discarded_pile.pop()
            self.discarded_history.pop()

        if hasattr(target_player, 'choose_discard_interactively'):
            discard_index = target_player.choose_discard_interactively()
        else:
            visible_counts = self.get_visible_counts_for_player(target_player)
            river_ids = [t.id for t in self.discarded_pile]
            opponents = [p for p in self.players if p != target_player]
            discard_index = target_player.cpu_choose_discard(visible_counts, river_ids, self.all_unique_tiles, opponents)
            

        discarded_tile = target_player.discard_tile(discard_index)
        self.discarded_pile.append(discarded_tile)
        # 🌟 新增這行：記錄這張牌是哪個座位打的
        self.discarded_history.append({'player_index': self.current_turn, 'tile': discarded_tile})
        self.discard_count += 1 
        
        if target_player.is_guo_shui:
            target_player.is_guo_shui = False
            print(f"🌊 【{target_player.name}】完成鳴牌後的常態切牌，解除過水狀態。")
            
        self.print_ting_status_with_rem(target_player)
        self.handle_reactions(discarded_tile, target_player)


# ==================== 🏆 4. 全新聯賽總管控制器 (Match) ====================
class MahjongMatch:
    # 🌟 1. 新增 gui_callback 參數與執行狀態
    def __init__(self, players, base_chips=30, tai_chips=10, gui_callback=None):
        self.players = players                 
        self.base_chips = base_chips            
        self.tai_chips = tai_chips              
        self.winds = ['東', '南', '西', '北']
        self.current_wind_idx = 0               
        self.dealer_index = 0                   
        self.dealer_streak = 0                  
        self.match_count = 1                    
        
        # self.gui_callback = gui_callback  # 🔌 用來與 GUI 溝通的信號線
        # self.is_running = False           # 🔌 控制背景迴圈是否繼續執行的開關
        # 🌟 新增：用於 GUI 視窗執行的多執行緒狀態控制
        self.is_running = True
        self.game_thread = None          

    def build_shuffled_deck(self):
        """重新動態生成 144 張洗好的物件牌堆"""
        deck = []
        for category, sub_dict in total_card_dict.items():
            base_id = BASE_IDS[category]
            for i, (card_name, count) in enumerate(sub_dict.items(), start=1):
                id_val = base_id + int(card_name) if card_name.isdigit() else base_id + i
                for _ in range(count):
                    deck.append(Tile(category, card_name, id_val))
        random.shuffle(deck)
        return deck

    def distribute_initial_cards(self, deck):
        """發給每個人起手 16 張牌並完成補花"""
        for _ in range(4): 
            for p in self.players:
                for _ in range(4): 
                    p.hand_card.append(deck.pop())
        print("\n--- 🀄 遊戲初始化：起手補花階段 ---")
        for p in self.players:
            p.check_and_bu_hua(deck)
            p.hand_card.sort()

    


    # 🌟 新增：啟動背景遊戲執行緒，避免卡死 GUI 主迴圈
    def start_match_thread(self, max_hands=None):
        """🚀 開啟新執行緒跑遊戲，避免 while 迴圈卡死 GUI"""
        # if self.is_running: return
        if self.game_thread and self.game_thread.is_alive():
                    print("⚠️ 賽事已經在執行中！")
                    return
        self.is_running = True
        # 將 play_match 放入 daemon thread，這樣視窗關閉時執行緒會自動結束
        self.game_thread = threading.Thread(target=self.play_match, args=(max_hands,), daemon=True)
        self.game_thread.start()
        print("🚀 [系統] 麻將賽事背景執行緒已成功啟動！")

    # 安全中斷遊戲（例如玩家中途關閉視窗）
    def stop_match(self):
        self.is_running = False
        print("🛑 [系統] 接收到中斷指令，正在安全停止賽事...")
        # 喚醒所有可能正在等待 GUI 點擊的玩家，打破 while 迴圈
        for p in self.players:
            if hasattr(p, 'gui_response'):
                p.gui_response = -1 

    def play_match(self, max_hands=None):
        """🎮 開始正統台灣麻將「一將」賽事（加入 is_running 判斷）"""
        self.hand_count = 1  
        self.current_wind_idx = 0  
        self.dealer_index = 0  
        self.dealer_streak = 0  
        
        # 🔄 主迴圈：只要還沒打完四圈，且 GUI 沒有發出中斷指令 (is_running == True)
        while self.current_wind_idx < 4 and self.is_running:
            current_wind = self.winds[self.current_wind_idx]
            dealer_player = self.players[self.dealer_index]
            wind_names = ["東", "南", "西", "北"]
            round_name = f"{current_wind}風{wind_names[self.dealer_index]}局"
            
            print(f"\n" + "="*70)
            print(f"⚡⚡⚡ 【第 {self.hand_count} 手牌】環境：{round_name} | 莊家：{dealer_player.name} [連莊 {self.dealer_streak}] ⚡⚡⚡")
            print("="*70)
            
            for p in self.players:
                p.reset_for_new_round()
                
            deck = self.build_shuffled_deck()
            self.distribute_initial_cards(deck)
            
            game = MahjongGame(
                self.players, deck, ALL_UNIQUE_TILES, 
                round_wind=current_wind, 
                dealer_index=self.dealer_index, 
                dealer_streak=self.dealer_streak
            )

            # 👇 新增這行：讓 GUI 可以透過 match.current_game 抓取海底與牌堆資訊
            self.current_game = game 
            
            # 🌟 單局核心引擎：同樣加入 self.is_running 防護
            while not game.is_over and self.is_running:
                game.start_turn()
                
            # 如果是中途被玩家按鈕中斷的，直接跳出迴圈不結算
            if not self.is_running:
                print("\n🚫 賽事已因使用者關閉而強制中斷！")
                break

            if game.is_draw:
                print("\n🔍 【流局 debug 觀測站】來看看大家最後的手牌長怎樣：")
                for p in self.players:
                    hand_str = ", ".join(str(t) for t in p.hand_card)
                    print(f"  👤 {p.name} 最終手牌: [{hand_str}]")
                    
            is_bankrupt = self.settle_round_scores(game)
            
            print("\n💰 當前全場籌碼餘額：")
            for p in sorted(self.players, key=lambda x: x.chips, reverse=True):
                print(f"   📊 {p.name} ({p.difficulty}): {p.chips} 點")
            print("="*70)
            
            if is_bankrupt:
                print("\n🚨 【賽事提前結束】因有玩家不幸破產，大會宣告本場「一將」賽事提前腰斬！")
                break
            
            if max_hands and self.hand_count >= max_hands:
                print(f"\n🧪 【測試中斷】已達到設定的測試局數上限（共 {max_hands} 局），測試圓滿結束！")
                break 

            self.hand_count += 1
            
            # 🌟 局與局之間可以給 GUI 一點喘息時間，方便播放結算動畫
            time.sleep(1)
            
        else:
            if self.is_running:
                print(f"\n🏆🏆🏆 🎉 【一將圓滿結束】恭喜四位大俠英勇打完東南西北四圈！ 🎉 🏆🏆🏆")
            
        if self.is_running:
            final_winner = max(self.players, key=lambda x: x.chips)
            print(f"👑 本將總冠軍：【{final_winner.name}】！最終淨資產：{final_winner.chips} 點！\n")

    def settle_round_scores(self, game):
        """🎯 核心：跨局籌碼轉移、連莊移莊與風圈推進邏輯"""
        print("\n--- 🏁 本局結束結算 ---")
        
        if game.is_draw:
            self.dealer_streak += 1
            print(f"⏸️ 海底摸空流局！莊家【{self.players[self.dealer_index].name}】成功守住 ➡️ 變更為：連 {self.dealer_streak}！")
            return self.check_bankruptcy()
            
        # 🎉有人胡牌    
        winner = game.winner
        winner_idx = self.players.index(winner)
        is_self_drawn = (game.shooter is None)
        winning_tile = getattr(game, 'winning_tile', None)
        
        # 🌟 傳入大腦環境包
        game_context = {
            'round_wind': self.winds[self.current_wind_idx], 
            'dealer_index': self.dealer_index,
            'dealer_streak': self.dealer_streak, 
            'player_index': winner_idx,
            'shooter_index': self.players.index(game.shooter) if game.shooter else None,
            'is_lever_congenial': getattr(game, 'is_lever_congenial', False), 
            'is_tian_hu': getattr(game, 'is_tian_hu', False),                 
            'is_di_hu': getattr(game, 'is_di_hu', False),                     
            'is_ren_hu': getattr(game, 'is_ren_hu', False),
            'is_rob_gang': getattr(game, 'is_rob_gang', False),
            'is_hai_di_lao_yue': getattr(game, 'is_hai_di_lao_yue', False),
            'is_he_di_lao_yu': getattr(game, 'is_he_di_lao_yu', False),
            'is_qi_qiang_yi': getattr(game, 'is_qi_qiang_yi', False)
        }
        
        # 呼叫大腦計算牌型台數 (純手牌台數，不含莊家台)
        total_tai, details = TaiCalculator.calculate_tai(winner, winning_tile, is_self_drawn, game_context)
        
        # ==================== 🌟 核心修正：計算台灣麻將莊家台 ====================
        # 莊家基本 1 台 + 每連莊 1 次多 2 台
        dealer_tai = 1 + (2 * self.dealer_streak)
        
        # 2. 籌碼流向精準判定
        if is_self_drawn:
            print(f"🎉🎉🎉 💥【{winner.name}】自摸！！！ 牌型共 {total_tai} 台 {details}")
            total_win = 0
            
            # 判斷自摸者是不是莊家
            if winner_idx == self.dealer_index:
                # 👑 【莊家自摸】：每位閒家都要多付「莊家連拉台數」
                pay_per_player = self.base_chips + ((total_tai + dealer_tai) * self.tai_chips)
                for i, p in enumerate(self.players):
                    if i != winner_idx:
                        p.chips -= pay_per_player
                        total_win += pay_per_player
                        print(f"💸 閒家【{p.name}】支付 {pay_per_player} 點 (含莊家連拉 {dealer_tai} 台)")
            else:
                # 👤 【閒家自摸】：其他閒家付基本台數，莊家要獨自多付「莊家連拉台數」
                normal_pay = self.base_chips + (total_tai * self.tai_chips)
                dealer_pay = self.base_chips + ((total_tai + dealer_tai) * self.tai_chips)
                
                for i, p in enumerate(self.players):
                    if i != winner_idx:
                        if i == self.dealer_index:
                            p.chips -= dealer_pay
                            total_win += dealer_pay
                            print(f"💸 莊家【{p.name}】支付 {dealer_pay} 點 (含莊家連拉加付 {dealer_tai} 台)")
                        else:
                            p.chips -= normal_pay
                            total_win += normal_pay
                            print(f"💸 閒家【{p.name}】支付 {normal_pay} 點")
                            
            winner.chips += total_win
            print(f"🏆 【{winner.name}】自摸大豐收，淨賺 +{total_win} 點！")
            
        else:
            # 🎯 放槍胡
            shooter = game.shooter
            shooter_idx = self.players.index(shooter)
            
            # 判斷贏家或放槍者是否有一方是莊家
            if winner_idx == self.dealer_index or shooter_idx == self.dealer_index:
                actual_tai = total_tai + dealer_tai
                print_dealer_msg = f" (含莊家連拉 {dealer_tai} 台)"
            else:
                # 閒家放槍給閒家，完全不關莊家的事，只算純牌型台數
                actual_tai = total_tai
                print_dealer_msg = ""
                
            single_pay = self.base_chips + (actual_tai * self.tai_chips)
            shooter.chips -= single_pay
            winner.chips += single_pay
            
            print(f"🎉🎉🎉 💥【{winner.name}】胡牌！！！放槍者：【{shooter.name}】 💥")
            print(f"📊 【牌型台數明細】: 牌型共 {total_tai} 台 {details}")
            print(f"💸 【{shooter.name}】慘遭獨碰！支付 {single_pay} 點給 【{winner.name}】{print_dealer_msg}")

        # 3. 處理連莊或移莊邏輯 
        if winner_idx == self.dealer_index:
            self.dealer_streak += 1
            print(f"🔥 莊家【{winner.name}】胡牌！繼續連莊 ➡️ 目前為：連 {self.dealer_streak}！")
        else:
            old_dealer_idx = self.dealer_index
            self.dealer_index = (self.dealer_index + 1) % 4
            self.dealer_streak = 0
            print(f"換人做做看！【{winner.name}】逆襲下莊！➔ 新莊家為【{self.players[self.dealer_index].name}】")
            if old_dealer_idx == 3 and self.dealer_index == 0:
                self.current_wind_idx += 1
                if self.current_wind_idx < 4:
                    print(f"\n🌍 🪐 【風圈推進】全場已移莊一圈！風圈更換變更為：【{self.winds[self.current_wind_idx]}風圈】")
                    
        return self.check_bankruptcy()

    def check_bankruptcy(self):
        """💥 檢查全場是否有玩家已經輸光籌碼"""
        bankrupt_detected = False
        for p in self.players:
            if p.chips <= 0:
                print(f"🚨 【破產公告】玩家【{p.name}】籌碼歸零或為負數 ({p.chips} 點)！宣告倒莊！")
                bankrupt_detected = True
        return bankrupt_detected


# 將原本的測試區塊包裝成一個函式
def run_game_engine(human_player, other_players):
    players = [human_player] + other_players
    match = MahjongMatch(players=players, base_chips=30, tai_chips=10)
    match.play_match(max_hands=4) # 在背景執行四圈或指定局數

# 當 GUI 準備好時，啟動這支背景執行緒
# human_player 物件必須能被 GUI 存取，以便讀取 ui_state
def start_game(human_player, other_players):
    game_thread = threading.Thread(
        target=run_game_engine, 
        args=(human_player, other_players),
        daemon=True # 設定為 True，當 GUI 關閉時引擎也會自動終止
    )
    game_thread.start()