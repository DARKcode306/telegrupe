import re
import time
from typing import Tuple, Dict, Any, Optional
import logging
from telegram import Update, User, Chat, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from config import DEFAULT_PROTECTION_SETTINGS, SPAM_URL_PATTERNS

logger = logging.getLogger(__name__)

# Store user message counts for flood detection
user_message_count: Dict[str, Dict[int, int]] = {}
# Store user warnings
user_warnings: Dict[str, Dict[int, int]] = {}
# Store group settings
group_settings: Dict[int, Dict[str, Any]] = {}

async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> None:
    """
    Handle a new member joining a group.
    
    Args:
        update: The update object.
        context: The context object.
        user: The user who joined.
    """
    chat_id = update.effective_chat.id
    
    # Get group settings or use default
    settings = group_settings.get(chat_id, DEFAULT_PROTECTION_SETTINGS)
    
    # Send welcome message
    if settings.get("welcome_message"):
        welcome_message = settings["welcome_message"].replace("{username}", user.mention_html())
        await context.bot.send_message(
            chat_id=chat_id,
            text=welcome_message,
            parse_mode="HTML"
        )
    
    # Check if user is a bot and take action if needed
    if user.is_bot and settings.get("ban_bots", False):
        try:
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user.id)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Bot {user.mention_html()} was banned automatically.",
                parse_mode="HTML"
            )
        except BadRequest as e:
            logger.error(f"Error banning bot: {e}")

