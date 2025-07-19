import json
import logging
from pathlib import Path
from core import db_manager, pet_manager, config
from systems import battle_system, walk_system, shop_system, evolution_system
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
from astrbot.core.message.components import At

def setup_logging():
    """配置日志系统"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 文件日志
    file_handler = logging.FileHandler("pet_game.log")
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # 控制台日志
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(name)s - %(levelname)s - %(message)s'
    ))
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

class PetGame:
    def __init__(self, context: Context):
        setup_logging()
        self.logger = logging.getLogger("PetGame")
        
        # 初始化配置
        self.cfg = config.ConfigManager(context)
        
        # 初始化核心模块
        self.db = db_manager.DatabaseManager(self.cfg)
        self.pet_mgr = pet_manager.PetManager(self.db, self.cfg)
        
        # 初始化功能系统
        self.battle_sys = battle_system.BattleManager(self.db, self.cfg)
        self.walk_sys = walk_system.WalkManager(self.db, self.cfg, self.pet_mgr)
        self.shop_sys = shop_system.ShopManager(self.db, self.cfg)
        self.evo_sys = evolution_system.EvolutionManager(self.db, self.cfg)
        
        self.logger.info("宠物游戏系统初始化完成")
    
    # --- 命令注册 ---
    @filter.command("领养宠物")
    async def adopt_pet(self, event: AstrMessageEvent, pet_name: str | None = None):
        return await self.pet_mgr.handle_adopt(event, pet_name)
    
    @filter.command("我的宠物")
    async def my_pet_status(self, event: AstrMessageEvent):
        return await self.pet_mgr.handle_status(event)
    
    @filter.command("对决")
    async def duel_pet(self, event: AiocqhttpMessageEvent):
        target_id = self._get_at_target(event)
        if not target_id:
            return [event.plain_result("请@一位对手")]
        return await self.battle_sys.handle_battle(event, event.get_sender_id(), target_id)
    
    @filter.command("散步")
    async def walk_pet(self, event: AstrMessageEvent):
        return await self.walk_sys.handle_walk(event)
    
    @filter.command("宠物进化")
    async def evolve_pet(self, event: AstrMessageEvent):
        return await self.evo_sys.handle_evolution(event)
    
    @filter.command("宠物商店")
    async def shop(self, event: AstrMessageEvent):
        return await self.shop_sys.handle_shop(event)
    
    @filter.command("宠物背包")
    async def backpack(self, event: AstrMessageEvent):
        return await self.shop_sys.handle_backpack(event)
    
    @filter.command("购买")
    async def buy_item(self, event: AstrMessageEvent, item_name: str, quantity: int = 1):
        return await self.shop_sys.handle_buy(event, item_name, quantity)
    
    @filter.command("投喂")
    async def feed_pet_item(self, event: AstrMessageEvent, item_name: str):
        return await self.shop_sys.handle_feed(event, item_name)
    
    @filter.command("宠物菜单")
    async def pet_menu(self, event: AstrMessageEvent):
        menu_text = """--- 🐾 宠物插件帮助菜单 🐾 ---
        【核心功能】
        /领养宠物 [宠物名字] - 随机领养一只初始宠物
        /我的宠物 - 查看宠物状态
        /宠物进化 - 进化宠物
        /宠物背包 - 查看背包物品
        
        【冒险与对战】
        /散步 - 带宠物散步触发事件
        /对决 @某人 - 与其他玩家对战
        
        【商店与喂养】
        /宠物商店 - 查看可购买物品
        /购买 [物品名] [数量] - 购买物品
        /投喂 [物品名] - 喂养宠物"""
        return [event.plain_result(menu_text)]
    
    def _get_at_target(self, event: AiocqhttpMessageEvent) -> str | None:
        """获取@的目标用户ID"""
        return next(
            (str(seg.qq) for seg in event.get_messages() 
             if isinstance(seg, At) and str(seg.qq) != event.get_self_id()),
            None
        )
    
    async def terminate(self):
        """释放资源"""
        self.db.close()
        self.logger.info("宠物游戏系统已卸载")

# 插件注册
@register(
    "简易群宠物游戏",
    "DITF16",
    "一个简单的的群内宠物养成插件，支持LLM随机事件、PVP对决和图片状态卡。",
    "1.0",
    "https://github.com/DITF16/astrbot_plugin_pet"
)
class PetPlugin(PetGame):
    def __init__(self, context: Context):
        super().__init__(context)
