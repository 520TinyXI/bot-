# modules/pet_battle.py - 战斗系统
import random
from datetime import datetime

class BattleManager:
    def __init__(self, db_manager, pet_types, stat_map):
        self.db = db_manager
        self.pet_types = pet_types
        self.stat_map = stat_map
        self.WILD_BATTLE_COOLDOWN = 300  # 5分钟
        self.PVP_COOLDOWN = 1800  # 30分钟
        
    async def handle_battle(self, event, battle_type):
        """处理战斗命令"""
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        
        if battle_type == "pvp":
            return await self._handle_pvp(event, user_id, group_id)
        elif battle_type == "pve":
            return await self._handle_pve(event, user_id, group_id)
        else:
            return event.plain_result("未知战斗类型")
    
    async def _handle_pvp(self, event, user_id, group_id):
        """玩家对战逻辑"""
        at_info = self._get_at(event)
        if not at_info:
            return event.plain_result("请@一位你想对决的群友。用法: /对决 @某人")
            
        target_id = at_info
        if user_id == target_id:
            return event.plain_result("不能和自己对决哦。")
            
        challenger_pet = self.db.get_pet(user_id, group_id)
        if not challenger_pet:
            return event.plain_result("你还没有宠物，无法发起对决。")
            
        target_pet = self.db.get_pet(target_id, group_id)
        if not target_pet:
            return event.plain_result("对方还没有宠物呢。")
            
        now = datetime.now()
        
        # 检查冷却时间
        if not self.db.check_cooldown(user_id, group_id, "duel", self.PVP_COOLDOWN):
            return event.plain_result("你的对决技能正在冷却中，请稍后再试。")
            
        if not self.db.check_cooldown(target_id, group_id, "duel", self.PVP_COOLDOWN):
            return event.plain_result("对方的宠物正在休息，请稍后再试。")
            
        # 执行战斗
        battle_log, winner_name = self._run_battle(challenger_pet, target_pet)
        
        # 设置冷却时间
        self.db.set_cooldown(user_id, group_id, "duel", now)
        self.db.set_cooldown(target_id, group_id, "duel", now)
        
        # 奖励结算
        money_gain = 20
        if winner_name == challenger_pet['pet_name']:
            winner_id, loser_id = user_id, target_id
            winner_exp = 10 + target_pet['level'] * 2
            loser_exp = 5 + challenger_pet['level']
        else:
            winner_id, loser_id = target_id, user_id
            winner_exp = 10 + challenger_pet['level'] * 2
            loser_exp = 5 + target_pet['level']
            
        # 更新数据库
        self.db.update_pet(winner_id, group_id, {
            "exp": winner_exp,
            "money": money_gain
        })
        self.db.update_pet(loser_id, group_id, {"exp": loser_exp})
        
        # 构建结果
        result = "\n".join(battle_log)
        result += f"\n\n对决结算：胜利者获得了 {winner_exp} 点经验值和 ${money_gain}，参与者获得了 {loser_exp} 点经验值。"
        return event.plain_result(result)
    
    async def _handle_pve(self, event, user_id, group_id):
        """PVE战斗逻辑"""
        pet = self.db.get_pet(user_id, group_id)
        if not pet:
            return event.plain_result("你还没有宠物，无法战斗。")
            
        # 创建野生宠物
        npc_level = max(1, pet['level'] + random.randint(-1, 1))
        npc_type = random.choice(list(self.pet_types.keys()))
        npc_stats = self.pet_types[npc_type]['initial_stats']
        
        npc_pet = {
            "pet_name": f"野生的{npc_type}",
            "pet_type": npc_type,
            "level": npc_level,
            "attack": npc_stats['attack'] + npc_level,
            "defense": npc_stats['defense'] + npc_level,
            "satiety": 100
        }
        
        # 执行战斗
        battle_log, winner_name = self._run_battle(pet, npc_pet)
        result = ["野外遭遇战！"] + battle_log
        
        # 奖励结算
        exp_gain = 0
        money_gain = 0
        if winner_name == pet['pet_name']:
            exp_gain = npc_level * 5 + random.randint(1, 5)
            money_gain = random.randint(5, 15)
            result.append(f"\n胜利了！你获得了 {exp_gain} 点经验值和 ${money_gain} 赏金！")
        else:
            exp_gain = 1
            result.append(f"\n很遗憾，你的宠物战败了，但也获得了 {exp_gain} 点经验。")
            
        # 更新数据库
        self.db.update_pet(user_id, group_id, {
            "exp": exp_gain,
            "money": money_gain
        })
        
        return event.plain_result("\n".join(result))
    
    def _run_battle(self, pet1: dict, pet2: dict) -> tuple[list[str], str]:
        """执行战斗逻辑"""
        log = []
        p1_hp = pet1['level'] * 10 + pet1['satiety']
        p2_hp = pet2['level'] * 10 + pet2['satiety']
        p1_name = pet1['pet_name']
        p2_name = pet2['pet_name']

        # 获取属性
        p1_attr = self.pet_types[pet1['pet_type']]['attribute']
        p2_attr = self.pet_types[pet2['pet_type']]['attribute']

        log.append(
            f"战斗开始！\n「{p1_name}」(Lv.{pet1['level']} {p1_attr}系) vs 「{p2_name}」(Lv.{pet2['level']} {p2_attr}系)")

        turn = 0
        while p1_hp > 0 and p2_hp > 0:
            turn += 1
            log.append(f"\n--- 第 {turn} 回合 ---")

            # 宠物1攻击
            multiplier1 = self._get_attribute_multiplier(p1_attr, p2_attr)
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
            multiplier2 = self._get_attribute_multiplier(p2_attr, p1_attr)
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

    def _get_attribute_multiplier(self, attacker_attr: str, defender_attr: str) -> float:
        """属性克制计算"""
        effectiveness = {"水": "火", "火": "草", "草": "水"}
        if effectiveness.get(attacker_attr) == defender_attr:
            return 1.5
        if effectiveness.get(defender_attr) == attacker_attr:
            return 0.5
        return 1.0
    
    @staticmethod
    def _get_at(event) -> str | None:
        return next(
            (
                str(seg.qq)
                for seg in event.get_messages()
                if isinstance(seg, At) and str(seg.qq) != event.get_self_id()
            ),
            None,
        )
