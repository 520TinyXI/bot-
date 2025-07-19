from ..constants import SHOP_ITEMS, STAT_MAP

class ShopSystem:
    def __init__(self, db):
        self.db = db
    
    def display_shop(self):
        shop_text = "🏪 宠物商店 🏪\n================\n"
        for name, item in SHOP_ITEMS.items():
            shop_text += f"【{name}】 ${item['price']}\n{item['description']}\n"
        shop_text += "================\n使用 /购买 [物品名] [数量] 购买"
        return shop_text
    
    def display_backpack(self, user_id, group_id):
        items = self.db.get_inventory(user_id, group_id)
        if not items:
            return "👜 你的背包空空如也"
        
        backpack = "👜 你的背包\n================\n"
        for item_name, quantity in items:
            backpack += f"{item_name} × {quantity}\n"
        return backpack
    
    def handle_purchase(self, user_id, group_id, item_name, quantity):
        if item_name not in SHOP_ITEMS:
            return f"❌ 商店没有「{item_name}」"
        
        item = SHOP_ITEMS[item_name]
        total_cost = item['price'] * quantity
        
        # 检查金钱是否足够
        pet = self.db.get_pet(user_id, group_id)
        if not pet or pet['money'] < total_cost:
            return f"❌ 金钱不足！需要 ${total_cost}"
        
        # 扣钱
        self.db.update_pet(user_id, group_id, {'money': f"money - {total_cost}"})
        
        # 添加物品到背包
        self.db.add_item_to_inventory(user_id, group_id, item_name, quantity)
        
        return f"✅ 购买成功！获得 {quantity}个「{item_name}」"
    
    def handle_feeding(self, user_id, group_id, item_name):
        if item_name not in SHOP_ITEMS or SHOP_ITEMS[item_name]['type'] != 'food':
            return f"❌ 「{item_name}」不是食物"
        
        # 检查背包中是否有该物品
        items = dict(self.db.get_inventory(user_id, group_id))
        if item_name not in items or items[item_name] < 1:
            return f"❌ 背包中没有「{item_name}」"
        
        # 从背包移除物品
        self.db.remove_item_from_inventory(user_id, group_id, item_name)
        
        # 更新宠物状态
        item = SHOP_ITEMS[item_name]
        updates = {
            'satiety': f"MIN(100, satiety + {item['satiety']})",
            'mood': f"MIN(100, mood + {item['mood']})"
        }
        self.db.update_pet(user_id, group_id, updates)
        
        pet = self.db.get_pet(user_id, group_id)
        return (
            f"🍖 投喂成功！「{pet['pet_name']}」\n"
            f"{STAT_MAP['satiety']}+{item['satiety']} "
            f"{STAT_MAP['mood']}+{item['mood']}"
        )
