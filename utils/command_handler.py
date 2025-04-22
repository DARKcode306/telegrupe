import os
from typing import List, Dict, Any, Tuple

def get_commands_text() -> str:
    """
    Get the text describing all available commands.
    
    Returns:
        The commands text as a formatted string.
    """
    text = """<b>اوامر التشغيل ⚡:</b>
» <code>شغل</code> او <code>تشغيل</code> - لتشغيل الموسيقى  
» <code>فيد</code> او <code>فيديو</code>  - لتشغيل مقطع فيديو 
» <code>تشغيل عشوائي</code>  - لتشغيل اغنيه عشوائية 
» <code>بحث</code> - للبحث عن نتائج في اليوتيوب
» <code>تحميل</code> + اسم الفيديو - لتحميل مقطع فيديو
» <code>تنزيل</code> + اسم الاغنيه - لتحميل ملف صوتي
» <code>قران</code> - جلب قائمة بالقرآن الكريم
» <code>اغاني</code> - جلب قائمة الاغاني والفنانين 
» <code>تفعيل الاذان</code> - تفعيل تنبيهات الصلاة في المحادثه 
» <code>بنج</code> - عرض سرعة الاستجابة
» <code>سورس</code> - لعرض معلومات البوت

<b>🛡️ أوامر الحماية:</b>
» <code>/ban</code> [المستخدم] [السبب] - حظر مستخدم من المجموعة
» <code>/kick</code> [المستخدم] [السبب] - طرد مستخدم من المجموعة
» <code>/warn</code> [المستخدم] [السبب] - تحذير مستخدم في المجموعة
» <code>/settings</code> - عرض وتغيير إعدادات المجموعة

<b>⚡️  Developer by DARKCODE</b>"""
    
    return text

def get_standard_command_list() -> List[Tuple[str, str]]:
    """
    Get a list of standard commands for the bot with descriptions.
    This is useful for setting up the commands menu in BotFather.
    
    Returns:
        A list of tuples with (command, description).
    """
    return [
        ("start", "بدء استخدام البوت"),
        ("help", "عرض رسالة المساعدة"),
        ("play", "تشغيل أغنية من يوتيوب"),
        ("video", "تشغيل فيديو من يوتيوب"),
        ("random", "تشغيل أغنية عشوائية"),
        ("search", "البحث عن أغنية على يوتيوب"),
        ("download", "تحميل فيديو من يوتيوب"),
        ("downloadaudio", "تحميل ملف صوتي من يوتيوب"),
        ("quran", "عرض قائمة القرآن الكريم"),
        ("songs", "عرض قائمة الأغاني"),
        ("adhan", "تفعيل تنبيهات الصلاة"),
        ("ping", "عرض سرعة الاستجابة"),
        ("source", "عرض معلومات البوت"),
        ("ban", "حظر مستخدم من المجموعة"),
        ("kick", "طرد مستخدم من المجموعة"),
        ("warn", "تحذير مستخدم في المجموعة"),
        ("settings", "عرض وتغيير إعدادات المجموعة"),
    ]

def get_bot_father_commands() -> str:
    """
    Get commands formatted for BotFather setup.
    
    Returns:
        A string with commands formatted for BotFather.
    """
    commands = get_standard_command_list()
    return "\n".join([f"{cmd} - {desc}" for cmd, desc in commands])