async def handle_left_member(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> None:
    """
    Handle a member leaving a group.
    
    Args:
        update: The update object.
        context: The context object.
        user: The user who left.
    """
    if not user:
        return
    
    chat_id = update.effective_chat.id
    
    # Get group settings or use default
    settings = group_settings.get(chat_id, DEFAULT_PROTECTION_SETTINGS)
    
    # Send goodbye message
    if settings.get("goodbye_message"):
        goodbye_message = settings["goodbye_message"].replace("{username}", user.mention_html())
        await context.bot.send_message(
            chat_id=chat_id,
            text=goodbye_message,
            parse_mode="HTML"
        )

async def delete_spam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check for spam and delete if necessary.
    
    Args:
        update: The update object.
        context: The context object.
        
    Returns:
        True if spam was detected and deleted, False otherwise.
    """
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Skip checks for admins and the owner
    from config import OWNER_ID, BAD_WORDS
    if str(user_id) == OWNER_ID:
        return False
    
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status in ['administrator', 'creator']:
            return False
    except BadRequest:
        # If we can't get chat member, proceed with checks
        pass
    
    # Get group settings or use default
    settings = group_settings.get(chat_id, DEFAULT_PROTECTION_SETTINGS)
    
    # 1. Check for forwarded messages
    if settings.get("anti_forward", True) and update.message.forward_date:
        try:
            await update.message.delete()
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ {update.effective_user.mention_html()}: غير مسموح بإعادة توجيه الرسائل في هذه المجموعة",
                parse_mode="HTML"
            )
            
            # Give a warning for forwarded message
            await warn_user_internal(
                context, chat_id, user_id, 
                update.effective_user.mention_html(),
                "إرسال رسالة محولة"
            )
            
            return True
        except BadRequest as e:
            logger.error(f"Error deleting forwarded message: {e}")
            return False
    
    # 2. Check for bad words/offensive language
    if settings.get("anti_bad_words", True) and update.message.text:
        message_text = update.message.text.lower()
        
        # تحسين التعرف على الكلمات المسيئة
        normalized_text = message_text
        
        # استبدال بعض الحروف المتشابهة التي يستخدمها الناس للتحايل
        replacements = {
            '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't', '8': 'b',
            '@': 'a', '$': 's', '+': 't', 'أ': 'ا', 'إ': 'ا', 'آ': 'ا',
            'ة': 'ه', 'ى': 'ي', '_': '', '-': '', '.': '', ',': ''
        }
        
        for old, new in replacements.items():
            normalized_text = normalized_text.replace(old, new)
        
        # تقطيع الجمل إلى كلمات للبحث عن الكلمات المسيئة
        words = normalized_text.split()
        
        # فحص كل كلمة مسيئة
        for bad_word in BAD_WORDS:
            bad_word_lower = bad_word.lower()
            
            # التحقق من وجود الكلمة كاملة
            if bad_word_lower in normalized_text:
                try:
                    await update.message.delete()
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ {update.effective_user.mention_html()}: تم حذف رسالتك لاحتوائها على كلمات غير لائقة. التكرار سيؤدي إلى الحظر.",
                        parse_mode="HTML"
                    )
                    
                    # إعطاء تحذير لاستخدام كلمات مسيئة
                    await warn_user_internal(
                        context, chat_id, user_id, 
                        update.effective_user.mention_html(),
                        "استخدام كلمات مسيئة"
                    )
                    
                    return True
                except BadRequest as e:
                    logger.error(f"Error deleting message with bad words: {e}")
                    return False
                
            # التحقق من وجود الكلمة كجزء من كلمة أخرى
            for word in words:
                # تحقق ما إذا كانت الكلمة المسيئة موجودة كجزء من الكلمة
                if len(bad_word_lower) > 3 and bad_word_lower in word:
                    try:
                        await update.message.delete()
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"⚠️ {update.effective_user.mention_html()}: تم حذف رسالتك لاحتوائها على كلمات غير لائقة. التكرار سيؤدي إلى الحظر.",
                            parse_mode="HTML"
                        )
                        
                        # إعطاء تحذير لاستخدام كلمات مسيئة
                        await warn_user_internal(
                            context, chat_id, user_id, 
                            update.effective_user.mention_html(),
                            "استخدام كلمات مسيئة"
                        )
                        
                        return True
                    except BadRequest as e:
                        logger.error(f"Error deleting message with bad words: {e}")
                        return False
    
    # 3. Check for spam links
    if settings.get("anti_link", True) and update.message.text:
        for pattern in SPAM_URL_PATTERNS:
            if pattern.lower() in update.message.text.lower():
                try:
                    await update.message.delete()
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ {update.effective_user.mention_html()}: غير مسموح بإرسال روابط في هذه المجموعة.",
                        parse_mode="HTML"
                    )
                    
                    # Give a warning for posting links
                    await warn_user_internal(
                        context, chat_id, user_id, 
                        update.effective_user.mention_html(),
                        "نشر روابط غير مصرح بها"
                    )
                    
                    return True
                except BadRequest as e:
                    logger.error(f"Error deleting spam message: {e}")
                    return False
    
    # Check for flood
    if settings.get("anti_flood", True):
        # Initialize counter for this chat if it doesn't exist
        chat_key = str(chat_id)
        if chat_key not in user_message_count:
            user_message_count[chat_key] = {}
        
        # Get current time
        current_time = int(time.time())
        
        # Clean old entries (more than 60 seconds old)
        user_message_count[chat_key] = {
            uid: timestamp for uid, timestamp in user_message_count[chat_key].items()
            if current_time - timestamp < 60
        }
        
        # Increment counter for user
        if user_id in user_message_count[chat_key]:
            user_message_count[chat_key][user_id] += 1
        else:
            user_message_count[chat_key][user_id] = 1
        
        # Check for flood (more than 10 messages in 60 seconds)
        if user_message_count[chat_key][user_id] > 10:
            try:
                # Reset counter
                user_message_count[chat_key][user_id] = 0
                
                # Warn or mute the user
                success, message = await warn_user_internal(
                    context, chat_id, user_id, 
                    update.effective_user.mention_html(),
                    "إرسال رسائل كثيرة بسرعة (flood)"
                )
                return success
            except BadRequest as e:
                logger.error(f"Error handling flood: {e}")
                return False
    
    return False

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Tuple[bool, str]:
    """
    Ban a user from a group.
    
    Args:
        update: The update object.
        context: The context object.
        
    Returns:
        A tuple of (success, message).
    """
    # Check if replying to a message
    target_user = None
    reason = "لم يتم تحديد سبب"
    
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        # Check if there's a reason in the command
        if context.args:
            reason = " ".join(context.args)
    elif context.args:
        # Try to find user by username or user_id
        if len(context.args) >= 1:
            user_id_or_username = context.args[0]
            
            # If it's a mention, extract the username
            if user_id_or_username.startswith("@"):
                username = user_id_or_username[1:]
                try:
                    chat = await context.bot.get_chat(f"@{username}")
                    target_user = chat.linked_chat_id if hasattr(chat, 'linked_chat_id') else None
                except BadRequest:
                    return False, f"لم أستطع العثور على المستخدم {user_id_or_username}"
            else:
                # Try to interpret as user_id
                try:
                    user_id = int(user_id_or_username)
                    try:
                        chat_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
                        target_user = chat_member.user
                    except BadRequest:
                        return False, f"المستخدم برقم {user_id} ليس في المجموعة"
                except ValueError:
                    return False, "الرجاء استخدام معرف المستخدم أو الرد على رسالته"
            
            # If more arguments, they form the reason
            if len(context.args) > 1:
                reason = " ".join(context.args[1:])
    
    if not target_user:
        return False, "الرجاء تحديد المستخدم للحظر (بالرد على رسالته أو ذكر اسم المستخدم)"
    
    # Don't allow banning the owner or self
    from config import OWNER_ID
    if str(target_user.id) == OWNER_ID:
        return False, "لا يمكن حظر مالك البوت"
    
    if target_user.id == context.bot.id:
        return False, "لا يمكنني حظر نفسي"
    
    # Check if user is admin
    try:
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, target_user.id)
        if chat_member.status in ['administrator', 'creator']:
            return False, "لا يمكن حظر المشرفين"
    except BadRequest:
        pass
    
    try:
        await context.bot.ban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target_user.id
        )
        return True, f"تم حظر {target_user.mention_html()} من المجموعة.\nالسبب: {reason}"
    except BadRequest as e:
        logger.error(f"Error banning user: {e}")
        return False, f"حدث خطأ أثناء محاولة حظر المستخدم: {str(e)}"

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Tuple[bool, str]:
    """
    Kick a user from a group.
    
    Args:
        update: The update object.
        context: The context object.
        
    Returns:
        A tuple of (success, message).
    """
    # Check if replying to a message
    target_user = None
    reason = "لم يتم تحديد سبب"
    
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        # Check if there's a reason in the command
        if context.args:
            reason = " ".join(context.args)
    elif context.args:
        # Follow same logic as ban_user for extracting target user
        if len(context.args) >= 1:
            user_id_or_username = context.args[0]
            
            # If it's a mention, extract the username
            if user_id_or_username.startswith("@"):
                username = user_id_or_username[1:]
                try:
                    chat = await context.bot.get_chat(f"@{username}")
                    target_user = chat.linked_chat_id if hasattr(chat, 'linked_chat_id') else None
                except BadRequest:
                    return False, f"لم أستطع العثور على المستخدم {user_id_or_username}"
            else:
                # Try to interpret as user_id
                try:
                    user_id = int(user_id_or_username)
                    try:
                        chat_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
                        target_user = chat_member.user
                    except BadRequest:
                        return False, f"المستخدم برقم {user_id} ليس في المجموعة"
                except ValueError:
                    return False, "الرجاء استخدام معرف المستخدم أو الرد على رسالته"
            
            # If more arguments, they form the reason
            if len(context.args) > 1:
                reason = " ".join(context.args[1:])
    
    if not target_user:
        return False, "الرجاء تحديد المستخدم للطرد (بالرد على رسالته أو ذكر اسم المستخدم)"
    
    # Don't allow kicking the owner or self
    from config import OWNER_ID
    if str(target_user.id) == OWNER_ID:
        return False, "لا يمكن طرد مالك البوت"
    
    if target_user.id == context.bot.id:
        return False, "لا يمكنني طرد نفسي"
    
    # Check if user is admin
    try:
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, target_user.id)
        if chat_member.status in ['administrator', 'creator']:
            return False, "لا يمكن طرد المشرفين"
    except BadRequest:
        pass
    
    try:
        # Ban and then unban to kick
        await context.bot.ban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target_user.id
        )
        await context.bot.unban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target_user.id
        )
        return True, f"تم طرد {target_user.mention_html()} من المجموعة.\nالسبب: {reason}"
    except BadRequest as e:
        logger.error(f"Error kicking user: {e}")
        return False, f"حدث خطأ أثناء محاولة طرد المستخدم: {str(e)}"

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Tuple[bool, str]:
    """
    Warn a user in a group.
    
    Args:
        update: The update object.
        context: The context object.
        
    Returns:
        A tuple of (success, message).
    """
    # Check if replying to a message
    target_user = None
    reason = "لم يتم تحديد سبب"
    
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        # Check if there's a reason in the command
        if context.args:
            reason = " ".join(context.args)
    elif context.args:
        # Follow same logic as ban_user for extracting target user
        if len(context.args) >= 1:
            user_id_or_username = context.args[0]
            
            # If it's a mention, extract the username
            if user_id_or_username.startswith("@"):
                username = user_id_or_username[1:]
                try:
                    chat = await context.bot.get_chat(f"@{username}")
                    target_user = chat.linked_chat_id if hasattr(chat, 'linked_chat_id') else None
                except BadRequest:
                    return False, f"لم أستطع العثور على المستخدم {user_id_or_username}"
            else:
                # Try to interpret as user_id
                try:
                    user_id = int(user_id_or_username)
                    try:
                        chat_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
                        target_user = chat_member.user
                    except BadRequest:
                        return False, f"المستخدم برقم {user_id} ليس في المجموعة"
                except ValueError:
                    return False, "الرجاء استخدام معرف المستخدم أو الرد على رسالته"
            
            # If more arguments, they form the reason
            if len(context.args) > 1:
                reason = " ".join(context.args[1:])
    
    if not target_user:
        return False, "الرجاء تحديد المستخدم للتحذير (بالرد على رسالته أو ذكر اسم المستخدم)"
    
    # Don't allow warning the owner or self
    from config import OWNER_ID
    if str(target_user.id) == OWNER_ID:
        return False, "لا يمكن تحذير مالك البوت"
    
    if target_user.id == context.bot.id:
        return False, "لا يمكنني تحذير نفسي"
    
    # Check if user is admin
    try:
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, target_user.id)
        if chat_member.status in ['administrator', 'creator']:
            return False, "لا يمكن تحذير المشرفين"
    except BadRequest:
        pass
    
    # Call the internal warning function
    return await warn_user_internal(
        context, 
        update.effective_chat.id,
        target_user.id,
        target_user.mention_html(),
        reason
    )

async def warn_user_internal(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user_id: int,
    user_mention: str,
    reason: str
) -> Tuple[bool, str]:
    """
    Internal function to warn a user and take action if needed.
    
    Args:
        context: The context object.
        chat_id: The chat ID.
        user_id: The user ID.
        user_mention: HTML mention of the user.
        reason: The reason for the warning.
        
    Returns:
        A tuple of (success, message).
    """
    # Get group settings or use default
    settings = group_settings.get(chat_id, DEFAULT_PROTECTION_SETTINGS)
    warn_limit = settings.get("warn_limit", 3)
    warn_action = settings.get("warn_action", "kick")
    
    # Initialize warnings dict for this chat if needed
    chat_key = str(chat_id)
    if chat_key not in user_warnings:
        user_warnings[chat_key] = {}
    
    # Increment warnings
    if user_id in user_warnings[chat_key]:
        user_warnings[chat_key][user_id] += 1
    else:
        user_warnings[chat_key][user_id] = 1
    
    current_warnings = user_warnings[chat_key][user_id]
    
    # Check if warnings exceed limit
    if current_warnings >= warn_limit:
        # Reset warnings
        user_warnings[chat_key][user_id] = 0
        
        # Take action based on warn_action
        action_message = ""
        try:
            if warn_action == "ban":
                await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
                action_message = f"تم حظر {user_mention} بعد تجاوز عدد التحذيرات المسموح ({warn_limit})."
            elif warn_action == "kick":
                await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
                await context.bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
                action_message = f"تم طرد {user_mention} بعد تجاوز عدد التحذيرات المسموح ({warn_limit})."
            else:  # mute
                from telegram import ChatPermissions
                await context.bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=user_id,
                    permissions=ChatPermissions(
                        can_send_messages=False,
                        can_send_media_messages=False,
                        can_send_other_messages=False
                    )
                )
                action_message = f"تم كتم {user_mention} بعد تجاوز عدد التحذيرات المسموح ({warn_limit})."
            
            return True, action_message
        except BadRequest as e:
            logger.error(f"Error taking action after warnings: {e}")
            return False, f"حدث خطأ أثناء محاولة تنفيذ الإجراء بعد التحذيرات: {str(e)}"
    
    # If warnings don't exceed limit yet
    return True, f"تم تحذير {user_mention} ({current_warnings}/{warn_limit}).\nالسبب: {reason}"

def get_group_settings(chat_id: int) -> Dict[str, Any]:
    """
    Get settings for a group.
    
    Args:
        chat_id: The chat ID.
        
    Returns:
        The group settings.
    """
    return group_settings.get(chat_id, DEFAULT_PROTECTION_SETTINGS)

def update_group_settings(chat_id: int, new_settings: Dict[str, Any]) -> None:
    """
    Update settings for a group.
    
    Args:
        chat_id: The chat ID.
        new_settings: The new settings to apply.
    """
    if chat_id in group_settings:
        group_settings[chat_id].update(new_settings)
    else:
        settings = DEFAULT_PROTECTION_SETTINGS.copy()
        settings.update(new_settings)
        group_settings[chat_id] = settings

async def get_protection_settings_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    """
    Get an inline keyboard with the current protection settings of a group.
    
    Args:
        chat_id: The chat ID.
        
    Returns:
        An inline keyboard markup with toggleable protection options.
    """
    settings = get_group_settings(chat_id)
    
    # Create keyboard with current settings
    keyboard = []
    
    # Status emojis
    on_emoji = "✅"
    off_emoji = "❌"
    
    # Add toggleable options
    keyboard.append([
        InlineKeyboardButton(
            f"{'🔄 رسائل محولة' if settings['anti_forward'] else '🔄 رسائل محولة'} ({on_emoji if settings['anti_forward'] else off_emoji})", 
            callback_data=f"protection_toggle:anti_forward:{chat_id}"
        )
    ])
    
    keyboard.append([
        InlineKeyboardButton(
            f"{'🔗 روابط' if settings['anti_link'] else '🔗 روابط'} ({on_emoji if settings['anti_link'] else off_emoji})", 
            callback_data=f"protection_toggle:anti_link:{chat_id}"
        )
    ])
    
    keyboard.append([
        InlineKeyboardButton(
            f"{'🤬 كلمات سيئة' if settings['anti_bad_words'] else '🤬 كلمات سيئة'} ({on_emoji if settings['anti_bad_words'] else off_emoji})", 
            callback_data=f"protection_toggle:anti_bad_words:{chat_id}"
        )
    ])
    
    keyboard.append([
        InlineKeyboardButton(
            f"{'🌊 رسائل متكررة' if settings['anti_flood'] else '🌊 رسائل متكررة'} ({on_emoji if settings['anti_flood'] else off_emoji})", 
            callback_data=f"protection_toggle:anti_flood:{chat_id}"
        )
    ])
    
    # Add warning settings
    warn_limit = settings.get("warn_limit", 3)
    warn_action = settings.get("warn_action", "kick")
    
    # Convert action to Arabic
    action_name = {"ban": "حظر", "kick": "طرد", "mute": "كتم"}[warn_action]
    
    keyboard.append([
        InlineKeyboardButton(
            f"⚠️ عدد التحذيرات: {warn_limit}",
            callback_data=f"protection_warn_limit:{chat_id}"
        )
    ])
    
    keyboard.append([
        InlineKeyboardButton(
            f"🔨 إجراء بعد التحذيرات: {action_name}",
            callback_data=f"protection_warn_action:{chat_id}"
        )
    ])
    
    # Add custom welcome/goodbye message options
    keyboard.append([
        InlineKeyboardButton(
            "👋 تعديل رسالة الترحيب",
            callback_data=f"protection_welcome:{chat_id}"
        )
    ])
    
    keyboard.append([
        InlineKeyboardButton(
            "🚶‍♂️ تعديل رسالة الوداع",
            callback_data=f"protection_goodbye:{chat_id}"
        )
    ])
    
    # Add back button
    keyboard.append([
        InlineKeyboardButton("العودة", callback_data="protection_back")
    ])
    
    return InlineKeyboardMarkup(keyboard)

async def handle_protection_setting_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """
    معالجة استجابات الأزرار المتعلقة بإعدادات الحماية
    
    Args:
        update: كائن التحديث
        context: كائن السياق
        callback_data: بيانات الاستجابة من الأزرار
    """
    query = update.callback_query
    user = update.effective_user
    
    if callback_data.startswith("protection_toggle:"):
        # تبديل إعدادات الحماية
        parts = callback_data.split(":")
        if len(parts) != 3:
            return
            
        setting_name = parts[1]
        chat_id = int(parts[2])
        
        # التحقق من صلاحيات المستخدم
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user.id)
            if chat_member.status not in ['administrator', 'creator']:
                from config import OWNER_ID
                if str(user.id) != OWNER_ID:
                    await query.answer("عذراً، هذه الميزة متاحة فقط للمشرفين.")
                    return
        except BadRequest:
            await query.answer("حدث خطأ. تأكد من أنك مشرف في المجموعة.")
            return
            
        # تحديث الإعدادات
        settings = get_group_settings(chat_id)
        settings[setting_name] = not settings.get(setting_name, True)
        update_group_settings(chat_id, settings)
        
        # تحديث لوحة الإعدادات
        keyboard = await get_protection_settings_keyboard(chat_id)
        
        await query.answer(f"تم {'تفعيل' if settings[setting_name] else 'تعطيل'} {setting_name}")
        await query.message.edit_reply_markup(reply_markup=keyboard)
        
    elif callback_data.startswith("protection_warn_limit:"):
        # تغيير حد التحذيرات
        parts = callback_data.split(":")
        if len(parts) != 2:
            return
            
        chat_id = int(parts[1])
        
        # التحقق من صلاحيات المستخدم
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user.id)
            if chat_member.status not in ['administrator', 'creator']:
                from config import OWNER_ID
                if str(user.id) != OWNER_ID:
                    await query.answer("عذراً، هذه الميزة متاحة فقط للمشرفين.")
                    return
        except BadRequest:
            await query.answer("حدث خطأ. تأكد من أنك مشرف في المجموعة.")
            return
            
        # جلب الإعدادات الحالية
        settings = get_group_settings(chat_id)
        current_limit = settings.get("warn_limit", 3)
        
        # إنشاء لوحة مفاتيح للاختيار
        keyboard = []
        for limit in [1, 2, 3, 5, 10]:
            keyboard.append([
                InlineKeyboardButton(
                    f"{limit} {'✓' if limit == current_limit else ''}",
                    callback_data=f"set_warn_limit:{chat_id}:{limit}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("العودة", callback_data=f"protection_settings:{chat_id}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            "⚠️ اختر عدد التحذيرات قبل اتخاذ الإجراء:",
            reply_markup=reply_markup
        )
        
    elif callback_data.startswith("set_warn_limit:"):
        # تعيين حد التحذيرات
        parts = callback_data.split(":")
        if len(parts) != 3:
            return
            
        chat_id = int(parts[1])
        warn_limit = int(parts[2])
        
        # تحديث الإعدادات
        settings = get_group_settings(chat_id)
        settings["warn_limit"] = warn_limit
        update_group_settings(chat_id, settings)
        
        await query.answer(f"تم تعيين حد التحذيرات إلى {warn_limit}")
        
        # العودة إلى شاشة إعدادات الحماية
        keyboard = await get_protection_settings_keyboard(chat_id)
        await query.message.edit_text(
            "⚙️ **إعدادات الحماية للمجموعة**\n\n"
            "اختر الميزات التي تريد تفعيلها أو تعطيلها:",
            reply_markup=keyboard,
            parse_mode="MARKDOWN"
        )
        
    elif callback_data.startswith("protection_warn_action:"):
        # تغيير إجراء التحذير
        parts = callback_data.split(":")
        if len(parts) != 2:
            return
            
        chat_id = int(parts[1])
        
        # التحقق من صلاحيات المستخدم
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user.id)
            if chat_member.status not in ['administrator', 'creator']:
                from config import OWNER_ID
                if str(user.id) != OWNER_ID:
                    await query.answer("عذراً، هذه الميزة متاحة فقط للمشرفين.")
                    return
        except BadRequest:
            await query.answer("حدث خطأ. تأكد من أنك مشرف في المجموعة.")
            return
            
        # جلب الإعدادات الحالية
        settings = get_group_settings(chat_id)
        current_action = settings.get("warn_action", "kick")
        
        # إنشاء لوحة مفاتيح للاختيار
        keyboard = []
        actions = [
            ("حظر", "ban"),
            ("طرد", "kick"),
            ("كتم", "mute")
        ]
        
        for action_name, action_code in actions:
            keyboard.append([
                InlineKeyboardButton(
                    f"{action_name} {'✓' if action_code == current_action else ''}",
                    callback_data=f"set_warn_action:{chat_id}:{action_code}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("العودة", callback_data=f"protection_settings:{chat_id}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            "🔨 اختر الإجراء الذي سيتم اتخاذه بعد تجاوز الحد الأقصى للتحذيرات:",
            reply_markup=reply_markup
        )
        
    elif callback_data.startswith("set_warn_action:"):
        # تعيين إجراء التحذير
        parts = callback_data.split(":")
        if len(parts) != 3:
            return
            
        chat_id = int(parts[1])
        warn_action = parts[2]
        
        # تحديث الإعدادات
        settings = get_group_settings(chat_id)
        settings["warn_action"] = warn_action
        update_group_settings(chat_id, settings)
        
        # تحويل الكود إلى اسم بالعربية للعرض
        action_name = {"ban": "حظر", "kick": "طرد", "mute": "كتم"}[warn_action]
        
        await query.answer(f"تم تعيين إجراء التحذير إلى {action_name}")
        
        # العودة إلى شاشة إعدادات الحماية
        keyboard = await get_protection_settings_keyboard(chat_id)
        await query.message.edit_text(
            "⚙️ **إعدادات الحماية للمجموعة**\n\n"
            "اختر الميزات التي تريد تفعيلها أو تعطيلها:",
            reply_markup=keyboard,
            parse_mode="MARKDOWN"
        )
        
    elif callback_data.startswith("protection_settings:"):
        # استرجاع رقم المحادثة إذا كان موجودًا في البيانات
        chat_id = update.effective_chat.id
        if ":" in callback_data:
            chat_id = int(callback_data.split(":")[1])
            
        # جلب لوحة إعدادات الحماية
        keyboard = await get_protection_settings_keyboard(chat_id)
        
        await query.message.edit_text(
            "⚙️ **إعدادات الحماية للمجموعة**\n\n"
            "اختر الميزات التي تريد تفعيلها أو تعطيلها:",
            reply_markup=keyboard,
            parse_mode="MARKDOWN"
        )
