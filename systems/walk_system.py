import random
from datetime import datetime
from ..utils import event_library

class WalkSystem:
    def __init__(self, db, state_mgr, battle_sys):
        self.db = db
        self.state_mgr = state_mgr
        self.battle_sys = battle_sys
        self.event_lib = event_library.EventLibrary()
    
    async def handle_walk(self, user_id, group_id):
        pet = self.state_mgr.get_pet_with_decay(user_id, group_id)
        if not pet:
            return ["你还没有宠物，不能散步哦"]
        
        now = datetime.now()
        last_walk = datetime.fromisoformat(pet['last_walk_time'])
        if (now - last_walk).total_seconds() < 300:  # 5分钟冷却
            return [f"「{pet['pet_name']}」需要休息，{int(300 - (now - last_walk).total_seconds())}秒后再试"]
        
        final_reply = []
        
        # 70%概率触发事件，30%概率战斗
        if random.random() < 0.7:
            event = self.event_lib.get_random_event(pet['pet_name'])
            reward_type = event['reward_type']
            reward_value = event['reward_value']
            money_gain = event['money_gain']
            
            final_reply.append(f"奇遇发生！\n{event['description']}")
            final_reply.append(f"获得 {reward_value} {STAT_MAP[reward_type]}！")
            
            if money_gain > 0:
                final_reply.append(f"捡到了 ${money_gain}！")
            
            # 更新数据库
            updates = {
                reward_type: f"MIN(100, {reward_type} + {reward_value})" if reward_type != 'exp' 
                            else f"{reward_type} + {reward_value}",
                'money': f"money + {money_gain}",
                'last_walk_time': now.isoformat()
            }
            self.db.update_pet(user_id, group_id, updates)
            
            # 检查升级
            if reward_type == 'exp':
                final_reply.extend(self.state_mgr.check_level_up(user_id, group_id))
        else:
            # PVE战斗
            npc_level = max(1, pet['level'] + random.randint(-1, 1))
            npc_type = random.choice(list(PET_TYPES.keys()))
            npc_stats = PET_TYPES[npc_type]['initial_stats']
            
            npc_pet = {
                "pet_name": f"野生的{npc_type}",
                "pet_type": npc_type,
                "level": npc_level,
                "attack": npc_stats['attack'] + npc_level,
                "defense": npc_stats['defense'] + npc_level,
                "satiety": 100
            }
            
            battle_log, winner = self.battle_sys.run_battle(pet, npc_pet)
            final_reply.extend(battle_log)
            
            if winner == pet['pet_name']:
                exp_gain = npc_level * 5 + random.randint(1, 5)
                money_gain = random.randint(5, 15)
                final_reply.append(f"\n胜利奖励: {exp_gain} 经验 + ${money_gain}")
            else:
                exp_gain = 1
                money_gain = 0
                final_reply.append(f"\n安慰奖: {exp_gain} 经验")
            
            # 更新数据库
            self.db.update_pet(user_id, group_id, {
                'exp': f"exp + {exp_gain}",
                'money': f"money + {money_gain}",
                'last_walk_time': now.isoformat()
            })
            final_reply.extend(self.state_mgr.check_level_up(user_id, group_id))
        
        return final_reply
