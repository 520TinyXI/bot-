
import random
import json
import logging
from datetime import datetime
from core.db_manager import DatabaseManager
from core.config import ConfigManager
from core.pet_manager import PetManager
from utils.llm_integration import generate_random_event
from utils.helpers import extract_json_from_text
from systems.battle_system import BattleManager

class WalkManager:
    def __init__(self, db_manager: DatabaseManager, config: ConfigManager, pet_manager: PetManager):
        self.db = db_manager
        self.config = config
        self.pet_mgr = pet_manager
        self.battle_sys = BattleManager(db_manager, config)
        self.logger = logging.getLogger("WalkManager")
        
        # 加载状态映射
        with open(self.config.get_data_path("data") / "stat_map.json") as f:
            self.stat_map = json.load(f)
    
    def handle_walk(self, event):
        """处理散步逻辑"""
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        pet = self.db.get_pet(user_id, group_id)
        now = datetime.now()
        
        # 检查冷却时间
        last_walk = datetime.fromisoformat(pet['last_walk_time'])
        if now - last_walk < timedelta(minutes=5):
            return [event.plain_result(f"刚散步回来，让「{pet['pet_name']}」休息一下吧。")]
        
        final_reply = []
        if random.random() < 0.7:
            # 生成随机奇遇事件
            response = generate_random_event(pet['pet_name'])
            
            if response and 'completion_text' in response:
                json_str = extract_json_from_text(response['completion_text'])
                
                if json_str:
                    try:
                        data = json.loads(json_str)
                        desc = data['description'].format(pet_name=pet['pet_name'])
                        reward_type = data['reward_type']
                        reward_value = int(data['reward_value'])
                        money_gain = int(data.get('money_gain', 0))
                        
                        reward_type_chinese = self.stat_map.get(reward_type, reward_type)
                        final_reply.append(f"奇遇发生！\n{desc}\n你的宠物获得了 {reward_value} 点{reward_type_chinese}！")
                        
                        if money_gain > 0:
                            final_reply.append(f"意外之喜！你在路边捡到了 ${money_gain}！")
                        
                        # 更新数据库
                        updates = {
                            reward_type: f"{reward_type} + {reward_value}",
                            'money': f"money + {money_gain}",
                            'last_walk_time': now.isoformat()
                        }
                        self.db.update_pet(user_id, group_id, updates)
                        
                        if reward_type == 'exp':
                            final_reply.extend(self.pet_mgr.check_level_up(user_id, group_id))
                    
                    except (json.JSONDecodeError, KeyError) as e:
                        self.logger.error(f"奇遇事件处理失败: {e}")
                        final_reply.append("你的宠物在外面迷路了，好在最后成功找回，但什么也没发生。")
                else:
                    self.logger.error("无法从LLM响应中提取JSON")
                    final_reply.append("散步时发生了一些意外，但宠物安全回来了。")
            else:
                final_reply.append("散步时发生了一些意外，但宠物安全回来了。")
        else:
            # 遭遇野生宠物
            with open(self.config.get_data_path("data") / "pet_types.json") as f:
                pet_types = json.load(f)
            
            npc_level = max(1, pet['level'] + random.randint(-1, 1))
            npc_type_name = random.choice(list(pet_types.keys()))
            npc_stats = pet_types[npc_type_name]['initial_stats']
            
            npc_pet = {
                "pet_name": f"野生的{npc_type_name}",
                "pet_type": npc_type_name,
                "level": npc_level,
                "attack": npc_stats['attack'] + npc_level,
                "defense": npc_stats['defense'] + npc_level,
                "satiety": 100
            }
            
            battle_log, winner_name = self.battle_sys.run_battle(pet, npc_pet)
            final_reply.extend(battle_log)
            
            exp_gain = 0
            money_gain = 0
            if winner_name == pet['pet_name']:
                exp_gain = npc_level * 5 + random.randint(1, 5)
                money_gain = random.randint(5, 15)
                final_reply.append(f"\n胜利了！你获得了 {exp_gain} 点经验值和 ${money_gain} 赏金！")
            else:
                exp_gain = 1
                final_reply.append(f"\n很遗憾，你的宠物战败了，但也获得了 {exp_gain} 点经验。")
            
            # 更新数据库
            updates = {
                'exp': f"exp + {exp_gain}",
                'money': f"money + {money_gain}",
                'last_walk_time': now.isoformat()
            }
            self.db.update_pet(user_id, group_id, updates)
            
            final_reply.extend(self.pet_mgr.check_level_up(user_id, group_id))
        
        return [event.plain_result("\n".join(final_reply))]
