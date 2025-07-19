# modules/pet_image.py - 图片生成
import io
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

class ImageManager:
    def __init__(self):
        self.assets_dir = Path("assets/pet_game")
        self.cache_dir = Path("data/pet_game/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_status_image(self, pet_data: dict, sender_name: str) -> Path | None:
        """生成宠物状态图"""
        try:
            # 图片尺寸
            W, H = 800, 600
            
            # 加载背景
            bg_path = self.assets_dir / "background.png"
            img = Image.open(bg_path).resize((W, H))
            draw = ImageDraw.Draw(img)
            
            # 加载字体
            font_path = self.assets_dir / "font.ttf"
            font_title = ImageFont.truetype(str(font_path), 40)
            font_text = ImageFont.truetype(str(font_path), 28)
            
            # 加载宠物图片
            pet_type_info = PET_TYPES[pet_data['pet_type']]
            evo_info = pet_type_info['evolutions'][pet_data['evolution_stage']]
            pet_img_path = self.assets_dir / evo_info['image']
            pet_img = Image.open(pet_img_path).convert("RGBA").resize((300, 300))
            img.paste(pet_img, (50, 150), pet_img)
            
            # 绘制文本
            draw.text((W / 2, 50), f"{pet_data['pet_name']}的状态", font=font_title, fill="white", anchor="mt")
            draw.text((400, 150), f"主人: {sender_name}", font=font_text, fill="white")
            draw.text((400, 200), f"种族: {evo_info['name']} ({pet_data['pet_type']})", font=font_text, fill="white")
            draw.text((400, 250), f"等级: Lv.{pet_data['level']}", font=font_text, fill="white")
            
            # 经验条
            exp_needed = self._exp_for_next_level(pet_data['level'])
            exp_ratio = min(1.0, pet_data['exp'] / exp_needed)
            draw.text((400, 300), f"经验: {pet_data['exp']} / {exp_needed}", font=font_text, fill="white")
            draw.rectangle([400, 340, 750, 360], outline="white", fill="gray")
            draw.rectangle([400, 340, 400 + 350 * exp_ratio, 360], fill="#66ccff")
            
            # 属性
            draw.text((400, 390), f"攻击: {pet_data['attack']}", font=font_text, fill="white")
            draw.text((600, 390), f"防御: {pet_data['defense']}", font=font_text, fill="white")
            draw.text((400, 440), f"心情: {pet_data['mood']}/100", font=font_text, fill="white")
            draw.text((600, 440), f"饱食度: {pet_data['satiety']}/100", font=font_text, fill="white")
            draw.text((400, 490), f"金钱: ${pet_data.get('money', 0)}", font=font_text, fill="#FFD700")
            
            # 保存图片
            output_path = self.cache_dir / f"status_{pet_data['group_id']}_{pet_data['user_id']}.png"
            img.save(output_path, format='PNG')
            return output_path
            
        except Exception as e:
            print(f"生成状态图失败: {e}")
            return None
    
    def _exp_for_next_level(self, level: int) -> int:
        """计算升级所需经验"""
        return int(10 * (level ** 1.5))
