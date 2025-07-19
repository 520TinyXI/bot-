async def generate_random_event(pet_name: str) -> dict | None:
    """使用LLM生成随机奇遇事件"""
    prompt = (
        f"你是一个宠物游戏的世界事件生成器。请为一只名为'{pet_name}'的宠物在散步时，"
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
    
    try:
        # 假设有获取LLM提供者的方法
        llm_response = await self.context.get_using_provider().text_chat(prompt=prompt)
        return {
            'completion_text': llm_response.completion_text,
            'success': True
        }
    except Exception as e:
        logging.error(f"LLM请求失败: {e}")
        return None
