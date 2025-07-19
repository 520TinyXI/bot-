import random
import logging
from datetime import datetime, timedelta
from core.db_manager import DatabaseManager
from core.config import ConfigManager
from utils.helpers import get_attribute_multiplier

class BattleManager:
    def __init__(self, db_manager: DatabaseManager, config: ConfigManager):
        self.db = db_manager
        self.config = config
        self.logger = logging.getLogger("BattleManager")
    
    def run_battle(self, pet1: dict, pet2: dict) -> tuple[list[str], str]:
        """执行两个宠物之间的对战"""
        # 从静态数据加载宠物类型
        with open(self.config.get_data_path("data") / "pet_types.json") as f:
            pet_types = json.load(f)
        
        log = []
        p1_hp = pet1['level'] * 10 + pet1['satiety']
        p2_hp = pet2['level'] * 10 + pet2['satiety']
        p1_name = pet1['pet_name']
        p2_name = pet2['pet_name']
        
        # 获取双方属性
        p1_attr = pet_types[pet1['pet_type']]['attribute']
        p2_attr = pet_types[pet2['pet_type']]['attribute']
        
        log.append(
            f"战斗开始！\n「{p1_name}」(Lv.{pet1['level']} {p1_attr}系) vs 「{p2_name}」(Lv.{pet2['level']} {p2_attr}系)")
        
        turn = 0
        while p1_hp > 0 and p2_hp > 0:
            turn += 1
            log.append(f"\n--- 第 {turn} 回合 ---")
            
            # 宠物1攻击
            multiplier1 = get_attribute_multiplier(p1_attr, p2_attr)
            base_dmg_to_p2 = max(1, int(pet1['attack'] * random.uniform(0.8, 1.2) - pet2['defense'] * 0.5))
            final_dmg_to_p2 = int(base_dmg_to_p2 * multiplier1)
            p2_hp -= final_dmg_to_p2
            
            log.append(f"「{p1_name}」发起了攻击！")
            if multiplier1 > 1.0:
                log.append("效果拔群！")
            elif multiplier1 < 1.0:
                log.append("效果不太理想…")
            log.append(f"对「{p2_name}」造成了 {final_dmg_to_p2} 点伤害！(剩余HP: {max(0, p2_hp)})")
            
            if p2_hp <= 0:
                break
            
            # 宠物2攻击
            multiplier2 = get_attribute_multiplier(p2_attr, p1_attr)
            base_dmg_to_p1 = max(1, int(pet2['attack'] * random.uniform(0.8, 1.2) - pet1['defense'] * 0.5))
            final_dmg_to_p1 = int(base_dmg_to_p1 * multiplier2)
            p1_hp -= final_dmg_to_p1
            
            log.append(f"「{p2_name}」进行了反击！")
            if multiplier2 > 1.0:
                log.append("效果拔群！")
            elif multiplier2 < 1.0:
                log.append("效果不太理想…")
            log.append(f"对「{p1_name}」造成了 {final_dmg_to_p1} 点伤害！(剩余HP: {max(0, p1_hp)})")
        
        winner_name = p1_name if p1_hp > 0 else p2_name
        log.append(f"\n战斗结束！胜利者是「{winner_name}」！")
        return log, winner_name
    
    def handle_battle(self, event, challenger_id: str, target_id: str):
        """处理PVP对决"""
        group_id = event.get_group_id()
        now = datetime.now()
        
        # 获取挑战者和被挑战者宠物
        challenger_pet = self.db.get_pet(challenger_id, group_id)
        target_pet = self.db.get_pet(target_id, group_id)
        
        # 检查冷却时间
        last_duel_challenger = datetime.fromisoformat(challenger_pet['last_duel_time'])
        if now - last_duel_challenger < timedelta(minutes=30):
            remaining = timedelta(minutes=30) - (now - last_duel_challenger)
            return [event.plain_result(f"你的对决技能正在冷却中，还需等待 {str(remaining).split('.')[0]}。")]
        
        last_duel_target = datetime.fromisoformat(target_pet['last_duel_time'])
        if now - last_duel_target < timedelta(minutes=30):
            remaining = timedelta(minutes=30) - (now - last_duel_target)
            return [event.plain_result(f"对方的宠物正在休息，还需等待 {str(remaining).split('.')[0]} 才能接受对决。")]
        
        # 执行战斗
        battle_log, winner_name = self.run_battle(challenger_pet, target_pet)
        
        # 处理奖励
        money_gain = 20
        if winner_name == challenger_pet['pet_name']:
            winner_id, loser_id = challenger_id, target_id
            winner_exp = 10 + target_pet['level'] * 2
            loser_exp = 5 + challenger_pet['level']
        else:
            winner_id, loser_id = target_id, challenger_id
            winner_exp = 10 + challenger_pet['level'] * 2
            loser_exp = 5 + target_pet['level']
        
        final_reply = list(battle_log)
        final_reply.append(
            f"\n对决结算：胜利者获得了 {winner_exp} 点经验值和 ${money_gain}，参与者获得了 {loser_exp} 点经验值。")
        
        # 更新数据库
        updates = {
            'last_duel_time': now.isoformat(),
            'exp': f"exp + {winner_exp}",
            'money': f"money + {money_gain}"
        }
        self.db.update_pet(winner_id, group_id, updates)
        
        updates = {
            'last_duel_time': now.isoformat(),
            'exp': f"exp + {loser_exp}"
        }
        self.db.update_pet(loser_id, group_id, updates)
        
        # 检查升级
        final_reply.extend(self.pet_mgr.check_level_up(winner_id, group_id))
        final_reply.extend(self.pet_mgr.check_level_up(loser_id, group_id))
        
        return [event.plain_result("\n".join(final_reply))]
