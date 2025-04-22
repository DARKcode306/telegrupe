import os
import json

# القيم الافتراضية في حالة عدم وجود ملف الإعدادات
DEFAULT_DEVELOPER_ID = "1464626603"  # تعيين معرف المالك المطلوب
DEFAULT_DEVELOPER_USERNAME = "@Dv_Website"
DEFAULT_BOT_CHANNEL = "@DARKCODE_Channel"

# محاولة قراءة الإعدادات من الملف مباشرة دون استيراد الوحدة
def _load_settings_directly():
    try:
        settings_file = 'data/bot_settings.json'
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {
        "developer_id": DEFAULT_DEVELOPER_ID,
        "developer_username": DEFAULT_DEVELOPER_USERNAME,
        "bot_channel": DEFAULT_BOT_CHANNEL,
    }

# تحميل الإعدادات مباشرة
_settings = _load_settings_directly()

# Bot token from BotFather
BOT_TOKEN = os.environ.get("BOT_TOKEN", "2029853716:AAHuwKyxqImVjTvbLs9dUC2GgqXGV-J5SJk")

# Owner ID - this ID will be recognized as the bot owner
OWNER_ID = os.environ.get("OWNER_ID", _settings.get("developer_id", DEFAULT_DEVELOPER_ID))

# Default settings for group protection
DEFAULT_PROTECTION_SETTINGS = {
    "anti_spam": True,
    "anti_link": True,
    "anti_flood": True,
    "anti_forward": True,     # حذف الرسائل المحولة
    "anti_bad_words": True,   # حذف الكلمات المسيئة
    "welcome_message": "مرحبًا {username} في المجموعة!",
    "goodbye_message": "وداعًا {username}!",
    "warn_limit": 3,  # Number of warnings before taking action
    "warn_action": "kick",  # 'kick', 'ban', or 'mute'
}

# Bot channel and developer info
BOT_CHANNEL = os.environ.get("BOT_CHANNEL", _settings.get("bot_channel", DEFAULT_BOT_CHANNEL))
BOT_DEVELOPER = os.environ.get("BOT_DEVELOPER", _settings.get("developer_username", DEFAULT_DEVELOPER_USERNAME))
# قائمة مشرفي البوت (ستظهر لهم أيقونة لوحة التحكم)
BOT_ADMIN_IDS = [int(OWNER_ID), 1464626603]  # إضافة معرف المالك بشكل صريح

# URL patterns to detect spam links
SPAM_URL_PATTERNS = [
    "t.me/joinchat",
    "t.me/+",
    "bit.ly",
    "goo.gl",
    "http://",
    "https://",
    "www."
]

# قائمة الكلمات المسيئة بالعربية والإنجليزية
BAD_WORDS = [
    # كلمات عربية مسيئة - عامة
    "كلب", "حمار", "غبي", "احمق", "متخلف", 
    "حيوان", "خنزير", "قرد", "وسخ", "قذر",
    "ارهابي", "عبيط", "حقير", "سافل", "خسيس",
    "وغد", "نذل", "خائن", "جبان", "منافق",
    
    # كلمات عربية مسيئة - قوية
    "عرص", "خول", "منيوك", "متناك", "زبي", "زب", 
    "طيزك", "كسمك", "كس امك", "كس اختك", "ابن المتناكة",
    "ابن الكلب", "ابن الحرام", "ابن القحبة", "شرموط", "شرموطة",
    "قحبة", "زانية", "عاهرة", "داعر", "ابن الزنا", "ابن الزانية",
    "عير", "نيك", "ناك", "اناكك", "انيكك", "عيري", "امك",
    "زاني", "جلخ", "منيك", "نياك", "دعارة", "مومس", "زنا",
    "فاجر", "فاجرة", "فاسق", "فاسقة", "فحش", "فاحش", "فاحشة",
    
    # كلمات إنجليزية مسيئة
    "stupid", "idiot", "damn", "hell", "ass",
    "fool", "moron", "jerk", "dumb", "crap",
    "fuck", "shit", "bitch", "pussy", "dick", 
    "asshole", "cock", "whore", "slut", "motherfucker",
    "fucker", "bastard", "wanker", "prick"
]

# Maximum number of songs to cache
MAX_SONG_CACHE = 50

# Maximum file size for music downloads (in bytes)
MAX_DOWNLOAD_SIZE = 50 * 1024 * 1024  # 50 MB

# Supported music file formats
SUPPORTED_FORMATS = ["mp3", "ogg", "m4a"]

# Default music format for downloads
DEFAULT_MUSIC_FORMAT = "mp3"
