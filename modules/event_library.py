# modules/event_library.py - 事件库
import random

class EventLibrary:
    def __init__(self):
        self.events = [
            {
                "description": "在森林中发现了一处清澈的泉水，{pet_name}喝下后感觉精神焕发。",
                "reward_type": "mood",
                "reward_value": random.randint(15, 25),
                "money_gain": random.randint(1, 5)
            },
            {
                "description": "{pet_name}在树丛中找到了一个被遗忘的宝箱，里面有些许财宝。",
                "reward_type": "money",
                "reward_value": 0,
                "money_gain": random.randint(10, 20)
            },
            {
                "description": "发现了一片野果林，{pet_name}大快朵颐。",
                "reward_type": "satiety",
                "reward_value": random.randint(20, 30),
                "money_gain": random.randint(0, 3)
            },
            {
                "description": "{pet_name}帮助了一只受伤的小动物，获得了经验奖励。",
                "reward_type": "exp",
                "reward_value": random.randint(10, 20),
                "money_gain": 0
            },
            {
                "description": "在探险途中，{pet_name}发现了一个训练场，进行了实战训练。",
                "reward_type": "exp",
                "reward_value": random.randint(15, 25),
                "money_gain": random.randint(5, 10)
            },
            {
                "description": "{pet_name}在花丛中玩耍，心情变得格外愉悦。",
                "reward_type": "mood",
                "reward_value": random.randint(20, 30),
                "money_gain": 0
            }
        ]
    
    def get_random_event(self, pet_name: str) -> dict:
        """获取随机事件"""
        event = random.choice(self.events).copy()
        event["description"] = event["description"].format(pet_name=pet_name)
        return event
