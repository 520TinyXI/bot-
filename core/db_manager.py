import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from core.config import ConfigManager

class DatabaseManager:
    def __init__(self, config: ConfigManager):
        self.config = config
        self.db_path = config.get_data_path() / "pets.db"
        self.logger = logging.getLogger("DatabaseManager")
        self._init_database()
    
    def _init_database(self):
        """初始化数据库结构"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
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
                    money INTEGER DEFAULT 50,
                    last_updated_time TEXT,
                    PRIMARY KEY (user_id, group_id)
                )
            """)
            
            # 尝试添加可能缺失的字段
            try:
                cursor.execute("ALTER TABLE pets ADD COLUMN money INTEGER DEFAULT 50")
            except sqlite3.OperationalError:
                pass
            
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
    
    def get_pet(self, user_id: str, group_id: str) -> dict | None:
        """获取宠物数据并处理状态衰减"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pets WHERE user_id = ? AND group_id = ?", 
                          (int(user_id), int(group_id)))
            row = cursor.fetchone()
            if not row:
                return None
            
            pet_dict = dict(row)
            now = datetime.now()
            
            # 处理状态衰减
            last_updated_str = pet_dict.get('last_updated_time')
            if not last_updated_str:
                cursor.execute("UPDATE pets SET last_updated_time = ? WHERE user_id = ? AND group_id = ?",
                               (now.isoformat(), int(user_id), int(group_id)))
                last_updated_time = now
            else:
                last_updated_time = datetime.fromisoformat(last_updated_str)
            
            hours_passed = (now - last_updated_time).total_seconds() / 3600
            if hours_passed >= 1:
                hours_to_decay = int(hours_passed)
                satiety_decay = 3 * hours_to_decay
                mood_decay = 2 * hours_to_decay
                
                new_satiety = max(0, pet_dict['satiety'] - satiety_decay)
                new_mood = max(0, pet_dict['mood'] - mood_decay)
                
                cursor.execute(
                    "UPDATE pets SET satiety = ?, mood = ?, last_updated_time = ? WHERE user_id = ? AND group_id = ?",
                    (new_satiety, new_mood, now.isoformat(), int(user_id), int(group_id))
                )
                conn.commit()
                
                pet_dict['satiety'] = new_satiety
                pet_dict['mood'] = new_mood
            
            # 确保时间戳存在
            pet_dict.setdefault('last_fed_time', now.isoformat())
            pet_dict.setdefault('last_walk_time', now.isoformat())
            pet_dict.setdefault('last_duel_time', now.isoformat())
            
            return pet_dict
    
    def create_pet(self, user_id: str, group_id: str, pet_name: str, pet_type: str, stats: dict):
        """创建新宠物"""
        now = datetime.now().isoformat()
        cooldown_expired = (datetime.now() - timedelta(hours=2)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO pets (user_id, group_id, pet_name, pet_type, attack, defense, 
                                     last_fed_time, last_walk_time, last_duel_time) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (int(user_id), int(group_id), pet_name, pet_type, 
                 stats['attack'], stats['defense'], now, cooldown_expired, cooldown_expired))
            conn.commit()
    
    def update_pet(self, user_id: str, group_id: str, updates: dict):
        """更新宠物属性"""
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values()) + [int(user_id), int(group_id)]
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"UPDATE pets SET {set_clause} WHERE user_id = ? AND group_id = ?",
                values
            )
            conn.commit()
    
    def level_up_pet(self, user_id: str, group_id: str, new_level: int, remaining_exp: int, 
                    new_attack: int, new_defense: int):
        """处理宠物升级"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE pets SET level = ?, exp = ?, attack = ?, defense = ? WHERE user_id = ? AND group_id = ?",
                (new_level, remaining_exp, new_attack, new_defense, int(user_id), int(group_id))
            )
            conn.commit()
    
    def get_inventory(self, user_id: str, group_id: str) -> list:
        """获取背包物品"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT item_name, quantity FROM inventory WHERE user_id = ? AND group_id = ?",
                          (int(user_id), int(group_id)))
            return cursor.fetchall()
    
    def buy_item(self, user_id: str, group_id: str, item_name: str, quantity: int, total_cost: int) -> bool:
        """购买物品"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 扣款
            cursor.execute(
                "UPDATE pets SET money = money - ? WHERE user_id = ? AND group_id = ? AND money >= ?",
                (total_cost, int(user_id), int(group_id), total_cost)
            )
            
            if cursor.rowcount == 0:
                return False
            
            # 添加物品
            cursor.execute("""
                INSERT INTO inventory (user_id, group_id, item_name, quantity) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, group_id, item_name) 
                DO UPDATE SET quantity = quantity + excluded.quantity
            """, (int(user_id), int(group_id), item_name, quantity))
            
            conn.commit()
            return True
    
    def feed_pet(self, user_id: str, group_id: str, item_name: str, satiety_gain: int, mood_gain: int) -> bool:
        """投喂宠物"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 减少物品数量
            cursor.execute(
                "UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND group_id = ? AND item_name = ? AND quantity > 0",
                (int(user_id), int(group_id), item_name)
            )
            
            if cursor.rowcount == 0:
                return False
            
            # 更新宠物状态
            cursor.execute(
                "UPDATE pets SET satiety = MIN(100, satiety + ?), mood = MIN(100, mood + ?) WHERE user_id = ? AND group_id = ?",
                (satiety_gain, mood_gain, int(user_id), int(group_id))
            )
            
            # 清理空物品
            cursor.execute(
                "DELETE FROM inventory WHERE user_id = ? AND group_id = ? AND item_name = ? AND quantity <= 0",
                (int(user_id), int(group_id), item_name))
            
            conn.commit()
            return True
