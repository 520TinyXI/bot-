from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

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
        
        result = self.image_gen.generate_pet_status_image(pet, event.get_sender_name())
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
    async def duel_pet(self, event: AstrMessageEvent):
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
        menu = (
            "🐾 宠物游戏菜单 🐾\n"
            "/领养宠物 - 领养新宠物\n"
            "/我的宠物 - 查看宠物状态\n"
            "/散步 - 带宠物外出\n"
            "/对决 @某人 - 挑战其他玩家\n"
            "/宠物进化 - 进化宠物\n"
            "/宠物商店 - 查看商店\n"
            "/宠物背包 - 查看背包\n"
            "/购买 [物品] [数量] - 购买物品\n"
            "/投喂 [物品] - 喂养宠物"
        )
        yield event.plain_result(menu)

    async def terminate(self):
        self.db.close()
        logger.info("宠物游戏插件已卸载")
