import random

class EventLibrary:
    def __init__(self):
        self.events = [
            {
                "description": "{pet_name}在河边发现了一颗闪亮的石头，心情大好！",
                "reward_type": "mood",
                "reward_value": 15,
                "money_gain": 5
            },
            {
                "description": "{pet_name}找到了一片美味的草地，饱餐一顿！",
                "reward_type": "satiety",
                "reward_value": 20,
                "money_gain": 3
            },
            {
                "description": "{pet_name}遇到了一位训练师，获得了战斗经验！",
                "reward_type": "exp",
                "reward_value": 25,
                "money_gain": 8
            },
            {
                "description": "{pet_name}在树丛中发现了一个宝箱！",
                "reward_type": "money",
                "reward_value": 0,
                "money_gain": 15
            },
            {
                "description": "{pet_name}帮助了迷路的小动物，感到非常满足！",
                "reward_type": "mood",
                "reward_value": 25,
                "money_gain": 0
            },
            {
                "description": "{pet_name}发现了一棵结满果实的树！",
                "reward_type": "satiety",
                "reward_value": 30,
                "money_gain": 5
            }
        ]
    
    def get_random_event(self, pet_name):
        event = random.choice(self.events).copy()
        event["description"] = event["description"].format(pet_name=pet_name)
        return event
