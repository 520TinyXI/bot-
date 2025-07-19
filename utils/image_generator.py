import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def generate_pet_status_image(pet_data: dict, pet_types: dict, sender_name: str, config) -> Path | str:
    """生成宠物状态图片"""
    try:
        W, H = 800, 600
        bg_path = config.get_asset_path("background.png")
        font_path = config.get_asset_path("fonts/font.ttf")
        
        img = Image.open(bg_path).resize((W, H))
        draw = ImageDraw.Draw(img)
        
        font_title = ImageFont.truetype(str(font_path), 40)
        font_text = ImageFont.truetype(str(font_path), 28)
        
        pet_type_info = pet_types[pet_data['pet_type']]
        evo_info = pet_type_info['evolutions'][pet_data['evolution_stage']]
        pet_img_path = config.get_asset_path(f"images/{evo_info['image']}")
        pet_img = Image.open(pet_img_path).convert("RGBA").resize((300, 300))
        img.paste(pet_img, (50, 150), pet_img)
        
        draw.text((W / 2, 50), f"{pet_data['pet_name']}的状态", font=font_title, fill="white", anchor="mt")
        draw.text((400, 150), f"主人: {sender_name}", font=font_text, fill="white")
        draw.text((400, 200), f"种族: {evo_info['name']} ({pet_data['pet_type']})", font=font_text, fill="white")
        draw.text((400, 250), f"等级: Lv.{pet_data['level']}", font=font_text, fill="white")
        
        # 经验计算
        exp_needed = 10 * (pet_data['level'] ** 1.5)
        exp_ratio = min(1.0, pet_data['exp'] / exp_needed)
        draw.text((400, 300), f"经验: {pet_data['exp']} / {int(exp_needed)}", font=font_text, fill="white")
        draw.rectangle([400, 340, 750, 360], outline="white", fill="gray")
        draw.rectangle([400, 340, 400 + 350 * exp_ratio, 360], fill="#66ccff")
        
        draw.text((400, 390), f"攻击: {pet_data['attack']}", font=font_text, fill="white")
        draw.text((600, 390), f"防御: {pet_data['defense']}", font=font_text, fill="white")
        draw.text((400, 440), f"心情: {pet_data['mood']}/100", font=font_text, fill="white")
        draw.text((600, 440), f"饱食度: {pet_data['satiety']}/100", font=font_text, fill="white")
        draw.text((400, 490), f"金钱: ${pet_data.get('money', 0)}", font=font_text, fill="#FFD700")
        
        # 保存图片
        output_path = config.cache_dir / f"status_{pet_data['group_id']}_{pet_data['user_id']}.png"
        img.save(output_path, format='PNG')
        return output_path
    
    except FileNotFoundError as e:
        logging.error(f"生成状态图失败，缺少素材文件: {e}")
        return f"生成状态图失败，请检查插件素材文件是否完整：\n{e}"
    except Exception as e:
        logging.error(f"生成状态图时发生未知错误: {e}")
        return f"生成状态图时发生未知错误: {e}"
