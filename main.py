import sqlite3
import random
import io
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.core.message.components import At
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
from astrbot.core.star import StarTools
from astrbot.api import logger

# --- 静态游戏数据定义 ---
# 定义了所有可用的宠物类型及其基础属性、进化路径和图片资源
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
# --- 新增：静态游戏数据定义 (商店) ---
SHOP_ITEMS = {
    "普通口粮": {"price": 10, "type": "food", "satiety": 20, "mood": 5, "description": "能快速填饱肚子的基础食物。"},
    "美味罐头": {"price": 30, "type": "food", "satiety": 50, "mood": 15, "description": "营养均衡，宠物非常爱吃。"},
    "心情饼干": {"price": 25, "type": "food", "satiety": 10, "mood": 30, "description": "能让宠物心情愉悦的神奇零食。"},
}
# --- 新增：静态游戏数据定义 (状态中文名映射) ---
STAT_MAP = {
    "exp": "经验值",
    "mood": "心情值",
    "satiety": "饱食度"
}

@register(
    "简易群宠物游戏",
    "DITF16",
    "一个简单的的群内宠物养成插件，支持LLM随机事件、PVP对决和图片状态卡。",
    "1.1",
    "https://github.com/DITF16/astrbot_plugin_pet"
)
class PetPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # --- 初始化路径和数据库 ---
        self.data_dir = StarTools.get_data_dir("astrbot_plugin_pet")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        # 创建一个用于存放临时状态图的缓存目录
        self.cache_dir = self.data_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # 假设 assets 文件夹与插件目录同级
        self.assets_dir = Path(__file__).parent / "assets"
        self.db_path = self.data_dir / "pets.db"

        self._init_database()
        logger.info("群宠物对决版插件已加载。")

    # --- 数据库初始化与辅助函数 ---
    def _init_database(self):
        """初始化数据库，创建宠物表。"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 数据库中依旧使用 INTEGER 存储ID，效率更高
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pets (
                    user_id INTEGER NOT NULL,
                    group_id INTEGER NOT NULL,
                    pet_name TEXT NOT NULL,
                    pet_type TEXT NOT NULL,
                    level INTEGER DEFAULT 1,
                    exp INTEGER DEFAULT 0,
                    mood INTEGER DEFAULT 100,
                    satiety INTEGER DEFAULT 80,
                    attack INTEGER DEFAULT 10,
                    defense INTEGER DEFAULT 10,
                    evolution_stage INTEGER DEFAULT 1,
                    last_fed_time TEXT,
                    last_walk_time TEXT,
                    last_duel_time TEXT,
                    PRIMARY KEY (user_id, group_id)
                )
            """)
            # 修改 pets 表，如果不存在则添加 money 和 last_updated_time 字段
            try:
                cursor.execute("ALTER TABLE pets ADD COLUMN money INTEGER DEFAULT 50")
            except sqlite3.OperationalError:
                pass  # 如果字段已存在，会报错，忽略即可
            try:
                cursor.execute("ALTER TABLE pets ADD COLUMN last_updated_time TEXT")
            except sqlite3.OperationalError:
                pass

            # 创建背包表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    user_id INTEGER NOT NULL,
                    group_id INTEGER NOT NULL,
                    item_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    PRIMARY KEY (user_id, group_id, item_name)
                )
            """)
            conn.commit()

    def _get_pet(self, user_id: str, group_id: str) -> dict | None:
        """
        [修改] 根据ID获取宠物信息，并自动处理离线期间的状态衰减。
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 先从数据库获取原始数据
            cursor.execute("SELECT * FROM pets WHERE user_id = ? AND group_id = ?", (int(user_id), int(group_id)))
            row = cursor.fetchone()
            if not row:
                return None

            pet_dict = dict(row)
            now = datetime.now()

            # 初始化或获取上次更新时间
            last_updated_str = pet_dict.get('last_updated_time')
            if not last_updated_str:
                last_updated_time = now
                # 首次为新字段写入当前时间
                cursor.execute("UPDATE pets SET last_updated_time = ? WHERE user_id = ? AND group_id = ?",
                               (now.isoformat(), int(user_id), int(group_id)))
            else:
                last_updated_time = datetime.fromisoformat(last_updated_str)

            # 计算离线时间并应用衰减
            hours_passed = (now - last_updated_time).total_seconds() / 3600
            if hours_passed >= 1:
                hours_to_decay = int(hours_passed)
                satiety_decay = 3 * hours_to_decay  # 每小时降低3点饱食度
                mood_decay = 2 * hours_to_decay  # 每小时降低2点心情

                # 计算新值，确保不低于0
                new_satiety = max(0, pet_dict['satiety'] - satiety_decay)
                new_mood = max(0, pet_dict['mood'] - mood_decay)

                # 更新数据库
                cursor.execute(
                    "UPDATE pets SET satiety = ?, mood = ?, last_updated_time = ? WHERE user_id = ? AND group_id = ?",
                    (new_satiety, new_mood, now.isoformat(), int(user_id), int(group_id))
                )
                logger.info(
                    f"宠物 {pet_dict['pet_name']} 离线{hours_to_decay}小时，饱食度降低{satiety_decay}, 心情降低{mood_decay}")

                # 更新返回给程序的字典
                pet_dict['satiety'] = new_satiety
                pet_dict['mood'] = new_mood

            conn.commit()

            # 补全其他可能为空的时间戳
            pet_dict.setdefault('last_fed_time', now.isoformat())
            pet_dict.setdefault('last_walk_time', now.isoformat())
            pet_dict.setdefault('last_duel_time', now.isoformat())

            return pet_dict

    def _exp_for_next_level(self, level: int) -> int:
        """计算升到下一级所需的总经验。"""
        return int(10 * (level ** 1.5))

    def _check_level_up(self, user_id: str, group_id: str) -> list[str]:
        """
        检查并处理宠物升级，此函数现在返回一个包含升级消息的列表，而不是直接发送。
        接收str类型的ID。
        """
        level_up_messages = []
        while True:
            pet = self._get_pet(user_id, group_id)
            if not pet:
                break

            exp_needed = self._exp_for_next_level(pet['level'])
            if pet['exp'] >= exp_needed:
                new_level = pet['level'] + 1
                remaining_exp = pet['exp'] - exp_needed
                new_attack = pet['attack'] + random.randint(1, 2)
                new_defense = pet['defense'] + random.randint(1, 2)

                with sqlite3.connect(self.db_path) as conn:
                    # 在更新数据库时，将str转换为int
                    conn.execute(
                        "UPDATE pets SET level = ?, exp = ?, attack = ?, defense = ? WHERE user_id = ? AND group_id = ?",
                        (new_level, remaining_exp, new_attack, new_defense, int(user_id), int(group_id))
                    )
                    conn.commit()

                logger.info(f"宠物升级: {pet['pet_name']} 升到了 {new_level} 级！")
                level_up_messages.append(f"🎉 恭喜！你的宠物「{pet['pet_name']}」升级到了 Lv.{new_level}！")
            else:
                break
        return level_up_messages

    # --- 图片生成 ---
    def _generate_pet_status_image(self, pet_data: dict, sender_name: str) -> Path | str:
        """
        [修正] 根据宠物数据生成一张状态图并保存为文件。
        成功则返回文件路径(Path)，失败则返回错误信息字符串(str)。
        """
        try:
            W, H = 800, 600
            bg_path = self.assets_dir / "background.png"
            font_path = self.assets_dir / "font.ttf"

            img = Image.open(bg_path).resize((W, H))
            draw = ImageDraw.Draw(img)

            font_title = ImageFont.truetype(str(font_path), 40)
            font_text = ImageFont.truetype(str(font_path), 28)

            pet_type_info = PET_TYPES[pet_data['pet_type']]
            evo_info = pet_type_info['evolutions'][pet_data['evolution_stage']]
            pet_img_path = self.assets_dir / evo_info['image']
            pet_img = Image.open(pet_img_path).convert("RGBA").resize((300, 300))
            img.paste(pet_img, (50, 150), pet_img)

            draw.text((W / 2, 50), f"{pet_data['pet_name']}的状态", font=font_title, fill="white", anchor="mt")
            draw.text((400, 150), f"主人: {sender_name}", font=font_text, fill="white")
            draw.text((400, 200), f"种族: {evo_info['name']} ({pet_data['pet_type']})", font=font_text, fill="white")
            draw.text((400, 250), f"等级: Lv.{pet_data['level']}", font=font_text, fill="white")

            exp_needed = self._exp_for_next_level(pet_data['level'])
            exp_ratio = min(1.0, pet_data['exp'] / exp_needed)
            draw.text((400, 300), f"经验: {pet_data['exp']} / {exp_needed}", font=font_text, fill="white")
            draw.rectangle([400, 340, 750, 360], outline="white", fill="gray")
            draw.rectangle([400, 340, 400 + 350 * exp_ratio, 360], fill="#66ccff")

            draw.text((400, 390), f"攻击: {pet_data['attack']}", font=font_text, fill="white")
            draw.text((600, 390), f"防御: {pet_data['defense']}", font=font_text, fill="white")
            draw.text((400, 440), f"心情: {pet_data['mood']}/100", font=font_text, fill="white")
            draw.text((600, 440), f"饱食度: {pet_data['satiety']}/100", font=font_text, fill="white")

            # [新增] 显示金钱
            draw.text((400, 490), f"金钱: ${pet_data.get('money', 0)}", font=font_text, fill="#FFD700")

            # [修正] 将图片保存到缓存文件夹，而不是内存
            output_path = self.cache_dir / f"status_{pet_data['group_id']}_{pet_data['user_id']}.png"
            img.save(output_path, format='PNG')
            return output_path

        except FileNotFoundError as e:
            logger.error(f"生成状态图失败，缺少素材文件: {e}")
            return f"生成状态图失败，请检查插件素材文件是否完整：\n{e}"
        except Exception as e:
            logger.error(f"生成状态图时发生未知错误: {e}")
            return f"生成状态图时发生未知错误: {e}"

    # --- 属性克制计算 ---
    def _get_attribute_multiplier(self, attacker_attr: str, defender_attr: str) -> float:
        """根据攻击方和防御方的属性，计算伤害倍率。"""
        effectiveness = {
            "水": "火",  # 水克火
            "火": "草",  # 火克草
            "草": "水"  # 草克水
        }
        if effectiveness.get(attacker_attr) == defender_attr:
            return 1.2  # 克制，伤害加成20%
        if effectiveness.get(defender_attr) == attacker_attr:
            return 0.8  # 被克制，伤害减少20%
        return 1.0  # 无克制关系

    # --- 核心逻辑：对战系统 ---
    def _run_battle(self, pet1: dict, pet2: dict) -> tuple[list[str], str]:
        """执行两个宠物之间的对战，集成属性克制逻辑。"""
        log = []
        p1_hp = pet1['level'] * 10 + pet1['satiety']
        p2_hp = pet2['level'] * 10 + pet2['satiety']
        p1_name = pet1['pet_name']
        p2_name = pet2['pet_name']

        # 获取双方属性
        p1_attr = PET_TYPES[pet1['pet_type']]['attribute']
        p2_attr = PET_TYPES[pet2['pet_type']]['attribute']

        log.append(
            f"战斗开始！\n「{p1_name}」(Lv.{pet1['level']} {p1_attr}系) vs 「{p2_name}」(Lv.{pet2['level']} {p2_attr}系)")

        turn = 0
        while p1_hp > 0 and p2_hp > 0:
            turn += 1
            log.append(f"\n--- 第 {turn} 回合 ---")

            # 宠物1攻击
            multiplier1 = self._get_attribute_multiplier(p1_attr, p2_attr)
            base_dmg_to_p2 = max(1, int(pet1['attack'] * random.uniform(0.8, 1.2) - pet2['defense'] * 0.5))
            final_dmg_to_p2 = int(base_dmg_to_p2 * multiplier1)
            p2_hp -= final_dmg_to_p2

            log.append(f"「{p1_name}」发起了攻击！")
            if multiplier1 > 1.0:
                log.append("效果拔群！")
            elif multiplier1 < 1.0:
                log.append("效果不太理想…")
            log.append(f"对「{p2_name}」造成了 {final_dmg_to_p2} 点伤害！(剩余HP: {max(0, p2_hp)})")

            if p2_hp <= 0:
                break

            # 宠物2攻击
            multiplier2 = self._get_attribute_multiplier(p2_attr, p1_attr)
            base_dmg_to_p1 = max(1, int(pet2['attack'] * random.uniform(0.8, 1.2) - pet1['defense'] * 0.5))
            final_dmg_to_p1 = int(base_dmg_to_p1 * multiplier2)
            p1_hp -= final_dmg_to_p1

            log.append(f"「{p2_name}」进行了反击！")
            if multiplier2 > 1.0:
                log.append("效果拔群！")
            elif multiplier2 < 1.0:
                log.append("效果不太理想…")
            log.append(f"对「{p1_name}」造成了 {final_dmg_to_p1} 点伤害！(剩余HP: {max(0, p1_hp)})")

        winner_name = p1_name if p1_hp > 0 else p2_name
        log.append(f"\n战斗结束！胜利者是「{winner_name}」！")
        return log, winner_name

    def _extract_json_from_text(self, text: str) -> str | None:
        """
        从包含额外文本的字符串中稳健地提取出第一个完整的JSON对象字符串。
        优先匹配 ```json ... ``` 代码块。
        """
        # 优先策略：寻找markdown json代码块
        match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
        if match:
            return match.group(1).strip()

        # 后备策略：寻找第一个 '{' 并进行括号匹配
        try:
            start_index = text.find('{')
            if start_index == -1:
                return None

            brace_level = 0
            for i, char in enumerate(text[start_index:]):
                if char == '{':
                    brace_level += 1
                elif char == '}':
                    brace_level -= 1

                if brace_level == 0:
                    return text[start_index: start_index + i + 1]
            return None  # 括号不匹配
        except Exception:
            return None

    @filter.command("领养宠物")
    async def adopt_pet(self, event: AstrMessageEvent, pet_name: str | None = None):
        """领养一只随机的初始宠物"""
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        if not group_id:
            yield event.plain_result("该功能仅限群聊使用哦。")
            return

        if self._get_pet(user_id, group_id):
            yield event.plain_result("你在这个群里已经有一只宠物啦！发送 /我的宠物 查看。")
            return

        initial_pet_types = ["水灵灵", "火小犬", "草叶猫"]
        type_name = random.choice(initial_pet_types)

        if not pet_name:
            pet_name = type_name

        pet_info = PET_TYPES[type_name]
        stats = pet_info['initial_stats']
        now = datetime.now()
        cooldown_expired_time_iso = (now - timedelta(hours=2)).isoformat()
        now_iso = now.isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO pets (user_id, group_id, pet_name, pet_type, attack, defense, 
                                     last_fed_time, last_walk_time, last_duel_time) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (int(user_id), int(group_id), pet_name, type_name, stats['attack'], stats['defense'],
                 now_iso, cooldown_expired_time_iso, cooldown_expired_time_iso))
            conn.commit()

        logger.info(f"新宠物领养: 群 {group_id} 用户 {user_id} 随机领养了 {type_name} - {pet_name}")
        yield event.plain_result(
            f"恭喜你，{event.get_sender_name()}！命运让你邂逅了「{pet_name}」({type_name})！\n发送 /我的宠物 查看它的状态吧。")

    @filter.command("我的宠物")
    async def my_pet_status(self, event: AstrMessageEvent):
        user_id, group_id = event.get_sender_id(), event.get_group_id()

        if not group_id:
            yield event.plain_result("该功能仅限群聊使用哦。")
            return

        pet = self._get_pet(user_id, group_id)
        if not pet:
            yield event.plain_result("你还没有宠物哦，快发送 /领养宠物 来选择一只吧！")
            return

        result = self._generate_pet_status_image(pet, event.get_sender_name())
        if isinstance(result, Path):
            yield event.image_result(str(result))
        else:
            yield event.plain_result(result)

    @filter.command("散步")
    async def walk_pet(self, event: AstrMessageEvent):
        """带宠物散步，触发LLM生成的奇遇或PVE战斗"""
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        if not group_id:
            return

        pet = self._get_pet(user_id, group_id)
        if not pet:
            yield event.plain_result("你还没有宠物，不能去散步哦。")
            return

        now = datetime.now()
        last_walk = datetime.fromisoformat(pet['last_walk_time'])
        if now - last_walk < timedelta(minutes=5):
            yield event.plain_result(f"刚散步回来，让「{pet['pet_name']}」休息一下吧。")
            return

        final_reply = []
        if random.random() < 0.7:
            prompt = (
                f"你是一个宠物游戏的世界事件生成器。请为一只名为'{pet['pet_name']}'的宠物在散步时，"
                "生成一个简短、有趣的随机奇遇故事（50字以内）。"
                "然后，将奖励信息封装成一个JSON对象，并使用markdown的json代码块返回。JSON应包含四个字段："
                "\"description\" (string, 故事描述), "
                "\"reward_type\" (string, 从 'exp', 'mood', 'satiety' 中随机选择), "
                "\"reward_value\" (integer, 奖励数值), "
                "和 \"money_gain\" (integer, 获得的金钱)。\n\n"
                "示例回复格式：\n"
                "这是一个奇妙的下午。\n"
                "```json\n"
                "{\n"
                "    \"description\": \"{pet_name}在河边发现了一颗闪亮的石头，心情大好！\",\n"
                "    \"reward_type\": \"mood\",\n"
                "    \"reward_value\": 15,\n"
                "    \"money_gain\": 5\n"
                "}\n"
                "```"
            )

            completion_text = ""
            try:
                llm_response = await self.context.get_using_provider().text_chat(prompt=prompt)
                completion_text = llm_response.completion_text

                json_str = self._extract_json_from_text(completion_text)

                if not json_str:
                    logger.error(f"无法从LLM响应中提取JSON: {completion_text}")
                    raise ValueError("未能解析LLM的响应格式")

                data = json.loads(json_str)

                desc = data['description'].format(pet_name=pet['pet_name'])
                reward_type = data['reward_type']
                reward_value = int(data['reward_value'])
                money_gain = int(data.get('money_gain', 0))

                reward_type_chinese = STAT_MAP.get(reward_type, reward_type)
                final_reply.append(f"奇遇发生！\n{desc}\n你的宠物获得了 {reward_value} 点{reward_type_chinese}！")
                if money_gain > 0:
                    final_reply.append(f"意外之喜！你在路边捡到了 ${money_gain}！")

                with sqlite3.connect(self.db_path) as conn:
                    update_query = (
                        f"UPDATE pets SET "
                        f"{reward_type} = {'MIN(100, ' + reward_type + ' + ?)' if reward_type != 'exp' else (reward_type + ' + ?')}, "
                        f"money = money + ?, "
                        f"last_walk_time = ? "
                        f"WHERE user_id = ? AND group_id = ?"
                    )
                    conn.execute(update_query, (reward_value, money_gain, now.isoformat(), int(user_id), int(group_id)))
                    conn.commit()

                if reward_type == 'exp':
                    final_reply.extend(self._check_level_up(user_id, group_id))

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.error(f"LLM奇遇事件处理失败: {e}\n原始返回: {completion_text}")
                final_reply.append("你的宠物在外面迷路了，好在最后成功找回，但什么也没发生。")
        else:
            npc_level = max(1, pet['level'] + random.randint(-1, 1))
            npc_type_name = random.choice(list(PET_TYPES.keys()))
            npc_stats = PET_TYPES[npc_type_name]['initial_stats']
            npc_pet = {
                "pet_name": f"野生的{npc_type_name}",
                "pet_type": npc_type_name,
                "level": npc_level,
                "attack": npc_stats['attack'] + npc_level,
                "defense": npc_stats['defense'] + npc_level,
                "satiety": 100
            }

            battle_log, winner_name = self._run_battle(pet, npc_pet)
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

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE pets SET exp = exp + ?, money = money + ?, last_walk_time = ? WHERE user_id = ? AND group_id = ?",
                    (exp_gain, money_gain, now.isoformat(), int(user_id), int(group_id)))
                conn.commit()
            final_reply.extend(self._check_level_up(user_id, group_id))

        yield event.plain_result("\n".join(final_reply))

    @filter.command("对决")
    async def duel_pet(self, event: AiocqhttpMessageEvent):
        """与其他群友的宠物进行对决"""
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        if not group_id:
            yield event.plain_result("该功能仅限群聊使用哦。")
            return

        at_info = self.get_at(event)
        if not at_info:
            yield event.plain_result("请@一位你想对决的群友。用法: /对决 @某人")
            return

        challenger_pet = self._get_pet(user_id, group_id)
        if not challenger_pet:
            yield event.plain_result("你还没有宠物，无法发起对决。")
            return

        target_id = at_info
        if user_id == target_id:
            yield event.plain_result("不能和自己对决哦。")
            return

        target_pet = self._get_pet(target_id, group_id)
        if not target_pet:
            yield event.plain_result(f"对方还没有宠物呢。")
            return

        now = datetime.now()

        # 检查挑战者自己的CD
        last_duel_challenger = datetime.fromisoformat(challenger_pet['last_duel_time'])
        if now - last_duel_challenger < timedelta(minutes=30):
            remaining = timedelta(minutes=30) - (now - last_duel_challenger)
            yield event.plain_result(f"你的对决技能正在冷却中，还需等待 {str(remaining).split('.')[0]}。")
            return

        # 检查被挑战者的CD
        last_duel_target = datetime.fromisoformat(target_pet['last_duel_time'])
        if now - last_duel_target < timedelta(minutes=30):
            remaining = timedelta(minutes=30) - (now - last_duel_target)
            yield event.plain_result(
                f"对方的宠物正在休息，还需等待 {str(remaining).split('.')[0]} 才能接受对决。")
            return

        battle_log, winner_name = self._run_battle(challenger_pet, target_pet)

        money_gain = 20
        if winner_name == challenger_pet['pet_name']:
            winner_id, loser_id = user_id, target_id
            winner_exp = 10 + target_pet['level'] * 2
            loser_exp = 5 + challenger_pet['level']
        else:
            winner_id, loser_id = target_id, user_id
            winner_exp = 10 + challenger_pet['level'] * 2
            loser_exp = 5 + target_pet['level']

        final_reply = list(battle_log)
        final_reply.append(
            f"\n对决结算：胜利者获得了 {winner_exp} 点经验值和 ${money_gain}，参与者获得了 {loser_exp} 点经验值。")

        with sqlite3.connect(self.db_path) as conn:
            # 为双方都设置冷却时间
            conn.execute("UPDATE pets SET last_duel_time = ? WHERE user_id = ? AND group_id = ?",
                         (now.isoformat(), int(user_id), int(group_id)))
            conn.execute("UPDATE pets SET last_duel_time = ? WHERE user_id = ? AND group_id = ?",
                         (now.isoformat(), int(target_id), int(group_id)))

            # 为胜利者增加金钱
            conn.execute("UPDATE pets SET money = money + ? WHERE user_id = ? AND group_id = ?",
                         (money_gain, int(winner_id), int(group_id)))

            # 发放经验
            conn.execute("UPDATE pets SET exp = exp + ? WHERE user_id = ? AND group_id = ?",
                         (winner_exp, int(winner_id), int(group_id)))
            conn.execute("UPDATE pets SET exp = exp + ? WHERE user_id = ? AND group_id = ?",
                         (loser_exp, int(loser_id), int(group_id)))
            conn.commit()

        final_reply.extend(self._check_level_up(winner_id, group_id))
        final_reply.extend(self._check_level_up(loser_id, group_id))

        yield event.plain_result("\n".join(final_reply))

    @filter.command("宠物进化")
    async def evolve_pet(self, event: AstrMessageEvent):
        """让达到条件的宠物进化。"""
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        if not group_id:
            return

        pet = self._get_pet(user_id, group_id)
        if not pet:
            yield event.plain_result("你还没有宠物哦。")
            return

        pet_type_info = PET_TYPES[pet['pet_type']]
        current_evo_info = pet_type_info['evolutions'][pet['evolution_stage']]

        evolve_level = current_evo_info['evolve_level']
        if not evolve_level:
            yield event.plain_result(f"「{pet['pet_name']}」已是最终形态，无法再进化。")
            return

        if pet['level'] < evolve_level:
            yield event.plain_result(f"「{pet['pet_name']}」需达到 Lv.{evolve_level} 才能进化。")
            return

        next_evo_stage = pet['evolution_stage'] + 1
        next_evo_info = pet_type_info['evolutions'][next_evo_stage]
        new_attack = pet['attack'] + random.randint(8, 15)
        new_defense = pet['defense'] + random.randint(8, 15)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE pets SET evolution_stage = ?, attack = ?, defense = ? WHERE user_id = ? AND group_id = ?",
                (next_evo_stage, new_attack, new_defense, int(user_id), int(group_id)))
            conn.commit()

        logger.info(f"宠物进化成功: {pet['pet_name']} -> {next_evo_info['name']}")
        yield event.plain_result(
            f"光芒四射！你的「{pet['pet_name']}」成功进化为了「{next_evo_info['name']}」！各项属性都得到了巨幅提升！")

    @filter.command("宠物商店")
    async def shop(self, event: AstrMessageEvent):
        """显示宠物商店中可购买的物品列表。"""
        reply = "欢迎光临宠物商店！\n--------------------\n"
        for name, item in SHOP_ITEMS.items():
            reply += f"【{name}】 ${item['price']}\n效果: {item['description']}\n"
        reply += "--------------------\n使用 `/购买 [物品名] [数量]` 来购买。"
        yield event.plain_result(reply)

    @filter.command("宠物背包")
    async def backpack(self, event: AstrMessageEvent):
        """显示你的宠物背包中的物品。"""
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        if not self._get_pet(user_id, group_id):
            yield event.plain_result("你还没有宠物，自然也没有背包啦。")
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT item_name, quantity FROM inventory WHERE user_id = ? AND group_id = ?",
                           (int(user_id), int(group_id)))
            items = cursor.fetchall()

        if not items:
            yield event.plain_result("你的背包空空如也，去商店看看吧！")
            return

        reply = f"{event.get_sender_name()}的背包:\n--------------------\n"
        for item_name, quantity in items:
            reply += f"【{item_name}】 x {quantity}\n"
        yield event.plain_result(reply)

    @filter.command("购买")
    async def buy_item(self, event: AstrMessageEvent, item_name: str, quantity: int = 1):
        """[修改] 从商店购买物品，使用原子性数据库操作防止竞态条件。"""
        user_id, group_id = event.get_sender_id(), event.get_group_id()

        if item_name not in SHOP_ITEMS:
            yield event.plain_result(f"商店里没有「{item_name}」这种东西。")
            return

        if not self._get_pet(user_id, group_id):
            yield event.plain_result("你还没有宠物，无法购买物品。")
            return

        item_info = SHOP_ITEMS[item_name]
        total_cost = item_info['price'] * quantity

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE pets SET money = money - ? WHERE user_id = ? AND group_id = ? AND money >= ?",
                (total_cost, int(user_id), int(group_id), total_cost)
            )

            if cursor.rowcount == 0:
                yield event.plain_result(f"你的钱不够哦！购买 {quantity} 个「{item_name}」需要 ${total_cost}。")
                return

            cursor.execute("""
                    INSERT INTO inventory (user_id, group_id, item_name, quantity) 
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id, group_id, item_name) 
                    DO UPDATE SET quantity = quantity + excluded.quantity
                """, (int(user_id), int(group_id), item_name, quantity))

            conn.commit()

        yield event.plain_result(f"购买成功！你花费 ${total_cost} 购买了 {quantity} 个「{item_name}」。")

    @filter.command("投喂")
    async def feed_pet_item(self, event: AstrMessageEvent, item_name: str):
        """[修改] 从背包中使用食物投喂宠物，使用原子性数据库操作防止竞态条件。"""
        user_id, group_id = event.get_sender_id(), event.get_group_id()
        pet = self._get_pet(user_id, group_id)
        if not pet:
            yield event.plain_result("你还没有宠物，不能进行投喂哦。")
            return

        if item_name not in SHOP_ITEMS or SHOP_ITEMS[item_name].get('type') != 'food':
            yield event.plain_result(f"「{item_name}」不是可以投喂的食物。")
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND group_id = ? AND item_name = ? AND quantity > 0",
                (int(user_id), int(group_id), item_name)
            )

            if cursor.rowcount == 0:
                yield event.plain_result(f"你的背包里没有「{item_name}」。")
                return

            item_info = SHOP_ITEMS[item_name]
            satiety_gain = item_info.get('satiety', 0)
            mood_gain = item_info.get('mood', 0)

            cursor.execute(
                "UPDATE pets SET satiety = MIN(100, satiety + ?), mood = MIN(100, mood + ?) WHERE user_id = ? AND group_id = ?",
                (satiety_gain, mood_gain, int(user_id), int(group_id))
            )

            cursor.execute(
                "DELETE FROM inventory WHERE user_id = ? AND group_id = ? AND item_name = ? AND quantity <= 0",
                (int(user_id), int(group_id), item_name))

            conn.commit()

        satiety_chinese = STAT_MAP.get('satiety', '饱食度')
        mood_chinese = STAT_MAP.get('mood', '心情值')
        yield event.plain_result(
            f"你给「{pet['pet_name']}」投喂了「{item_name}」，它的{satiety_chinese}增加了 {satiety_gain}，{mood_chinese}增加了 {mood_gain}！")

    @filter.command("宠物菜单")
    async def pet_menu(self, event: AstrMessageEvent):
        """显示所有可用的宠物插件命令。"""

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
        return next(
            (
                str(seg.qq)
                for seg in event.get_messages()
                if isinstance(seg, At) and str(seg.qq) != event.get_self_id()
            ),
            None,  # 默认返回值（如果没有匹配项）
        )

    async def terminate(self):
        """插件卸载/停用时调用。"""
        logger.info("群宠物对决版插件已卸载。")
