import random
from datetime import datetime, timedelta
from .database_manager import DatabaseManager

class StateManager:
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def get_pet_with_decay(self, user_id, group_id):
        pet = self.db.get_pet(user_id, group_id)
        if not pet:
            return None
        
        now = datetime.now()
        last_updated = datetime.fromisoformat(pet['last_updated_time'])
        
        # 计算离线衰减
        hours_passed = (now - last_updated).total_seconds() / 3600
        if hours_passed >= 1:
            decay_hours = int(hours_passed)
            satiety_decay = 3 * decay_hours
            mood_decay = 2 * decay_hours
            
            new_satiety = max(0, pet['satiety'] - satiety_decay)
            new_mood = max(0, pet['mood'] - mood_decay)
            
            # 更新数据库
            self.db.update_pet(user_id, group_id, {
                'satiety': new_satiety,
                'mood': new_mood,
                'last_updated_time': now.isoformat()
            })
            
            # 更新返回数据
            pet['satiety'] = new_satiety
            pet['mood'] = new_mood
        
        return dict(pet)
    
    def check_level_up(self, user_id, group_id):
        level_up_messages = []
        while True:
            pet = self.get_pet_with_decay(user_id, group_id)
            if not pet:
                break
                
            exp_needed = self._exp_for_next_level(pet['level'])
            if pet['exp'] >= exp_needed:
                new_level = pet['level'] + 1
                remaining_exp = pet['exp'] - exp_needed
                new_attack = pet['attack'] + random.randint(1, 2)
                new_defense = pet['defense'] + random.randint(1, 2)
                
                self.db.update_pet(user_id, group_id, {
                    'level': new_level,
                    'exp': remaining_exp,
                    'attack': new_attack,
                    'defense': new_defense
                })
                
                level_up_messages.append(
                    f"🎉 恭喜！「{pet['pet_name']}」升级到了 Lv.{new_level}！"
                )
            else:
                break
        return level_up_messages
    
    def _exp_for_next_level(self, level):
        return int(10 * (level ** 1.5))
