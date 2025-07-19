# modules/pet_core.py - 宠物核心管理
import random
from datetime import datetime
from modules.pet_image import ImageManager

class CoreManager:
    def __init__(self, db_manager, image_manager, pet_types):
        self.db = db_manager
        self.image_manager = image_manager
        self.pet_types = pet_types
        
    async def handle_core(self, event, action, *args):
        """处理核心命令"""
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        
        if not group_id:
            return event.plain_result("该功能仅限群聊使用哦。")
            
        if action == "adopt":
            return await self._adopt_pet(event, user_id, group_id, args[0] if args else None)
        elif action == "status":
            return await self._pet_status(event, user_id, group_id)
        elif action == "evolve":
            return await self._evolve_pet(event, user_id, group_id)
        else:
            return event.plain_result("未知操作")
    
    async def _adopt_pet(self, event, user_id, group_id, pet_name):
        """领养宠物逻辑"""
        if self.db.get_pet(user_id, group_id):
            return event.plain_result("你在这个群里已经有一只宠物啦！")
            
        pet_type = random.choice(list(self.pet_types.keys()))
        stats = self.pet_types[pet_type]['initial_stats']
        
        if not pet_name:
            pet_name = pet_type
            
        self.db.create_pet(user_id, group_id, pet_name, pet_type, stats)
        return event.plain_result(
            f"恭喜你，{event.get_sender_name()}！你成功领养了「{pet_name}」({pet_type})！")
    
    async def _pet_status(self, event, user_id, group_id):
        """宠物状态查询"""
        pet = self.db.get_pet(user_id, group_id)
        if not pet:
            return event.plain_result("你还没有宠物哦，快发送 /领养宠物 来选择一只吧！")
            
        image_path = self.image_manager.generate_status_image(pet, event.get_sender_name())
        if image_path:
            return event.image_result(str(image_path))
        else:
            return event.plain_result("生成状态图失败")
    
    async def _evolve_pet(self, event, user_id, group_id):
        """宠物进化"""
        pet = self.db.get_pet(user_id, group_id)
        if not pet:
            return event.plain_result("你还没有宠物哦。")
            
        pet_type_info = self.pet_types[pet['pet_type']]
        current_evo = pet_type_info['evolutions'][pet['evolution_stage']]
        
        if not current_evo['evolve_level']:
            return event.plain_result(f"「{pet['pet_name']}」已是最终形态，无法再进化。")
            
        if pet['level'] < current_evo['evolve_level']:
            return event.plain_result(f"「{pet['pet_name']}」需达到 Lv.{current_evo['evolve_level']} 才能进化。")
            
        next_stage = pet['evolution_stage'] + 1
        new_attack = pet['attack'] + random.randint(8, 15)
        new_defense = pet['defense'] + random.randint(8, 15)
        
        self.db.update_pet(user_id, group_id, {
            "evolution_stage": next_stage,
            "attack": new_attack,
            "defense": new_defense
        })
        
        next_evo = pet_type_info['evolutions'][next_stage]
        return event.plain_result(
            f"光芒四射！你的「{pet['pet_name']}」成功进化为「{next_evo['name']}」！")
    
    def _exp_for_next_level(self, level: int) -> int:
        """计算升级所需经验"""
        return int(10 * (level ** 1.5))
    
    def check_level_up(self, user_id: str, group_id: str) -> list[str]:
        """检查并处理升级"""
        level_up_messages = []
        while True:
            pet = self.db.get_pet(user_id, group_id)
            if not pet:
                break
                
            exp_needed = self._exp_for_next_level(pet['level'])
            if pet['exp'] >= exp_needed:
                new_level = pet['level'] + 1
                remaining_exp = pet['exp'] - exp_needed
                new_attack = pet['attack'] + random.randint(1, 2)
                new_defense = pet['defense'] + random.randint(1, 2)
                
                self.db.update_pet(user_id, group_id, {
                    "level": new_level,
                    "exp": remaining_exp,
                    "attack": new_attack,
                    "defense": new_defense
                })
                
                level_up_messages.append(f"🎉 恭喜！你的宠物「{pet['pet_name']}」升级到了 Lv.{new_level}！")
            else:
                break
                
        return level_up_messages
