import re
import json

def get_attribute_multiplier(attacker_attr: str, defender_attr: str) -> float:
    """属性克制计算"""
    effectiveness = {
        "水": "火",
        "火": "草",
        "草": "水"
    }
    if effectiveness.get(attacker_attr) == defender_attr:
        return 1.5
    if effectiveness.get(defender_attr) == attacker_attr:
        return 0.5
    return 1.0

def extract_json_from_text(text: str) -> str | None:
    """从文本中提取JSON"""
    # 尝试提取JSON代码块
    match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    
    # 尝试提取JSON对象
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
        return None
    except Exception:
        return None
