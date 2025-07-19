# 宠物类型定义
PET_TYPES = {
    "水灵灵": {
        "attribute": "水",
        "description": "由纯净之水汇聚而成的元素精灵",
        "initial_stats": {"attack": 8, "defense": 12},
        "evolutions": {
            1: {"name": "水灵灵", "image": "WaterSprite_1.png", "evolve_level": 30},
            2: {"name": "源流之精", "image": "WaterSprite_2.png", "evolve_level": None}
        }
    },
    "火小犬": {
        "attribute": "火",
        "description": "体内燃烧着不灭之火的幼犬",
        "initial_stats": {"attack": 12, "defense": 8},
        "evolutions": {
            1: {"name": "火小犬", "image": "FirePup_1.png", "evolve_level": 30},
            2: {"name": "烈焰魔犬", "image": "FirePup_2.png", "evolve_level": None}
        }
    },
    "草叶猫": {
        "attribute": "草",
        "description": "能进行光合作用的奇特猫咪",
        "initial_stats": {"attack": 10, "defense": 10},
        "evolutions": {
            1: {"name": "草叶猫", "image": "LeafyCat_1.png", "evolve_level": 30},
            2: {"name": "丛林之王", "image": "LeafyCat_2.png", "evolve_level": None}
        }
    }
}

# 商店物品
SHOP_ITEMS = {
    "普通口粮": {"price": 10, "type": "food", "satiety": 20, "mood": 5, "description": "基础食物"},
    "美味罐头": {"price": 30, "type": "food", "satiety": 50, "mood": 15, "description": "营养均衡"},
    "心情饼干": {"price": 25, "type": "food", "satiety": 10, "mood": 30, "description": "提升心情"},
}

# 状态映射
STAT_MAP = {
    "exp": "经验值",
    "mood": "心情值",
    "satiety": "饱食度"
}

# 图片资源目录
ASSETS_DIR = "astrbot_plugin_pet/assets"
