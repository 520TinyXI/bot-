import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from ..constants import PET_TYPES, SHOP_ITEMS

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path="data/pets.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 宠物表
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
            # 背包表
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
    
    def create_pet(self, user_id, group_id, pet_name=None):
        initial_pets = list(PET_TYPES.keys())
        pet_type = random.choice(initial_pets)
        pet_name = pet_name or pet_type
        
        now = datetime.now().isoformat()
        cooldown_time = (now - timedelta(hours=2)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO pets (user_id, group_id, pet_name, pet_type, attack, defense, 
                                     last_fed_time, last_walk_time, last_duel_time, last_updated_time) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (int(user_id), int(group_id), pet_name, pet_type, 
                 PET_TYPES[pet_type]['initial_stats']['attack'],
                 PET_TYPES[pet_type]['initial_stats']['defense'],
                 now, cooldown_time, cooldown_time, now)
            )
            conn.commit()
        
        return f"恭喜！你领养了「{pet_name}」({pet_type})！发送 /我的宠物 查看状态"
    
    def get_pet(self, user_id, group_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pets WHERE user_id = ? AND group_id = ?", 
                          (int(user_id), int(group_id)))
            return cursor.fetchone()
    
    def update_pet(self, user_id, group_id, updates):
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values())
        values.extend([int(user_id), int(group_id)])
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"UPDATE pets SET {set_clause} WHERE user_id = ? AND group_id = ?",
                values
            )
            conn.commit()
    
    def add_item_to_inventory(self, user_id, group_id, item_name, quantity):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO inventory (user_id, group_id, item_name, quantity) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, group_id, item_name) 
                DO UPDATE SET quantity = quantity + ?
            """, (int(user_id), int(group_id), item_name, quantity, quantity))
            conn.commit()
    
    def remove_item_from_inventory(self, user_id, group_id, item_name, quantity=1):
        with sqlite3.connect(self.db_path) as conn:
            # 减少数量
            conn.execute("""
                UPDATE inventory SET quantity = quantity - ? 
                WHERE user_id = ? AND group_id = ? AND item_name = ? AND quantity >= ?
            """, (quantity, int(user_id), int(group_id), item_name, quantity))
            
            # 删除数量为0的记录
            conn.execute("""
                DELETE FROM inventory 
                WHERE user_id = ? AND group_id = ? AND item_name = ? AND quantity <= 0
            """, (int(user_id), int(group_id), item_name))
            conn.commit()
    
    def get_inventory(self, user_id, group_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT item_name, quantity FROM inventory 
                WHERE user_id = ? AND group_id = ?
            """, (int(user_id), int(group_id)))
            return cursor.fetchall()
    
    def close(self):
        """关闭数据库连接"""
        pass
