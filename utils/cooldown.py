from datetime import datetime, timedelta

class CooldownManager:
    @staticmethod
    def check_cooldown(last_time_str, cooldown_seconds):
        """检查冷却时间是否结束"""
        if not last_time_str:
            return True
            
        last_time = datetime.fromisoformat(last_time_str)
        return (datetime.now() - last_time).total_seconds() >= cooldown_seconds
    
    @staticmethod
    def get_remaining_cooldown(last_time_str, cooldown_seconds):
        """获取剩余冷却时间"""
        if not last_time_str:
            return 0
            
        last_time = datetime.fromisoformat(last_time_str)
        elapsed = (datetime.now() - last_time).total_seconds()
        return max(0, cooldown_seconds - elapsed)
