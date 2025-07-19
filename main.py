# main.py - 主程序入口
import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.core.message.components import At
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
from astrbot.api import logger

# --- 全局常量定义 ---
PET_TYPES = {
    "水灵灵": {
        "attribute": "水",
        "description": "由纯净之水汇聚而成的元素精灵，性格温和，防御出众。",
        "initial_stats": {"attack": 8, "defense": 12},
        "evolutions": {
            1: {"name": "水灵灵", "image": "WaterSprite_1.png", "evolve_level": 30},
            2: {"name": "源流之精", "image": "WaterSprite_2.png", "evolve_level": None}
        }
    },
    "火小犬": {
        "attribute": "火",
        "description": "体内燃烧着不灭之火的幼犬，活泼好动，攻击性强。",
        "initial_stats": {"attack": 12, "defense": 8},
        "evolutions": {
            1: {"name": "火小犬", "image": "FirePup_1.png", "evolve_level": 30},
            2: {"name": "烈焰魔犬", "image": "FirePup_2.png", "evolve_level": None}
        }
    },
    "草叶猫": {
        "attribute": "草",
        "description": "能进行光合作用的奇特猫咪，攻守均衡，喜欢打盹。",
        "initial_stats": {"attack": 10, "defense": 10},
        "evolutions": {
            1: {"name": "草叶猫", "image": "LeafyCat_1.png", "evolve_level": 30},
            2: {"name": "丛林之王", "image": "LeafyCat_2.png", "evolve_level": None}
        }
    }
}

SHOP_ITEMS = {
    "普通口粮": {"price": 10, "type": "food", "satiety": 20, "mood": 5, "description": "能快速填饱肚子的基础食物。"},
    "美味罐头": {"price": 30, "type": "food", "satiety": 50, "mood": 15, "description": "营养均衡，宠物非常爱吃。"},
    "心情饼干": {"price": 25, "type": "food", "satiety": 10, "mood": 30, "description": "能让宠物心情愉悦的神奇零食。"},
}

STAT_MAP = {
    "exp": "经验值",
    "mood": "心情值",
    "satiety": "饱食度"
}

# --- 模块初始化 ---
def init_modules():
    # 导入所有模块
    from modules.pet_db import DatabaseManager
    from modules.pet_core import CoreManager
    from modules.pet_battle import BattleManager
    from modules.pet_wild import WildManager
    from modules.pet_shop import ShopManager
    from modules.pet_image import ImageManager
    from modules.event_library import EventLibrary
    
    # 创建共享资源
    data_dir = Path("data/pet_game")
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "pets.db"
    
    db_manager = DatabaseManager(db_path)
    image_manager = ImageManager()
    event_library = EventLibrary()
    
    # 初始化功能模块
    core_manager = CoreManager(db_manager, image_manager, PET_TYPES)
    battle_manager = BattleManager(db_manager, PET_TYPES, STAT_MAP)
    shop_manager = ShopManager(db_manager, SHOP_ITEMS, STAT_MAP)
    wild_manager = WildManager(db_manager, battle_manager, event_library, PET_TYPES, STAT_MAP)
    
    return {
        "core": core_manager,
        "battle": battle_manager,
        "wild": wild_manager,
        "shop": shop_manager
    }

# --- 主插件类 ---
@register(
    "宠物对战游戏",
    "DITF16",
    "群内宠物养成对战插件，支持打野探险、PVP对决和宠物进化",
    "1.1",
    "https://github.com/DITF16/astrbot_plugin_pet"
)
class PetPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.managers = init_modules()
        logger.info("宠物对战游戏插件已加载")

    # --- 命令路由 ---
    @filter.command("领养宠物")
    async def adopt_pet(self, event: AstrMessageEvent, pet_name: str | None = None):
        """领养一只随机的初始宠物"""
        yield await self.managers["core"].handle_core(event, "adopt", pet_name)

    @filter.command("我的宠物")
    async def my_pet_status(self, event: AstrMessageEvent):
        """查看宠物状态"""
        yield await self.managers["core"].handle_core(event, "status")

    @filter.command("宠物进化")
    async def evolve_pet(self, event: AstrMessageEvent):
        """宠物进化"""
        yield await self.managers["core"].handle_core(event, "evolve")

    @filter.command("打野")
    async def wild_adventure(self, event: AstrMessageEvent):
        """野外探险"""
        yield await self.managers["wild"].handle_wild(event)

    @filter.command("对决")
    async def duel_pet(self, event: AiocqhttpMessageEvent):
        """与其他玩家对决"""
        yield await self.managers["battle"].handle_battle(event, "pvp")

    @filter.command("宠物商店")
    async def shop(self, event: AstrMessageEvent):
        """宠物商店"""
        yield await self.managers["shop"].handle_shop(event, "show")

    @filter.command("宠物背包")
    async def backpack(self, event: AstrMessageEvent):
        """宠物背包"""
        yield await self.managers["shop"].handle_shop(event, "backpack")

    @filter.command("购买")
    async def buy_item(self, event: AstrMessageEvent, item_name: str, quantity: int = 1):
        """购买物品"""
        yield await self.managers["shop"].handle_shop(event, "buy", item_name, quantity)

    @filter.command("投喂")
    async def feed_pet_item(self, event: AstrMessageEvent, item_name: str):
        """投喂宠物"""
        yield await self.managers["shop"].handle_shop(event, "feed", item_name)

    @filter.command("宠物菜单")
    async def pet_menu(self, event: AstrMessageEvent):
        """帮助菜单"""
        menu = (
            "🐾 宠物游戏命令菜单 🐾\n"
            "-------------------\n"
            "/领养宠物 - 领养新宠物\n"
            "/我的宠物 - 查看宠物状态\n"
            "/宠物进化 - 进化宠物\n"
            "/打野 - 野外探险\n"
            "/对决 @玩家 - 发起挑战\n"
            "/宠物商店 - 查看商店\n"
            "/购买 [物品] [数量] - 购买物品\n"
            "/宠物背包 - 查看背包\n"
            "/投喂 [物品] - 喂养宠物"
        )
        yield event.plain_result(menu)

    @staticmethod
    def get_at(event: AiocqhttpMessageEvent) -> str | None:
        return next(
            (
                str(seg.qq)
                for seg in event.get_messages()
                if isinstance(seg, At) and str(seg.qq) != event.get_self_id()
            ),
            None,
        )

    async def terminate(self):
        """插件卸载/停用时调用"""
        logger.info("宠物对战游戏插件已卸载")
