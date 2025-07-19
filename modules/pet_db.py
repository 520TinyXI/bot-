# modules/pet_db.py - 数据库管理
import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
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
            if last_updated_str:
                last_updated = datetime.fromisoformat(last_updated_str)
                hours_passed = (now - last_updated).total_seconds() / 3600
                if hours_passed >= 1:
                    hours_to_decay = int(hours_passed)
                    satiety_decay = 3 * hours_to_decay
                    mood_decay = 2 * hours_to_decay
                    
                    new_satiety = max(0, pet_dict['satiety'] - satiety_decay)
                    new_mood = max(0, pet_dict['mood'] - mood_decay)
                    
                    cursor.execute(
                        "UPDATE pets SET satiety = ?, mood = ?, last_updated_time = ? "
                        "WHERE user_id = ? AND group_id = ?",
                        (new_satiety, new_mood, now.isoformat(), 
                         int(user_id), int(group_id))
                    conn.commit()
                    
                    pet_dict['satiety'] = new_satiety
                    pet_dict['mood'] = new_mood
                    logger.info(f"宠物状态衰减: {pet_dict['pet_name']} 饱食度-{satiety_decay}, 心情-{mood_decay}")
            
            return pet_dict
    
    def create_pet(self, user_id: str, group_id: str, pet_name: str, pet_type: str, stats: dict):
        """创建新宠物"""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO pets (user_id, group_id, pet_name, pet_type, attack, defense, 
                                     last_fed_time, last_walk_time, last_duel_time, last_updated_time) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (int(user_id), int(group_id), pet_name, pet_type, 
                 stats['attack'], stats['defense'], now, now, now, now))
            conn.commit()
    
    def update_pet(self, user_id: str, group_id: str, updates: dict):
        """更新宠物数据"""
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values())
        values.extend([int(user_id), int(group_id)])
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"UPDATE pets SET {set_clause} WHERE user_id = ? AND group_id = ?",
                values)
            conn.commit()
    
    def update_inventory(self, user_id: str, group_id: str, item_name: str, quantity: int):
        """更新背包物品"""
        with sqlite3.connect(self.db_path) as conn:
            # 尝试更新现有物品
            conn.execute(
                "UPDATE inventory SET quantity = quantity + ? "
                "WHERE user_id = ? AND group_id = ? AND item_name = ?",
                (quantity, int(user_id), int(group_id), item_name))
            
            # 如果不存在则插入
            if conn.total_changes == 0:
                conn.execute(
                    "INSERT INTO inventory (user_id, group_id, item_name, quantity) "
                    "VALUES (?, ?, ?, ?)",
                    (int(user_id), int(group_id), item_name, quantity))
            
            # 删除数量为0的物品
            conn.execute(
                "DELETE FROM inventory WHERE quantity <= 0 "
                "AND user_id = ? AND group_id = ? AND item_name = ?",
                (int(user_id), int(group_id), item_name))
            
            conn.commit()
    
    def get_inventory(self, user_id: str, group_id: str) -> list:
        """获取用户背包物品"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT item_name, quantity FROM inventory "
                "WHERE user_id = ? AND group_id = ?",
                (int(user_id), int(group_id)))
            return cursor.fetchall()
    
    def set_cooldown(self, user_id: str, group_id: str, cooldown_type: str, time: datetime):
        """设置冷却时间"""
        column = f"last_{cooldown_type}_time"
        self.update_pet(user_id, group_id, {column: time.isoformat()})
    
    def check_cooldown(self, user_id: str, group_id: str, cooldown_type: str, cooldown: int) -> bool:
        """检查冷却时间是否结束"""
        pet = self.get_pet(user_id, group_id)
        if not pet:
            return False
            
        last_time = datetime.fromisoformat(pet[f"last_{cooldown_type}_time"])
        return (datetime.now() - last_time).total_seconds() >= cooldown
