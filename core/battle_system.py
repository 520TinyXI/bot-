import random
from ..constants import PET_TYPES

class BattleSystem:
    def __init__(self, db, state_mgr):
        self.db = db
        self.state_mgr = state_mgr
    
    def run_battle(self, pet1_data, pet2_data):
        log = []
        p1_hp = self._calculate_hp(pet1_data)
        p2_hp = self._calculate_hp(pet2_data)
        
        p1_attr = PET_TYPES[pet1_data['pet_type']]['attribute']
        p2_attr = PET_TYPES[pet2_data['pet_type']]['attribute']
        
        log.append(
            f"⚔️ 战斗开始！\n"
            f"「{pet1_data['pet_name']}」(Lv.{pet1_data['level']} {p1_attr}系) vs "
            f"「{pet2_data['pet_name']}」(Lv.{pet2_data['level']} {p2_attr}系)"
        )
        
        turn = 0
        while p1_hp > 0 and p2_hp > 0:
            turn += 1
            log.append(f"\n--- 第 {turn} 回合 ---")
            
            # 宠物1攻击
            multiplier = self._get_attribute_multiplier(p1_attr, p2_attr)
            dmg = self._calculate_damage(pet1_data, pet2_data, multiplier)
            p2_hp -= dmg
            log.extend(self._format_attack_log(
                pet1_data['pet_name'], pet2_data['pet_name'], dmg, p2_hp, multiplier
            ))
            
            if p2_hp <= 0:
                break
                
            # 宠物2反击
            multiplier = self._get_attribute_multiplier(p2_attr, p1_attr)
            dmg = self._calculate_damage(pet2_data, pet1_data, multiplier)
            p1_hp -= dmg
            log.extend(self._format_attack_log(
                pet2_data['pet_name'], pet1_data['pet_name'], dmg, p1_hp, multiplier
            ))
        
        winner = pet1_data if p1_hp > 0 else pet2_data
        log.append(f"\n🎉 战斗结束！胜利者是「{winner['pet_name']}」！")
        return log, winner['pet_name']
    
    def _calculate_hp(self, pet_data):
        return pet_data['level'] * 10 + pet_data['satiety']
    
    def _calculate_damage(self, attacker, defender, multiplier):
        base_dmg = max(1, int(
            attacker['attack'] * random.uniform(0.8, 1.2) - 
            defender['defense'] * 0.5
        ))
        return int(base_dmg * multiplier)
    
    def _get_attribute_multiplier(self, attacker_attr, defender_attr):
        effectiveness = {"水": "火", "火": "草", "草": "水"}
        if effectiveness.get(attacker_attr) == defender_attr:
            return 1.5  # 克制
        if effectiveness.get(defender_attr) == attacker_attr:
            return 0.5  # 被克制
        return 1.0  # 普通
    
    def _format_attack_log(self, attacker, defender, damage, remaining_hp, multiplier):
        log = [f"「{attacker}」发动攻击！"]
        if multiplier > 1.0:
            log.append("效果拔群！")
        elif multiplier < 1.0:
            log.append("效果不太理想…")
        log.append(f"对「{defender}」造成 {damage} 点伤害！(剩余HP: {max(0, remaining_hp)})")
        return log
