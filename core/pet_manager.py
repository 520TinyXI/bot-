import random
import logging
from datetime import datetime, timedelta
from core.db_manager import DatabaseManager
from core.config import ConfigManager
from utils.image_generator import generate_pet_status_image

class PetManager:
    def __init__(self, db_manager: DatabaseManager, config: ConfigManager):
        self.db = db_manager
        self.config = config
        self.logger = logging.getLogger("PetManager")
    
    def _exp_for_next_level(self, level: int) -> int:
        """计算升到下一级所需经验"""
        return int(10 * (level ** 1.5))
    
    def check_level_up(self, user_id: str, group_id: str) -> list[str]:
        """检查并处理宠物升级"""
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
                
                self.db.level_up_pet(user_id, group_id, new_level, remaining_exp, new_attack, new_defense)
                self.logger.info(f"宠物 {pet['pet_name']} 升到了 {new_level} 级！")
                level_up_messages.append(f"🎉 恭喜！你的宠物「{pet['pet_name']}」升级到了 Lv.{new_level}！")
            else:
                break
        return level_up_messages
    
    def handle_adopt(self, event, pet_name: str | None = None):
        """处理领养宠物"""
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        
        if self.db.get_pet(user_id, group_id):
            return [event.plain_result("你在这个群里已经有一只宠物啦！发送 /我的宠物 查看。")]
        
        # 从静态数据加载宠物类型
        with open(self.config.get_data_path("data") / "pet_types.json") as f:
            pet_types = json.load(f)
        
        type_name = random.choice(list(pet_types.keys()))
        pet_info = pet_types[type_name]
        stats = pet_info['initial_stats']
        
        if not pet_name:
            pet_name = type_name
        
        self.db.create_pet(user_id, group_id, pet_name, type_name, stats)
        self.logger.info(f"新宠物领养: 群 {group_id} 用户 {user_id} 随机领养了 {type_name} - {pet_name}")
        
        return [event.plain_result(
            f"恭喜你，{event.get_sender_name()}！命运让你邂逅了「{pet_name}」({type_name})！\n发送 /我的宠物 查看它的状态吧。")]
    
    def handle_status(self, event):
        """处理宠物状态查看"""
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        pet = self.db.get_pet(user_id, group_id)
        
        if not pet:
            return [event.plain_result("你还没有宠物哦，快发送 /领养宠物 来选择一只吧！")]
        
        # 从静态数据加载宠物类型
        with open(self.config.get_data_path("data") / "pet_types.json") as f:
            pet_types = json.load(f)
        
        image_path = generate_pet_status_image(pet, pet_types, event.get_sender_name(), self.config)
        
        if isinstance(image_path, Path):
            return [event.image_result(str(image_path))]
        else:
            return [event.plain_result(image_path)]
