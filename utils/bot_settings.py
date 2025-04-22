"""
وحدة إدارة إعدادات البوت
تتيح للمشرفين تغيير الإعدادات الأساسية للبوت مثل معرف المطور ورسالة الترحيب وإعدادات الاشتراك الإجباري
"""

import json
import os
from typing import Dict, Any, Tuple, List, Optional

# مسار ملف الإعدادات
SETTINGS_FILE = 'data/bot_settings.json'

# الإعدادات الافتراضية
DEFAULT_SETTINGS = {
    "developer_id": "5643970536",  # معرف المطور
    "developer_username": "@Dv_Website",  # اسم مستخدم المطور
    "welcome_message": """🤖 أهلاً بك في بوت الموسيقى والإدارة!

الميزات:
- تشغيل وتحميل الموسيقى من يوتيوب
- إدارة المجموعات وحمايتها
- دعم ميزات القرآن الكريم والصلاة
- استجابة سريعة وتجربة سلسة

أضفني إلى مجموعتك واستمتع بالميزات المتعددة!""",  # رسالة الترحيب
    "bot_channel": "@DARKCODE_Channel",  # قناة البوت
    "force_subscription": {
        "enabled": False,  # تفعيل الاشتراك الإجباري
        "channel": "@DARKCODE_Channel",  # قناة الاشتراك الإجباري
        "message": "🔒 عليك الاشتراك في القناة أولاً لاستخدام البوت\n\nاشترك ثم اضغط 'تحقق من الاشتراك'",  # رسالة الاشتراك الإجباري
    }
}

# تحميل الإعدادات
def load_settings() -> Dict[str, Any]:
    """
    تحميل إعدادات البوت من الملف
    
    Returns:
        Dict[str, Any]: إعدادات البوت
    """
    if not os.path.exists('data'):
        os.makedirs('data')
        
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS
    
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            
            # التأكد من وجود جميع الإعدادات الافتراضية
            for key, value in DEFAULT_SETTINGS.items():
                if key not in settings:
                    settings[key] = value
                elif isinstance(value, dict) and isinstance(settings[key], dict):
                    # مراجعة الإعدادات الفرعية
                    for sub_key, sub_value in value.items():
                        if sub_key not in settings[key]:
                            settings[key][sub_key] = sub_value
                            
            return settings
    except (json.JSONDecodeError, FileNotFoundError):
        # في حالة وجود خطأ في الملف، استخدام الإعدادات الافتراضية
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS

# حفظ الإعدادات
def save_settings(settings: Dict[str, Any]) -> None:
    """
    حفظ إعدادات البوت في الملف
    
    Args:
        settings (Dict[str, Any]): الإعدادات المراد حفظها
    """
    if not os.path.exists('data'):
        os.makedirs('data')
        
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)

# الحصول على معرف المطور
def get_developer_id() -> str:
    """
    الحصول على معرف المطور
    
    Returns:
        str: معرف المطور
    """
    settings = load_settings()
    return settings.get("developer_id", DEFAULT_SETTINGS["developer_id"])

# الحصول على اسم مستخدم المطور
def get_developer_username() -> str:
    """
    الحصول على اسم مستخدم المطور
    
    Returns:
        str: اسم مستخدم المطور
    """
    settings = load_settings()
    return settings.get("developer_username", DEFAULT_SETTINGS["developer_username"])

# الحصول على رسالة الترحيب
def get_welcome_message() -> str:
    """
    الحصول على رسالة الترحيب
    
    Returns:
        str: رسالة الترحيب
    """
    settings = load_settings()
    return settings.get("welcome_message", DEFAULT_SETTINGS["welcome_message"])

# الحصول على قناة البوت
def get_bot_channel() -> str:
    """
    الحصول على قناة البوت
    
    Returns:
        str: قناة البوت
    """
    settings = load_settings()
    return settings.get("bot_channel", DEFAULT_SETTINGS["bot_channel"])

# الحصول على إعدادات الاشتراك الإجباري
def get_force_subscription_settings() -> Dict[str, Any]:
    """
    الحصول على إعدادات الاشتراك الإجباري
    
    Returns:
        Dict[str, Any]: إعدادات الاشتراك الإجباري
    """
    settings = load_settings()
    return settings.get("force_subscription", DEFAULT_SETTINGS["force_subscription"])

