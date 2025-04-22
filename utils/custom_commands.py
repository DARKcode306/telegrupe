"""
وحدة إدارة الأوامر المخصصة للبوت
تتيح للمشرفين إضافة أوامر مخصصة من خلال لوحة التحكم
"""

import json
import os
import time
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# المسار إلى ملف تخزين الأوامر المخصصة
CUSTOM_COMMANDS_FILE = "data/custom_commands.json"

# التأكد من وجود المجلد
os.makedirs(os.path.dirname(CUSTOM_COMMANDS_FILE), exist_ok=True)

# قاموس لتخزين الأوامر المخصصة
# المفتاح هو اسم الأمر، والقيمة هي قاموس يحتوي على معلومات الأمر
custom_commands: Dict[str, Dict[str, Any]] = {}

def load_custom_commands() -> None:
    """
    تحميل الأوامر المخصصة من الملف
    """
    global custom_commands
    
    try:
        if os.path.exists(CUSTOM_COMMANDS_FILE):
            with open(CUSTOM_COMMANDS_FILE, "r", encoding="utf-8") as file:
                custom_commands = json.load(file)
        else:
            # إنشاء ملف فارغ إذا لم يكن موجودًا
            custom_commands = {}
            save_custom_commands()
    except Exception as e:
        logger.error(f"خطأ في تحميل الأوامر المخصصة: {e}")
        custom_commands = {}

def save_custom_commands() -> None:
    """
    حفظ الأوامر المخصصة في الملف
    """
    try:
        with open(CUSTOM_COMMANDS_FILE, "w", encoding="utf-8") as file:
            json.dump(custom_commands, file, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"خطأ في حفظ الأوامر المخصصة: {e}")

def add_custom_command(command_name: str, response_text: str, created_by: int) -> Tuple[bool, str]:
    """
    إضافة أمر مخصص جديد
    
    Args:
        command_name: اسم الأمر بدون / في البداية
        response_text: نص الرد على الأمر
        created_by: معرف المستخدم الذي أنشأ الأمر
        
    Returns:
        Tuple من (نجاح العملية، رسالة)
    """
    # تنظيف اسم الأمر
    command_name = command_name.strip().lower()
    if command_name.startswith("/"):
        command_name = command_name[1:]
    
    # التحقق من وجود الأمر مسبقًا
    if command_name in custom_commands:
        return False, f"الأمر /{command_name} موجود بالفعل"
    
    # التحقق من أن الأمر ليس من الأوامر المحجوزة
    reserved_commands = [
        "start", "help", "settings", "search", "play", "download",
        "ban", "kick", "warn", "random", "ping", "source", "adhan",
        "quran", "songs", "video", "cancel", "admin"
    ]
    
    if command_name in reserved_commands:
        return False, f"الأمر /{command_name} محجوز للاستخدام النظامي"
    
    # إضافة الأمر
    custom_commands[command_name] = {
        "response": response_text,
        "created_by": created_by,
        "created_at": int(time.time()),
        "usage_count": 0
    }
    
    # حفظ التغييرات
    save_custom_commands()
    
    return True, f"تم إضافة الأمر /{command_name} بنجاح"

def remove_custom_command(command_name: str) -> Tuple[bool, str]:
    """
    حذف أمر مخصص
    
    Args:
        command_name: اسم الأمر
        
    Returns:
        Tuple من (نجاح العملية، رسالة)
    """
    # تنظيف اسم الأمر
    command_name = command_name.strip().lower()
    if command_name.startswith("/"):
        command_name = command_name[1:]
    
    # التحقق من وجود الأمر
    if command_name not in custom_commands:
        return False, f"الأمر /{command_name} غير موجود"
    
    # حذف الأمر
    del custom_commands[command_name]
    
    # حفظ التغييرات
    save_custom_commands()
    
    return True, f"تم حذف الأمر /{command_name} بنجاح"

def edit_custom_command(command_name: str, new_response: str) -> Tuple[bool, str]:
    """
    تعديل أمر مخصص
    
    Args:
        command_name: اسم الأمر
        new_response: النص الجديد للرد
        
    Returns:
        Tuple من (نجاح العملية، رسالة)
    """
    # تنظيف اسم الأمر
    command_name = command_name.strip().lower()
    if command_name.startswith("/"):
        command_name = command_name[1:]
    
    # التحقق من وجود الأمر
    if command_name not in custom_commands:
        return False, f"الأمر /{command_name} غير موجود"
    
    # تعديل الأمر
    custom_commands[command_name]["response"] = new_response
    
    # حفظ التغييرات
    save_custom_commands()
    
    return True, f"تم تعديل الأمر /{command_name} بنجاح"

def get_custom_command(command_name: str) -> Optional[Dict[str, Any]]:
    """
    الحصول على معلومات أمر مخصص
    
    Args:
        command_name: اسم الأمر
        
    Returns:
        قاموس بمعلومات الأمر، أو None إذا لم يكن موجودًا
    """
    # تنظيف اسم الأمر
    command_name = command_name.strip().lower()
    if command_name.startswith("/"):
        command_name = command_name[1:]
    
    return custom_commands.get(command_name)

def get_all_custom_commands() -> Dict[str, Dict[str, Any]]:
    """
    الحصول على جميع الأوامر المخصصة
    
    Returns:
        قاموس بجميع الأوامر المخصصة
    """
    return custom_commands

def increment_command_usage(command_name: str) -> None:
    """
    زيادة عداد استخدام الأمر
    
    Args:
        command_name: اسم الأمر
    """
    # تنظيف اسم الأمر
    command_name = command_name.strip().lower()
    if command_name.startswith("/"):
        command_name = command_name[1:]
    
    if command_name in custom_commands:
        custom_commands[command_name]["usage_count"] += 1
        # حفظ التغييرات بشكل دوري
        if custom_commands[command_name]["usage_count"] % 5 == 0:
            save_custom_commands()

# تحميل الأوامر المخصصة عند استيراد الوحدة
load_custom_commands()