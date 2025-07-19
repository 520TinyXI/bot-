from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.message.components import At
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent

from core.database_manager import DatabaseManager
from core.state_manager import StateManager
from core.image_generator import ImageGenerator
from systems.battle_system import BattleSystem
from systems.walk_system import WalkSystem
from systems.shop_system import ShopSystem
from systems.evolution_system import EvolutionSystem
from systems.duel_system import DuelSystem

@register(
    "简易群宠物游戏",
    "DITF16",
    "群内宠物养成插件，支持随机事件、PVP对决和图片状态卡",
    "1.1",
    "https://github.com/DITF16/astrbot_plugin_pet"
)
class PetPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 初始化核心模块
        self.db = DatabaseManager()
        self.state_mgr = StateManager(self.db)
        self.image_gen = ImageGenerator()
        
        # 初始化游戏系统
        self.battle_sys = BattleSystem(self.db, self.state_mgr)
        self.walk_sys = WalkSystem(self.db, self.state_mgr, self.battle_sys)
        self.shop_sys = ShopSystem(self.db)
        self.evo_sys = EvolutionSystem(self.db)
        self.duel_sys = DuelSystem(self.db, self.state_mgr, self.battle_sys)
        
        logger.info("群宠物游戏插件已加载")

    @filter.command("领养宠物")
    async def adopt_pet(self, event: AstrMessageEvent, pet_name: str | None = None):
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        if not group_id:
            yield event.plain_result("该功能仅限群聊使用")
            return
        
        result = self.db.create_pet(user_id, group_id, pet_name)
        yield event.plain_result(result)

    @filter.command("我的宠物")
    async def my_pet_status(self, event: AstrMessageEvent):
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        pet = self.state_mgr.get_pet_with_decay(user_id, group_id)
        
        if not pet:
            yield event.plain_result("你还没有宠物，发送 /领养宠物 开始")
            return
        
        # 安全获取发送者名称
        sender_name = event.get_sender_name() or "主人"
        
        result = self.image_gen.generate_pet_status_image(pet, sender_name)
        if isinstance(result, str):
            yield event.plain_result(result)
        else:
            yield event.image_result(str(result))

    @filter.command("散步")
    async def walk_pet(self, event: AstrMessageEvent):
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        result = await self.walk_sys.handle_walk(user_id, group_id)
        yield event.plain_result("\n".join(result))

    @filter.command("对决")
    async def duel_pet(self, event: AiocqhttpMessageEvent):
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        result = await self.duel_sys.handle_duel(event, user_id, group_id)
        yield event.plain_result("\n".join(result))

    @filter.command("宠物进化")
    async def evolve_pet(self, event: AstrMessageEvent):
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        result = self.evo_sys.handle_evolution(user_id, group_id)
        yield event.plain_result(result)

    @filter.command("宠物商店")
    async def shop(self, event: AstrMessageEvent):
        result = self.shop_sys.display_shop()
        yield event.plain_result(result)

    @filter.command("宠物背包")
    async def backpack(self, event: AstrMessageEvent):
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        result = self.shop_sys.display_backpack(user_id, group_id)
        yield event.plain_result(result)

    @filter.command("购买")
    async def buy_item(self, event: AstrMessageEvent, item_name: str, quantity: int = 1):
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        result = self.shop_sys.handle_purchase(user_id, group_id, item_name, quantity)
        yield event.plain_result(result)

    @filter.command("投喂")
    async def feed_pet_item(self, event: AstrMessageEvent, item_name: str):
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        result = self.shop_sys.handle_feeding(user_id, group_id, item_name)
        yield event.plain_result(result)

    @filter.command("宠物菜单")
    async def pet_menu(self, event: AstrMessageEvent):
        menu_text = """--- 🐾 宠物插件帮助菜单 🐾 ---

    【核心功能】
    /领养宠物 [宠物名字]
    功能：随机领养一只初始宠物并为它命名。
    用法示例：/领养宠物 豆豆

    /我的宠物
    功能：以图片形式查看你当前宠物的详细状态。

    /宠物进化
    功能：当宠物达到指定等级时，让它进化成更强的形态。

    /宠物背包
    功能：查看你拥有的所有物品和对应的数量。

    【冒险与对战】
    /散步
    功能：带宠物外出散步，可能会触发奇遇、获得奖励或遭遇野生宠物。

    /对决 @某人
    功能：与群内其他玩家的宠物进行一场1v1对决，有1小时冷却时间。

    【商店与喂养】
    /宠物商店
    功能：查看所有可以购买的商品及其价格和效果。

    /购买 [物品名] [数量]
    功能：从商店购买指定数量的物品，数量为可选参数，默认为1。

    /投喂 [物品名]
    功能：从背包中使用食物来喂养你的宠物，恢复其状态。
    """
        yield event.plain_result(menu_text)

    @staticmethod
    def get_at(event: AiocqhttpMessageEvent) -> str | None:
        """安全获取被@的用户ID"""
        # 确保消息存在
        if not hasattr(event, 'get_messages') or not callable(event.get_messages):
            return None
        
        # 查找@消息
        for seg in event.get_messages():
            if isinstance(seg, At) and str(seg.qq) != event.get_self_id():
                return str(seg.qq)
        return None

    async def terminate(self):
        self.db.close()
        logger.info("宠物游戏插件已卸载")
