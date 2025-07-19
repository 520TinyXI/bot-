from PIL import Image, ImageDraw, ImageFont
import logging
from pathlib import Path
from ..constants import PET_TYPES, STAT_MAP, ASSETS_DIR

logger = logging.getLogger(__name__)

class ImageGenerator:
    def __init__(self, assets_dir=ASSETS_DIR):
        self.assets_dir = Path(assets_dir)
        self.cache_dir = self.assets_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_pet_status_image(self, pet_data, owner_name):
        # 确保owner_name不为空
        owner_name = owner_name or "主人"
        
        try:
            # 图片尺寸和资源路径
            W, H = 800, 600
            bg_path = self.assets_dir / "background.png"
            font_path = self.assets_dir / "font.ttf"
            
            # 创建画布
            img = Image.open(bg_path).resize((W, H))
            draw = ImageDraw.Draw(img)
            
            # 设置字体
            font_title = ImageFont.truetype(str(font_path), 40)
            font_text = ImageFont.truetype(str(font_path), 28)
            
            # 加载宠物图片 - 添加安全访问
            pet_type = pet_data.get('pet_type', 'unknown')
            evolution_stage = pet_data.get('evolution_stage', 0)
            
            # 安全获取宠物进化信息
            pet_type_info = PET_TYPES.get(pet_type, {})
            evolutions = pet_type_info.get('evolutions', {})
            evo_info = evolutions.get(evolution_stage, {'name': '未知形态'})
            
            # 尝试加载宠物图片，失败时使用默认图片
            pet_img = None
            if 'image' in evo_info:
                try:
                    pet_img_path = self.assets_dir / evo_info['image']
                    pet_img = Image.open(pet_img_path).convert("RGBA").resize((300, 300))
                except Exception as img_error:
                    logger.warning(f"加载宠物图片失败: {img_error}")
            
            # 如果图片加载失败，创建一个空图片占位
            if not pet_img:
                pet_img = Image.new('RGBA', (300, 300), (0, 0, 0, 0))
            
            img.paste(pet_img, (50, 150), pet_img)
            
            # 绘制文本信息
            draw.text((W // 2, 50), f"{pet_data.get('pet_name', '未知宠物')}的状态", 
                     font=font_title, fill="white", anchor="mt")
            draw.text((400, 150), f"主人: {owner_name}", font=font_text, fill="white")
            draw.text((400, 200), f"种族: {evo_info['name']} ({pet_type})", 
                     font=font_text, fill="white")
            draw.text((400, 250), f"等级: Lv.{pet_data.get('level', 1)}", 
                     font=font_text, fill="white")
            
            # 经验条
            level = pet_data.get('level', 1)
            exp_needed = self._exp_for_next_level(level)
            exp = pet_data.get('exp', 0)
            exp_ratio = min(1.0, exp / max(1, exp_needed))  # 防止除以0
            draw.text((400, 300), f"经验: {exp} / {exp_needed}", 
                     font=font_text, fill="white")
            draw.rectangle([400, 340, 750, 360], outline="white", fill="gray")
            draw.rectangle([400, 340, 400 + int(350 * exp_ratio), 360], fill="#66ccff")
            
            # 属性值
            draw.text((400, 390), f"攻击: {pet_data.get('attack', 0)}", 
                     font=font_text, fill="white")
            draw.text((600, 390), f"防御: {pet_data.get('defense', 0)}", 
                     font=font_text, fill="white")
            draw.text((400, 440), f"心情: {pet_data.get('mood', 50)}/100", 
                     font=font_text, fill="white")
            draw.text((600, 440), f"饱食度: {pet_data.get('satiety', 50)}/100", 
                     font=font_text, fill="white")
            draw.text((400, 490), f"金钱: ${pet_data.get('money', 0)}", 
                     font=font_text, fill="#FFD700")
            
            # 保存到缓存
            group_id = pet_data.get('group_id', 'unknown')
            user_id = pet_data.get('user_id', 'unknown')
            output_path = self.cache_dir / f"status_{group_id}_{user_id}.png"
            img.save(output_path, format='PNG')
            return output_path
            
        except Exception as e:
            logger.error(f"生成状态图失败: {e}", exc_info=True)
            return f"状态图生成失败: {str(e)}"
    
    def _exp_for_next_level(self, level):
        return int(10 * (max(1, level) ** 1.5))
