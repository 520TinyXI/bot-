from datetime import datetime, timedelta

class DuelSystem:
    def __init__(self, db, state_mgr, battle_sys):
        self.db = db
        self.state_mgr = state_mgr
        self.battle_sys = battle_sys
    
    async def handle_duel(self, event, user_id, group_id):
        if not group_id:
            return ["该功能仅限群聊使用"]
        
        # 获取被@的用户 - 使用修复后的get_at方法
        target_id = PetPlugin.get_at(event)
        if not target_id:
            return ["请@一位你想对决的群友"]
        
        if user_id == target_id:
            return ["不能和自己对决哦"]
        
        # 获取双方宠物
        challenger_pet = self.state_mgr.get_pet_with_decay(user_id, group_id)
        target_pet = self.state_mgr.get_pet_with_decay(target_id, group_id)
        
        if not challenger_pet:
            return ["你还没有宠物，无法对决"]
        if not target_pet:
            return ["对方还没有宠物"]
        
        # 确保宠物数据完整
        if 'pet_name' not in challenger_pet:
            challenger_pet['pet_name'] = "你的宠物"
        if 'pet_name' not in target_pet:
            target_pet['pet_name'] = "对方的宠物"
        
        now = datetime.now()
        
        # 检查冷却时间
        if not self._check_cooldown(challenger_pet, now):
            return ["你的对决技能正在冷却中"]
        if not self._check_cooldown(target_pet, now):
            return ["对方的宠物正在休息"]
        
        # 进行对战
        battle_log, winner_name = self.battle_sys.run_battle(challenger_pet, target_pet)
        result = list(battle_log)
        
        # 对战奖励
        money_gain = 20
        if winner_name == challenger_pet['pet_name']:
            winner_id, loser_id = user_id, target_id
            winner_exp = 10 + target_pet['level'] * 2
            loser_exp = 5 + challenger_pet['level']
        else:
            winner_id, loser_id = target_id, user_id
            winner_exp = 10 + challenger_pet['level'] * 2
            loser_exp = 5 + target_pet['level']
        
        result.append(
            f"\n对决奖励：胜利者获得 {winner_exp}经验 + ${money_gain}，"
            f"参与者获得 {loser_exp}经验"
        )
        
        # 更新数据库
        self._update_after_duel(
            user_id, group_id, target_id, 
            winner_id, winner_exp, loser_exp, 
            money_gain, now
        )
        
        return result
    
    def _check_cooldown(self, pet_data, now):
        last_duel = datetime.fromisoformat(pet_data['last_duel_time'])
        return (now - last_duel).total_seconds() >= 1800  # 30分钟
    
    def _update_after_duel(self, user_id, group_id, target_id, winner_id, 
                          winner_exp, loser_exp, money_gain, now):
        # 更新挑战者
        self.db.update_pet(user_id, group_id, {
            'exp': f"exp + {winner_exp if user_id == winner_id else loser_exp}",
            'money': f"money + {money_gain if user_id == winner_id else 0}",
            'last_duel_time': now.isoformat()
        })
        
        # 更新被挑战者
        self.db.update_pet(target_id, group_id, {
            'exp': f"exp + {winner_exp if target_id == winner_id else loser_exp}",
            'money': f"money + {money_gain if target_id == winner_id else 0}",
            'last_duel_time': now.isoformat()
        })
