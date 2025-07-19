from pathlib import Path
from astrbot.core.star import StarTools
from astrbot.api import Context

class ConfigManager:
    def __init__(self, context: Context):
        self.data_dir = StarTools.get_data_dir("astrbot_plugin_pet")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir = Path(__file__).parent.parent / "assets"
        
        # 创建缓存目录
        self.cache_dir = self.data_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_asset_path(self, filename: str) -> Path:
        return self.assets_dir / filename
    
    def get_data_path(self, subdir: str = "") -> Path:
        path = self.data_dir / subdir
        path.mkdir(parents=True, exist_ok=True)
        return path
