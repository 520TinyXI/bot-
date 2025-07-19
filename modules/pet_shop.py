# modules/pet_shop.py - 商店系统
import random

class ShopManager:
    def __init__(self, db_manager, shop_items, stat_map):
        self.db = db_manager
        self.shop_items = shop_items
        self.stat_map = stat_map
        
    async def handle_shop(self, event, action, *args):
        """处理商店相关命令"""
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        
        if action == "show":
            return self._show_shop(event)
        elif action == "backpack":
            return await self._show_backpack(event, user_id, group_id)
        elif action == "buy":
            return await self._buy_item(event, user_id, group_id, args[0], args[1] if len(args) > 1 else 1)
        elif action == "feed":
            return await self._feed_pet(event, user_id, group_id, args[0])
        else:
            return event.plain_result("未知操作")
    
    def _show_shop(self, event):
        """显示商店"""
        reply = "欢迎光临宠物商店！\n--------------------\n"
        for name, item in self.shop_items.items():
            reply += f"【{name}】 ${item['price']}\n效果: {item['description']}\n"
        reply += "--------------------\n使用 `/购买 [物品名] [数量]` 来购买。"
        return event.plain_result(reply)
    
    async def _show_backpack(self, event, user_id, group_id):
        """显示背包"""
        if not self.db.get_pet(user_id, group_id):
            return event.plain_result("你还没有宠物，自然也没有背包啦。")
            
        items = self.db.get_inventory(user_id, group_id)
        if not items:
            return event.plain_result("你的背包空空如也，去商店看看吧！")
            
        reply = f"{event.get_sender_name()}的背包:\n--------------------\n"
        for item_name, quantity in items:
            reply += f"【{item_name}】 x {quantity}\n"
        return event.plain_result(reply)
    
    async def _buy_item(self, event, user_id, group_id, item_name, quantity):
        """购买物品"""
        if item_name not in self.shop_items:
            return event.plain_result(f"商店里没有「{item_name}」这种东西。")
            
        pet = self.db.get_pet(user_id, group_id)
        if not pet:
            return event.plain_result("你还没有宠物，无法购买物品。")
            
        item_info = self.shop_items[item_name]
        total_cost = item_info['price'] * quantity
        
        # 检查金钱是否足够
        if pet.get("money", 0) < total_cost:
            return event.plain_result(f"你的钱不够哦！购买 {quantity} 个「{item_name}」需要 ${total_cost}。")
            
        # 更新金钱和背包
        self.db.update_pet(user_id, group_id, {"money": pet["money"] - total_cost})
        self.db.update_inventory(user_id, group_id, item_name, quantity)
        
        return event.plain_result(f"购买成功！你花费 ${total_cost} 购买了 {quantity} 个「{item_name}」。")
    
    async def _feed_pet(self, event, user_id, group_id, item_name):
        """投喂宠物"""
        pet = self.db.get_pet(user_id, group_id)
        if not pet:
            return event.plain_result("你还没有宠物，不能进行投喂哦。")
            
        if item_name not in self.shop_items or self.shop_items[item_name].get('type') != 'food':
            return event.plain_result(f"「{item_name}」不是可以投喂的食物。")
            
        # 检查背包中是否有该物品
        inventory = dict(self.db.get_inventory(user_id, group_id))
        if item_name not in inventory or inventory[item_name] <= 0:
            return event.plain_result(f"你的背包里没有「{item_name}」。")
            
        # 更新背包
        self.db.update_inventory(user_id, group_id, item_name, -1)
        
        # 应用食物效果
        item_info = self.shop_items[item_name]
        satiety_gain = item_info.get('satiety', 0)
        mood_gain = item_info.get('mood', 0)
        
        # 更新宠物状态
        updates = {
            "satiety": min(100, pet['satiety'] + satiety_gain),
            "mood": min(100, pet['mood'] + mood_gain)
        }
        self.db.update_pet(user_id, group_id, updates)
        
        # 构建回复
        satiety_chinese = self.stat_map.get('satiety', '饱食度')
        mood_chinese = self.stat_map.get('mood', '心情值')
        return event.plain_result(
            f"你给「{pet['pet_name']}」投喂了「{item_name}」，"
            f"它的{satiety_chinese}增加了 {satiety_gain}，{mood_chinese}增加了 {mood_gain}！")