# تحديث معرف المطور
def update_developer_id(developer_id: str) -> Tuple[bool, str]:
    """
    تحديث معرف المطور
    
    Args:
        developer_id (str): معرف المطور الجديد
        
    Returns:
        Tuple[bool, str]: (نجاح العملية، رسالة)
    """
    try:
        settings = load_settings()
        settings["developer_id"] = developer_id
        save_settings(settings)
        return True, "تم تحديث معرف المطور بنجاح"
    except Exception as e:
        return False, f"حدث خطأ أثناء تحديث معرف المطور: {str(e)}"

# تحديث اسم مستخدم المطور
def update_developer_username(username: str) -> Tuple[bool, str]:
    """
    تحديث اسم مستخدم المطور
    
    Args:
        username (str): اسم مستخدم المطور الجديد
        
    Returns:
        Tuple[bool, str]: (نجاح العملية، رسالة)
    """
    try:
        # التأكد من أن اسم المستخدم يبدأ بـ @
        if not username.startswith('@'):
            username = f'@{username}'
            
        settings = load_settings()
        settings["developer_username"] = username
        save_settings(settings)
        return True, "تم تحديث اسم مستخدم المطور بنجاح"
    except Exception as e:
        return False, f"حدث خطأ أثناء تحديث اسم مستخدم المطور: {str(e)}"

# تحديث رسالة الترحيب
def update_welcome_message(message: str) -> Tuple[bool, str]:
    """
    تحديث رسالة الترحيب
    
    Args:
        message (str): رسالة الترحيب الجديدة
        
    Returns:
        Tuple[bool, str]: (نجاح العملية، رسالة)
    """
    try:
        settings = load_settings()
        settings["welcome_message"] = message
        save_settings(settings)
        return True, "تم تحديث رسالة الترحيب بنجاح"
    except Exception as e:
        return False, f"حدث خطأ أثناء تحديث رسالة الترحيب: {str(e)}"

# تحديث قناة البوت
def update_bot_channel(channel: str) -> Tuple[bool, str]:
    """
    تحديث قناة البوت
    
    Args:
        channel (str): قناة البوت الجديدة
        
    Returns:
        Tuple[bool, str]: (نجاح العملية، رسالة)
    """
    try:
        # التأكد من أن اسم القناة يبدأ بـ @
        if not channel.startswith('@'):
            channel = f'@{channel}'
            
        settings = load_settings()
        settings["bot_channel"] = channel
        save_settings(settings)
        return True, "تم تحديث قناة البوت بنجاح"
    except Exception as e:
        return False, f"حدث خطأ أثناء تحديث قناة البوت: {str(e)}"

# تحديث إعدادات الاشتراك الإجباري
def update_force_subscription(enabled: bool, channel: str = None, message: str = None) -> Tuple[bool, str]:
    """
    تحديث إعدادات الاشتراك الإجباري
    
    Args:
        enabled (bool): تفعيل/تعطيل الاشتراك الإجباري
        channel (str, optional): قناة الاشتراك الإجباري
        message (str, optional): رسالة الاشتراك الإجباري
        
    Returns:
        Tuple[bool, str]: (نجاح العملية، رسالة)
    """
    try:
        settings = load_settings()
        
        # تحديث الإعدادات
        settings["force_subscription"]["enabled"] = enabled
        
        if channel:
            # التأكد من أن اسم القناة يبدأ بـ @
            if not channel.startswith('@'):
                channel = f'@{channel}'
                
            settings["force_subscription"]["channel"] = channel
            
        if message:
            settings["force_subscription"]["message"] = message
            
        save_settings(settings)
        
        if enabled:
            return True, "تم تفعيل الاشتراك الإجباري بنجاح"
        else:
            return True, "تم تعطيل الاشتراك الإجباري بنجاح"
    except Exception as e:
        return False, f"حدث خطأ أثناء تحديث إعدادات الاشتراك الإجباري: {str(e)}"

# التحقق من الاشتراك في القناة
async def check_subscription(bot, user_id: int) -> bool:
    """
    التحقق من اشتراك المستخدم في القناة المطلوبة
    
    Args:
        bot: كائن البوت
        user_id (int): معرف المستخدم
        
    Returns:
        bool: هل المستخدم مشترك في القناة
    """
    settings = load_settings()
    force_sub = settings.get("force_subscription", DEFAULT_SETTINGS["force_subscription"])
    
    # إذا كان الاشتراك الإجباري غير مفعل
    if not force_sub.get("enabled", False):
        return True
        
    channel = force_sub.get("channel", "")
    
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False