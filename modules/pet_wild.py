# modules/pet_wild.py - 打野系统
import random
from datetime import datetime

class WildManager:
    def __init__(self, db_manager, battle_manager, event_library, pet_types, stat_map):
        self.db = db_manager
        self.battle = battle_manager
        self.events = event_library
        self.pet_types = pet_types
        self.stat_map = stat_map
        self.COOLDOWN = 300  # 5分钟冷却
        
    async def handle_wild(self, event):
        """处理打野命令"""
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        
        if not group_id:
            return event.plain_result("该功能仅限群聊使用哦。")
            
        pet = self.db.get_pet(user_id, group_id)
        if not pet:
            return event.plain_result("你还没有宠物，不能去打野哦。")
            
        # 检查冷却时间
        if not self.db.check_cooldown(user_id, group_id, "walk", self.COOLDOWN):
            return event.plain_result(f"刚打野回来，让「{pet['pet_name']}」休息一下吧。")
            
        # 更新冷却时间
        self.db.set_cooldown(user_id, group_id, "walk", datetime.now())
        
        # 随机事件或战斗 (70%概率事件，30%概率战斗)
        if random.random() < 0.7:
            return await self._handle_event(event, user_id, group_id, pet)
        else:
            return await self.battle.handle_battle(event, "pve")
    
    async def _handle_event(self, event, user_id, group_id, pet):
        """处理随机事件"""
        # 从事件库获取随机事件
        event_data = self.events.get_random_event(pet['pet_name'])
        
        # 应用事件效果
        reward_type = event_data["reward_type"]
        reward_value = event_data["reward_value"]
        money_gain = event_data["money_gain"]
        
        # 构建回复消息
        result = [f"探险奇遇！{event_data['description']}"]
        result.append(f"你的宠物获得了 {reward_value} 点{self.stat_map.get(reward_type, reward_type)}！")
        
        if money_gain > 0:
            result.append(f"意外之喜！你在探险中发现了 ${money_gain}！")
            
        # 更新数据库
        updates = {
            reward_type: min(100, pet.get(reward_type, 0) + reward_value),
            "money": pet.get("money", 0) + money_gain
        }
        self.db.update_pet(user_id, group_id, updates)
        
        return event.plain_result("\n".join(result))
