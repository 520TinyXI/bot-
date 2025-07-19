from ..constants import PET_TYPES

class EvolutionSystem:
    def __init__(self, db):
        self.db = db
    
    def handle_evolution(self, user_id, group_id):
        pet = self.db.get_pet(user_id, group_id)
        if not pet:
            return "❌ 你还没有宠物"
        
        pet_type_info = PET_TYPES[pet['pet_type']]
        current_stage = pet['evolution_stage']
        current_evo = pet_type_info['evolutions'][current_stage]
        
        # 检查是否可以进化
        if not current_evo['evolve_level']:
            return f"❌ 「{pet['pet_name']}」已是最终形态"
        
        if pet['level'] < current_evo['evolve_level']:
            return f"❌ 需要 Lv.{current_evo['evolve_level']} 才能进化"
        
        # 执行进化
        next_stage = current_stage + 1
        next_evo = pet_type_info['evolutions'][next_stage]
        attack_boost = random.randint(8, 15)
        defense_boost = random.randint(8, 15)
        
        self.db.update_pet(user_id, group_id, {
            'evolution_stage': next_stage,
            'attack': f"attack + {attack_boost}",
            'defense': f"defense + {defense_boost}"
        })
        
        return (
            f"✨ 进化成功！\n"
            f"「{pet['pet_name']}」进化为「{next_evo['name']}」！\n"
            f"攻击力 +{attack_boost}，防御力 +{defense_boost}"
        )
