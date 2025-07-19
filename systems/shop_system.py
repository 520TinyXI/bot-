import logging
from core.db_manager import DatabaseManager
from core.config import ConfigManager

class ShopManager:
    def __init__(self, db_manager: DatabaseManager, config: ConfigManager):
        self.db = db_manager
        self.config = config
        self.logger = logging.getLogger("ShopManager")
        
        # 加载商店物品
        with open(self.config.get_data_path("data") / "shop_items.json") as f:
            self.shop_items = json.load(f)
        
        # 加载状态映射
        with open(self.config.get_data_path("data") / "stat_map.json") as f:
            self.stat_map = json.load(f)
    
    def handle_shop(self, event):
        """显示商店"""
        reply = "欢迎光临宠物商店！\n--------------------\n"
        for name, item in self.shop_items.items():
            reply += f"【{name}】 ${item['price']}\n效果: {item['description']}\n"
        reply += "--------------------\n使用 `/购买 [物品名] [数量]` 来购买。"
        return [event.plain_result(reply)]
    
    def handle_backpack(self, event):
        """显示背包"""
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        
        if not self.db.get_pet(user_id, group_id):
            return [event.plain_result("你还没有宠物，自然也没有背包啦。")]
        
        items = self.db.get_inventory(user_id, group_id)
        
        if not items:
            return [event.plain_result("你的背包空空如也，去商店看看吧！")]
        
        reply = f"{event.get_sender_name()}的背包:\n--------------------\n"
        for item_name, quantity in items:
            reply += f"【{item_name}】 x {quantity}\n"
        return [event.plain_result(reply)]
    
    def handle_buy(self, event, item_name: str, quantity: int = 1):
        """处理购买"""
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        
        if item_name not in self.shop_items:
            return [event.plain_result(f"商店里没有「{item_name}」这种东西。")]
        
        if not self.db.get_pet(user_id, group_id):
            return [event.plain_result("你还没有宠物，无法购买物品。")]
        
        item_info = self.shop_items[item_name]
        total_cost = item_info['price'] * quantity
        
        if self.db.buy_item(user_id, group_id, item_name, quantity, total_cost):
            return [event.plain_result(f"购买成功！你花费 ${total_cost} 购买了 {quantity} 个「{item_name}」。")]
        else:
            return [event.plain_result(f"你的钱不够哦！购买 {quantity} 个「{item_name}」需要 ${total_cost}。")]
    
    def handle_feed(self, event, item_name: str):
        """处理投喂"""
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        pet = self.db.get_pet(user_id, group_id)
        
        if not pet:
            return [event.plain_result("你还没有宠物，不能进行投喂哦。")]
        
        if item_name not in self.shop_items or self.shop_items[item_name].get('type') != 'food':
            return [event.plain_result(f"「{item_name}」不是可以投喂的食物。")]
        
        item_info = self.shop_items[item_name]
        satiety_gain = item_info.get('satiety', 0)
        mood_gain = item_info.get('mood', 0)
        
        if self.db.feed_pet(user_id, group_id, item_name, satiety_gain, mood_gain):
            satiety_chinese = self.stat_map.get('satiety', '饱食度')
            mood_chinese = self.stat_map.get('mood', '心情值')
            return [event.plain_result(
                f"你给「{pet['pet_name']}」投喂了「{item_name}」，它的{satiety_chinese}增加了 {satiety_gain}，{mood_chinese}增加了 {mood_gain}！")]
        else:
            return [event.plain_result(f"你的背包里没有「{item_name}」。")]
