import random
import logging
from core.db_manager import DatabaseManager
from core.config import ConfigManager

class EvolutionManager:
    def __init__(self, db_manager: DatabaseManager, config: ConfigManager):
        self.db = db_manager
        self.config = config
        self.logger = logging.getLogger("EvolutionManager")
        
        # 加载宠物类型
        with open(self.config.get_data_path("data") / "pet_types.json") as f:
            self.pet_types = json.load(f)
    
    def handle_evolution(self, event):
        """处理宠物进化"""
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        pet = self.db.get_pet(user_id, group_id)
        
        if not pet:
            return [event.plain_result("你还没有宠物哦。")]
        
        pet_type_info = self.pet_types[pet['pet_type']]
        current_evo_info = pet_type_info['evolutions'][pet['evolution_stage']]
        
        evolve_level = current_evo_info['evolve_level']
        if not evolve_level:
            return [event.plain_result(f"「{pet['pet_name']}」已是最终形态，无法再进化。")]
        
        if pet['level'] < evolve_level:
            return [event.plain_result(f"「{pet['pet_name']}」需达到 Lv.{evolve_level} 才能进化。")]
        
        next_evo_stage = pet['evolution_stage'] + 1
        next_evo_info = pet_type_info['evolutions'][next_evo_stage]
        new_attack = pet['attack'] + random.randint(8, 15)
        new_defense = pet['defense'] + random.randint(8, 15)
        
        # 更新数据库
        updates = {
            'evolution_stage': next_evo_stage,
            'attack': new_attack,
            'defense': new_defense
        }
        self.db.update_pet(user_id, group_id, updates)
        
        self.logger.info(f"宠物进化成功: {pet['pet_name']} -> {next_evo_info['name']}")
        return [event.plain_result(
            f"光芒四射！你的「{pet['pet_name']}」成功进化为了「{next_evo_info['name']}」！各项属性都得到了巨幅提升！")]
