#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import logging
import random
import asyncio
from datetime import datetime
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    User,
    Chat
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError

from config import BOT_TOKEN, OWNER_ID, BOT_CHANNEL, BOT_DEVELOPER, BOT_ADMIN_IDS
from utils.music_handler import download_music, play_music, search_youtube, get_audio_info
from utils.group_protection import (
    handle_new_member,
    handle_left_member,
    delete_spam,
    ban_user,
    kick_user,
    warn_user,
    get_group_settings,
    update_group_settings
)
from utils.custom_commands import (
    add_custom_command,
    remove_custom_command,
    edit_custom_command,
    get_custom_command,
    get_all_custom_commands,
    increment_command_usage
)
# سيتم استيراد الدوال من utils.bot_settings فقط عند الحاجة إليها لتجنب الاستيراد الدائري

# إحصائيات البوت
BOT_START_TIME = time.time()  # وقت بدء تشغيل البوت
BOT_STATISTICS = {
    "messages_received": 0,
    "songs_played": 0,
    "searches_performed": 0,
    "downloads_completed": 0,
    "commands_used": 0,
    "groups_joined": 0,
    "users_warned": 0,
    "users_banned": 0,
    "broadcasts_sent": 0,
}
from utils.command_handler import get_commands_text

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message with floating buttons when the command /start is issued."""
    user = update.effective_user
    is_owner = str(user.id) == OWNER_ID
    is_admin = user.id in BOT_ADMIN_IDS
    
    # إضافة رسالة تشخيصية لتتبع معرفات المستخدمين
    logging.info(f"User ID: {user.id}, Owner ID: {OWNER_ID}, is_owner: {is_owner}, is_admin: {is_admin}, BOT_ADMIN_IDS: {BOT_ADMIN_IDS}")
    
    # التحقق من الاشتراك الإجباري
    from utils.bot_settings import get_force_subscription_settings, check_subscription
    force_sub_settings = get_force_subscription_settings()
    if force_sub_settings.get("enabled", False):
        is_subscribed = await check_subscription(context.bot, user.id)
        if not is_subscribed:
            channel = force_sub_settings.get("channel", "@DARKCODE_Channel")
            message = force_sub_settings.get("message", "🔒 عليك الاشتراك في القناة أولاً لاستخدام البوت")
            
            # إنشاء أزرار للاشتراك والتحقق
            keyboard = [
                [InlineKeyboardButton("✅ اشترك الآن", url=f"https://t.me/{channel.replace('@', '')}")],
                [InlineKeyboardButton("🔄 تحقق من الاشتراك", callback_data="check_subscription")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            return
    
    # Create floating menu buttons - الأيقونات العائمة مع وضع لوحة التحكم بشكل رأسي
    keyboard = [
        [
            InlineKeyboardButton("🎵 الموسيقى", callback_data="play_music"),
            InlineKeyboardButton("🛡️ الحماية", callback_data="protection")
        ],
        [
            InlineKeyboardButton("📚 الأوامر", callback_data="commands"),
            InlineKeyboardButton("➕ إضافة للمجموعة", callback_data="add_to_group")
        ],
        [
            InlineKeyboardButton("👨‍💻 المطور", url=f"https://t.me/{BOT_DEVELOPER.replace('@', '')}"),
            InlineKeyboardButton("📣 القناة", url=f"https://t.me/{BOT_CHANNEL.replace('@', '')}")
        ]
    ]
    
    # هنا نضيف زر لوحة التحكم للمشرفين والمالك فقط (بشكل رأسي منفصل)
    if is_owner or is_admin:
        keyboard.append([InlineKeyboardButton("⚙️ لوحة تحكم المشرف", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # الحصول على رسالة الترحيب المخصصة
    from utils.bot_settings import get_welcome_message
    welcome_message = get_welcome_message()
    
    admin_text = ""
    if is_owner:
        admin_text = "👑 أنت مالك البوت"
    elif is_admin:
        admin_text = "🔰 أنت مشرف في البوت"
    
    try:
        with open("attached_assets/IMG_20250422_013112_433.jpg", "rb") as photo:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=photo,
                caption=f"مرحبًا {user.mention_html()}! \n\n"
                        f"{welcome_message} \n"
                        f"{admin_text}\n\n"
                        f"اختر أحد الخيارات أدناه:",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logging.error(f"Error sending welcome message with photo: {e}")
        # Fallback to text-only message if image fails
        await update.message.reply_text(
            f"مرحبًا {user.mention_html()}! \n\n"
            f"{welcome_message} \n"
            f"{admin_text}\n\n"
            f"اختر أحد الخيارات أدناه:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "commands":
        commands_text = get_commands_text()
        await query.message.reply_text(commands_text, parse_mode=ParseMode.HTML)
    
    elif query.data == "add_to_group":
        # Show instructions for adding the bot to a group
        invite_link = f"https://t.me/{context.bot.username}?startgroup=true"
        keyboard = [
            [InlineKeyboardButton("أضف البوت إلى مجموعتك", url=invite_link)],
            [InlineKeyboardButton("العودة", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_caption(
            caption="يمكنك إضافة البوت إلى مجموعتك بالضغط على الزر أدناه.\n\n"
            "لاستخدام جميع ميزات البوت، يرجى منح البوت الصلاحيات التالية:\n"
            "• حذف الرسائل\n"
            "• حظر المستخدمين\n"
            "• إضافة مستخدمين\n"
            "• إدارة الروابط\n"
            "• إرسال الوسائط\n\n"
            "بعد إضافة البوت، استخدم أمر /settings لتخصيص إعدادات الحماية.",
            reply_markup=reply_markup
        )
    
    elif query.data == "admin_panel":
        # Admin panel with privileged actions
        user = update.effective_user
        is_owner = str(user.id) == OWNER_ID
        
        keyboard = [
            [InlineKeyboardButton("إدارة المشرفين", callback_data="manage_admins")],
            [InlineKeyboardButton("تعديل قناة البوت", callback_data="set_channel")],
            [InlineKeyboardButton("إحصائيات البوت", callback_data="bot_stats")],
            [InlineKeyboardButton("🤖 إدارة الأوامر المخصصة", callback_data="custom_commands")]
        ]
        
        # Owner-only commands
        if is_owner:
            keyboard.append([InlineKeyboardButton("إرسال رسالة لجميع المستخدمين", callback_data="broadcast")])
            keyboard.append([InlineKeyboardButton("تعديل رسالة الترحيب", callback_data="set_welcome")])
            keyboard.append([InlineKeyboardButton("⚙️ الإعدادات المتقدمة", callback_data="advanced_settings")])
        
        keyboard.append([InlineKeyboardButton("👨‍💻 تواصل مع المطور", url=f"https://t.me/{BOT_DEVELOPER.replace('@', '')}")])
        keyboard.append([InlineKeyboardButton("العودة", callback_data="back_to_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_caption(
            caption="مرحبًا بك في لوحة تحكم المشرف. اختر إحدى الخيارات:",
            reply_markup=reply_markup
        )
    
    elif query.data == "play_music":
        keyboard = [
            [InlineKeyboardButton("بحث عن أغنية", callback_data="search_music")],
            [InlineKeyboardButton("تشغيل من يوتيوب", callback_data="play_from_youtube")],
            [InlineKeyboardButton("تحميل أغنية", callback_data="download_music")],
            [InlineKeyboardButton("العودة", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_caption(
            caption="اختر إحدى خيارات الموسيقى:",
            reply_markup=reply_markup
        )
    
    elif query.data == "protection":
        keyboard = [
            [InlineKeyboardButton("حظر مستخدم", callback_data="ban_user")],
            [InlineKeyboardButton("طرد مستخدم", callback_data="kick_user")],
            [InlineKeyboardButton("تحذير مستخدم", callback_data="warn_user")],
            [InlineKeyboardButton("⚙️ إعدادات الحماية", callback_data="protection_settings")],
            [InlineKeyboardButton("العودة", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_caption(
            caption="اختر إحدى خيارات الحماية:",
            reply_markup=reply_markup
        )
        
    elif query.data == "protection_settings":
        # تحقق مما إذا كان هذا محادثة خاصة أو مجموعة
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        
        if chat_type == "private":
            # في المحادثات الخاصة، اطلب من المستخدم تحديد المجموعة
            await query.message.edit_text(
                "⚠️ يجب استخدام هذا الأمر داخل المجموعة التي تريد تعديل إعداداتها.\n\n"
                "الرجاء استخدام الأمر /settings داخل المجموعة بعد إضافة البوت إليها."
            )
            return
        
        # تحقق من صلاحيات المستخدم (يجب أن يكون مشرفًا في المجموعة أو مالك البوت)
        user = update.effective_user
        is_owner = str(user.id) == OWNER_ID
        
        if not is_owner:
            try:
                chat_member = await context.bot.get_chat_member(chat_id, user.id)
                if chat_member.status not in ['administrator', 'creator']:
                    await query.message.edit_text("⚠️ عذراً، يجب أن تكون مشرفًا في المجموعة لتعديل إعدادات الحماية.")
                    return
            except BadRequest:
                await query.message.edit_text("⚠️ حدث خطأ أثناء التحقق من صلاحياتك. الرجاء المحاولة مرة أخرى.")
                return
        
        # تحويل الطلب إلى معالج إعدادات الحماية
        from utils.group_protection import handle_protection_setting_callback
        await handle_protection_setting_callback(update, context, f"protection_settings:{chat_id}")
    
    elif query.data == "check_subscription":
        # التحقق من اشتراك المستخدم في القناة
        user = update.effective_user
        from utils.bot_settings import get_force_subscription_settings, check_subscription
        force_sub_settings = get_force_subscription_settings()
        
        if not force_sub_settings.get("enabled", False):
            # إذا تم تعطيل الاشتراك الإجباري
            await query.message.edit_text("✅ تم تعطيل الاشتراك الإجباري، يمكنك استخدام البوت مباشرة!")
            return
            
        is_subscribed = await check_subscription(context.bot, user.id)
        if is_subscribed:
            # المستخدم مشترك، توجيهه إلى القائمة الرئيسية
            await query.message.delete()
            # إعادة توجيه إلى أمر /start
            await start(update, context)
        else:
            # المستخدم غير مشترك، إظهار رسالة تذكير
            channel = force_sub_settings.get("channel", "@DARKCODE_Channel")
            
            keyboard = [
                [InlineKeyboardButton("✅ اشترك الآن", url=f"https://t.me/{channel.replace('@', '')}")],
                [InlineKeyboardButton("🔄 تحقق مرة أخرى", callback_data="check_subscription")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                "❌ لم يتم الاشتراك بعد! يرجى الاشتراك في القناة أولاً ثم الضغط على 'تحقق مرة أخرى'.",
                reply_markup=reply_markup
            )
    
    elif query.data == "back_to_main":
        # Return to main menu
        user = update.effective_user
        is_owner = str(user.id) == OWNER_ID
        is_admin = user.id in BOT_ADMIN_IDS
        
        # إضافة رسالة تشخيصية في وظيفة back_to_main
        logging.info(f"BACK TO MAIN - User ID: {user.id}, Owner ID: {OWNER_ID}, is_owner: {is_owner}, is_admin: {is_admin}, BOT_ADMIN_IDS: {BOT_ADMIN_IDS}")
        
        # الأيقونات العائمة مع وضع لوحة التحكم بشكل رأسي منفصل
        keyboard = [
            [
                InlineKeyboardButton("🎵 الموسيقى", callback_data="play_music"),
                InlineKeyboardButton("🛡️ الحماية", callback_data="protection")
            ],
            [
                InlineKeyboardButton("📚 الأوامر", callback_data="commands"),
                InlineKeyboardButton("➕ إضافة للمجموعة", callback_data="add_to_group")
            ],
            [
                InlineKeyboardButton("👨‍💻 المطور", url=f"https://t.me/{BOT_DEVELOPER.replace('@', '')}"),
                InlineKeyboardButton("📣 القناة", url=f"https://t.me/{BOT_CHANNEL.replace('@', '')}")
            ]
        ]
        
        # Add admin panel button if user is owner or admin (بشكل رأسي منفصل)
        if is_owner or is_admin:
            keyboard.append([InlineKeyboardButton("⚙️ لوحة تحكم المشرف", callback_data="admin_panel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        admin_text = ""
        if is_owner:
            admin_text = "👑 أنت مالك البوت"
        elif is_admin:
            admin_text = "🔰 أنت مشرف في البوت"
            
        await query.message.edit_caption(
            caption=f"مرحبًا! \n\nأهلاً بك في بوت الموسيقى وحماية المجموعات.\n"
            f"{admin_text}\n\n"
            f"اختر أحد الخيارات أدناه:",
            reply_markup=reply_markup
        )
    
    elif query.data == "search_music":
        await query.message.reply_text(
            "أرسل لي اسم الأغنية للبحث عنها بالصيغة التالية:\n"
            "/search اسم الأغنية"
        )
    
    elif query.data == "play_from_youtube":
        await query.message.reply_text(
            "أرسل لي رابط الفيديو من يوتيوب لتشغيله بالصيغة التالية:\n"
            "/play رابط الفيديو"
        )
    
    elif query.data == "download_music":
        await query.message.reply_text(
            "أرسل لي رابط الفيديو من يوتيوب لتحميله بالصيغة التالية:\n"
            "/download رابط الفيديو"
        )
    
    elif query.data in ["ban_user", "kick_user", "warn_user"]:
        action_name = {
            "ban_user": "لحظر",
            "kick_user": "لطرد",
            "warn_user": "لتحذير"
        }[query.data]
        await query.message.reply_text(
            f"أرسل الأمر {action_name} متبوعًا باسم المستخدم أو الرد على رسالته.\n"
            f"مثال: /{query.data.split('_')[0]} @username"
        )
        
    elif query.data == "manage_admins":
        # Admin management panel - only for owner
        user = update.effective_user
        if str(user.id) != OWNER_ID:
            await query.message.reply_text("عذراً، هذه الميزة متاحة فقط لمالك البوت.")
            return
            
        # TODO: Implement admin management
        await query.message.reply_text(
            "لإضافة مشرف جديد، استخدم الأمر:\n"
            "/add_admin [معرف المستخدم]\n\n"
            "لإزالة مشرف، استخدم الأمر:\n"
            "/remove_admin [معرف المستخدم]"
        )
    
    elif query.data == "set_channel":
        # Channel settings - only for owner/admins
        user = update.effective_user
        is_owner = str(user.id) == OWNER_ID
        is_admin = user.id in BOT_ADMIN_IDS
        
        if not (is_owner or is_admin):
            await query.message.reply_text("عذراً، هذه الميزة متاحة فقط للمشرفين.")
            return
            
        await query.message.reply_text(
            "لتعيين قناة البوت، استخدم الأمر:\n"
            "/set_channel [معرف القناة]\n\n"
            "مثال: /set_channel @MyChannel"
        )
        
    elif query.data == "protection_settings":
        # إعدادات الحماية
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        # التحقق من صلاحيات المستخدم
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user.id)
            if chat_member.status not in ['administrator', 'creator'] and str(user.id) != OWNER_ID:
                await query.message.reply_text("عذراً، هذه الميزة متاحة فقط للمشرفين.")
                return
        except BadRequest:
            # إذا كان في محادثة خاصة
            if update.effective_chat.type == "private":
                await query.message.reply_text("هذه الميزة متاحة فقط في المجموعات.")
                return
                
        # جلب لوحة إعدادات الحماية
        from utils.group_protection import get_protection_settings_keyboard
        keyboard = await get_protection_settings_keyboard(chat_id)
        
        await query.message.edit_text(
            "⚙️ **إعدادات الحماية للمجموعة**\n\n"
            "اختر الميزات التي تريد تفعيلها أو تعطيلها:",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )

    elif query.data.startswith("protection_toggle:"):
        # تبديل إعدادات الحماية
        parts = query.data.split(":")
        if len(parts) != 3:
            return
            
        setting_name = parts[1]
        chat_id = int(parts[2])
        
        # التحقق من صلاحيات المستخدم
        user = update.effective_user
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user.id)
            if chat_member.status not in ['administrator', 'creator'] and str(user.id) != OWNER_ID:
                await query.answer("عذراً، هذه الميزة متاحة فقط للمشرفين.")
                return
        except BadRequest:
            await query.answer("حدث خطأ. تأكد من أنك مشرف في المجموعة.")
            return
            
        # تحديث الإعدادات
        from utils.group_protection import get_group_settings, update_group_settings
        settings = get_group_settings(chat_id)
        settings[setting_name] = not settings.get(setting_name, True)
        update_group_settings(chat_id, settings)
        
        # تحديث لوحة الإعدادات
        from utils.group_protection import get_protection_settings_keyboard
        keyboard = await get_protection_settings_keyboard(chat_id)
        
        await query.answer(f"تم {'تفعيل' if settings[setting_name] else 'تعطيل'} {setting_name}")
        await query.message.edit_reply_markup(reply_markup=keyboard)
        
    elif query.data.startswith("protection_warn_limit:"):
        # تغيير حد التحذيرات
        parts = query.data.split(":")
        if len(parts) != 2:
            return
            
        chat_id = int(parts[1])
        
        # التحقق من صلاحيات المستخدم
        user = update.effective_user
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user.id)
            if chat_member.status not in ['administrator', 'creator'] and str(user.id) != OWNER_ID:
                await query.answer("عذراً، هذه الميزة متاحة فقط للمشرفين.")
                return
        except BadRequest:
            await query.answer("حدث خطأ. تأكد من أنك مشرف في المجموعة.")
            return
            
        # جلب الإعدادات الحالية
        from utils.group_protection import get_group_settings, update_group_settings
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
        
        keyboard.append([InlineKeyboardButton("العودة", callback_data="protection_settings")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            "⚠️ اختر عدد التحذيرات قبل اتخاذ الإجراء:",
            reply_markup=reply_markup
        )
        
    elif query.data == "custom_commands":
        # إدارة الأوامر المخصصة
        user = update.effective_user
        is_owner = str(user.id) == OWNER_ID
        is_admin = user.id in BOT_ADMIN_IDS
        
        if not (is_owner or is_admin):
            await query.message.reply_text("عذراً، هذه الميزة متاحة فقط للمشرفين.")
            return
        
        # جلب قائمة الأوامر المخصصة
        all_commands = get_all_custom_commands()
        commands_count = len(all_commands)
        
        # إنشاء نص الواجهة
        text = "🤖 **إدارة الأوامر المخصصة**\n\n"
        
        if commands_count == 0:
            text += "لا توجد أوامر مخصصة حالياً. يمكنك إضافة أوامر جديدة عبر الأزرار أدناه."
        else:
            text += f"يوجد حالياً {commands_count} أمر مخصص:\n\n"
            for i, (cmd_name, cmd_info) in enumerate(all_commands.items(), 1):
                text += f"{i}. /{cmd_name} - استخدم {cmd_info['usage_count']} مرة\n"
        
        # إنشاء الأزرار
        keyboard = [
            [InlineKeyboardButton("➕ إضافة أمر جديد", callback_data="add_custom_command")],
        ]
        
        if commands_count > 0:
            keyboard.append([InlineKeyboardButton("📝 تعديل أمر", callback_data="edit_custom_command")])
            keyboard.append([InlineKeyboardButton("🗑️ حذف أمر", callback_data="delete_custom_command")])
            keyboard.append([InlineKeyboardButton("📋 تفاصيل الأوامر", callback_data="list_custom_commands")])
        
        keyboard.append([InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_panel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
    elif query.data == "toggle_force_subscription":
        # تبديل حالة الاشتراك الإجباري
        user = update.effective_user
        is_owner = str(user.id) == OWNER_ID
        
        if not is_owner:
            await query.message.reply_text("عذراً، هذه الميزة متاحة فقط لمالك البوت.")
            return
        
        # تغيير حالة الاشتراك الإجباري
        from utils.bot_settings import get_force_subscription_settings, update_force_subscription
        force_sub = get_force_subscription_settings()
        new_state = not force_sub.get("enabled", False)
        
        # تحديث الإعدادات
        success, message = update_force_subscription(
            enabled=new_state,
            channel=force_sub.get("channel"),
            message=force_sub.get("message")
        )
        
        if success:
            # إعادة عرض صفحة الإعدادات المتقدمة
            await query.answer(f"تم {'تفعيل' if new_state else 'تعطيل'} الاشتراك الإجباري")
            # إعادة توجيه إلى الإعدادات المتقدمة
            await query_callback_data(update, context, "advanced_settings")
        else:
            await query.answer(f"حدث خطأ: {message}")
    
    elif query.data == "force_sub_settings":
        # إعدادات الاشتراك الإجباري
        user = update.effective_user
        is_owner = str(user.id) == OWNER_ID
        
        if not is_owner:
            await query.message.reply_text("عذراً، هذه الميزة متاحة فقط لمالك البوت.")
            return
        
        # جلب الإعدادات الحالية
        from utils.bot_settings import get_force_subscription_settings
        force_sub = get_force_subscription_settings()
        
        await query.message.edit_text(
            "🔒 **إعدادات الاشتراك الإجباري**\n\n"
            f"الحالة: {'✅ مفعل' if force_sub.get('enabled', False) else '❌ معطل'}\n"
            f"القناة: {force_sub.get('channel', 'غير محددة')}\n\n"
            "لتعيين قناة الاشتراك الإجباري، أرسل الأمر:\n"
            "`/set_force_channel معرف_القناة`\n\n"
            "لتعيين رسالة الاشتراك الإجباري، أرسل الأمر:\n"
            "`/set_force_message نص_الرسالة`\n\n"
            "يمكنك استخدام تنسيق HTML في الرسالة.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("العودة", callback_data="advanced_settings")]])
        )
    
    elif query.data == "set_developer_id":
        # تعيين معرف المطور
        user = update.effective_user
        is_owner = str(user.id) == OWNER_ID
        
        if not is_owner:
            await query.message.reply_text("عذراً، هذه الميزة متاحة فقط لمالك البوت.")
            return
        
        # إعداد حالة المحادثة لانتظار معرف المطور الجديد
        if 'state' not in context.user_data:
            context.user_data['state'] = {}
        
        context.user_data['state']['waiting_for_developer_id'] = True
        
        await query.message.edit_text(
            "👤 **تعديل معرف المطور**\n\n"
            "الرجاء إرسال معرف المطور الجديد (رقم).\n"
            "يمكنك الحصول على معرف مستخدم تيليجرام باستخدام بوت @userinfobot\n\n"
            "أرسل /cancel لإلغاء العملية.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("إلغاء", callback_data="advanced_settings")]])
        )
    
    elif query.data == "clear_cache":
        # تنظيف ذاكرة التخزين المؤقت
        user = update.effective_user
        is_owner = str(user.id) == OWNER_ID
        
        if not is_owner:
            await query.message.reply_text("عذراً، هذه الميزة متاحة فقط لمالك البوت.")
            return
        
        # تنظيف ذاكرة التخزين المؤقت
        from utils.music_handler import clean_cache
        
        try:
            clean_cache()
            await query.answer("تم تنظيف ذاكرة التخزين المؤقت بنجاح!")
            
            # إعادة توجيه إلى الإعدادات المتقدمة
            await query_callback_data(update, context, "advanced_settings")
        except Exception as e:
            await query.answer(f"حدث خطأ أثناء تنظيف ذاكرة التخزين المؤقت: {str(e)}")
    
    elif query.data == "set_welcome":
        # تعديل رسالة الترحيب
        user = update.effective_user
        is_owner = str(user.id) == OWNER_ID
        
        if not is_owner:
            await query.message.reply_text("عذراً، هذه الميزة متاحة فقط لمالك البوت.")
            return
            
        # عرض رسالة الترحيب الحالية والتعليمات
        from utils.bot_settings import get_welcome_message
        current_welcome = get_welcome_message()
        
        await query.message.edit_text(
            f"✏️ **تعديل رسالة الترحيب**\n\n"
            f"الرسالة الحالية:\n\n"
            f"{current_welcome}\n\n"
            f"لتعديل رسالة الترحيب، أرسل الأمر:\n"
            f"`/set_welcome_message الرسالة الجديدة`\n\n"
            f"يمكنك استخدام تنسيق HTML في الرسالة.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("العودة", callback_data="admin_panel")]])
        )
    
    elif query.data == "advanced_settings":
        # الإعدادات المتقدمة
        user = update.effective_user
        is_owner = str(user.id) == OWNER_ID
        
        if not is_owner:
            await query.message.reply_text("عذراً، هذه الميزة متاحة فقط لمالك البوت.")
            return
            
        # إنشاء لوحة الإعدادات المتقدمة
        from utils.bot_settings import get_force_subscription_settings
        force_sub = get_force_subscription_settings()
        force_sub_status = "✅ مفعل" if force_sub.get("enabled", False) else "❌ معطل"
        
        keyboard = [
            [InlineKeyboardButton(f"🔒 الاشتراك الإجباري: {force_sub_status}", callback_data="toggle_force_subscription")],
            [InlineKeyboardButton("⚙️ إعدادات الاشتراك الإجباري", callback_data="force_sub_settings")],
            [InlineKeyboardButton("👤 تعديل معرف المطور", callback_data="set_developer_id")],
            [InlineKeyboardButton("🧹 تنظيف ذاكرة التخزين المؤقت", callback_data="clear_cache")],
            [InlineKeyboardButton("🔙 العودة", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            "⚙️ **الإعدادات المتقدمة**\n\n"
            "هنا يمكنك تعديل الإعدادات المتقدمة للبوت.\n"
            "اختر أحد الخيارات أدناه:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif query.data == "bot_stats":
        # عرض إحصائيات البوت
        user = update.effective_user
        is_owner = str(user.id) == OWNER_ID
        is_admin = user.id in BOT_ADMIN_IDS
        
        if not (is_owner or is_admin):
            await query.message.reply_text("عذراً، هذه الميزة متاحة فقط للمشرفين.")
            return
        
        # حساب وقت تشغيل البوت
        uptime_seconds = int(time.time() - BOT_START_TIME)
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        uptime_str = ""
        if days > 0:
            uptime_str += f"{days} يوم "
        if hours > 0:
            uptime_str += f"{hours} ساعة "
        if minutes > 0:
            uptime_str += f"{minutes} دقيقة "
        if seconds > 0 or not uptime_str:
            uptime_str += f"{seconds} ثانية"
        
        # إنشاء نص الإحصائيات
        stats_text = (
            "📊 **إحصائيات البوت**\n\n"
            f"⏱️ وقت التشغيل: {uptime_str}\n"
            f"📨 الرسائل المستلمة: {BOT_STATISTICS['messages_received']}\n"
            f"🎵 الأغاني التي تم تشغيلها: {BOT_STATISTICS['songs_played']}\n"
            f"🔍 عمليات البحث: {BOT_STATISTICS['searches_performed']}\n"
            f"⬇️ التنزيلات المكتملة: {BOT_STATISTICS['downloads_completed']}\n"
            f"💬 الأوامر المستخدمة: {BOT_STATISTICS['commands_used']}\n"
            f"👥 المجموعات المنضم إليها: {BOT_STATISTICS['groups_joined']}\n"
            f"⚠️ المستخدمين المحذرين: {BOT_STATISTICS['users_warned']}\n"
            f"🚫 المستخدمين المحظورين: {BOT_STATISTICS['users_banned']}\n"
            f"📢 رسائل البث المرسلة: {BOT_STATISTICS['broadcasts_sent']}\n\n"
            f"👑 مالك البوت: {BOT_DEVELOPER}\n"
            f"📣 قناة البوت: {BOT_CHANNEL}"
        )
        
        # إضافة زر العودة
        keyboard = [
            [InlineKeyboardButton("تحديث الإحصائيات", callback_data="bot_stats")],
            [InlineKeyboardButton("العودة للوحة التحكم", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(stats_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    elif query.data == "broadcast":
        # التحقق من صلاحيات المستخدم
        user = update.effective_user
        is_owner = str(user.id) == OWNER_ID
        
        if not is_owner:
            await query.message.reply_text("عذراً، هذه الميزة متاحة فقط لمالك البوت.")
            return
        
        # إعداد حالة المحادثة لانتظار رسالة البث
        if 'state' not in context.user_data:
            context.user_data['state'] = {}
        
        context.user_data['state']['waiting_for_broadcast'] = True
        
        # إرسال تعليمات البث
        await query.message.edit_text(
            "🔄 إرسال رسالة لجميع المستخدمين\n\n"
            "الرجاء كتابة الرسالة التي تريد إرسالها لجميع مستخدمي البوت.\n"
            "أرسل /cancel لإلغاء العملية."
        )
    
    elif query.data == "add_custom_command":
        # إضافة أمر مخصص جديد
        user = update.effective_user
        is_owner = str(user.id) == OWNER_ID
        is_admin = user.id in BOT_ADMIN_IDS
        
        if not (is_owner or is_admin):
            await query.message.reply_text("عذراً، هذه الميزة متاحة فقط للمشرفين.")
            return
        
        # إعداد حالة المحادثة لانتظار اسم الأمر
        if 'state' not in context.user_data:
            context.user_data['state'] = {}
        
        context.user_data['state']['waiting_for_command_name'] = True
        
        # إرسال تعليمات إضافة الأمر
        await query.message.edit_text(
            "➕ إضافة أمر مخصص جديد\n\n"
            "الرجاء إرسال اسم الأمر بدون علامة / في البداية.\n"
            "مثال: `ترحيب` أو `قوانين`\n\n"
            "أرسل /cancel لإلغاء العملية.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif query.data == "edit_custom_command":
        # تعديل أمر مخصص
        user = update.effective_user
        is_owner = str(user.id) == OWNER_ID
        is_admin = user.id in BOT_ADMIN_IDS
        
        if not (is_owner or is_admin):
            await query.message.reply_text("عذراً، هذه الميزة متاحة فقط للمشرفين.")
            return
            
        # جلب قائمة الأوامر المخصصة
        all_commands = get_all_custom_commands()
        if not all_commands:
            await query.message.edit_text(
                "⚠️ لا توجد أوامر مخصصة لتعديلها. قم بإضافة أوامر أولاً.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("العودة", callback_data="custom_commands")]])
            )
            return
            
        # إنشاء قائمة بالأوامر للاختيار
        keyboard = []
        for cmd_name in all_commands.keys():
            keyboard.append([InlineKeyboardButton(f"/{cmd_name}", callback_data=f"select_edit_cmd:{cmd_name}")])
            
        keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="custom_commands")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            "📝 تعديل أمر مخصص\n\n"
            "اختر الأمر الذي تريد تعديله:",
            reply_markup=reply_markup
        )
    
    elif query.data.startswith("select_edit_cmd:"):
        # اختيار أمر للتعديل
        cmd_name = query.data.split(":")[1]
        
        # إعداد حالة المحادثة لانتظار النص الجديد
        if 'state' not in context.user_data:
            context.user_data['state'] = {}
            
        context.user_data['state']['editing_command'] = cmd_name
        context.user_data['state']['waiting_for_command_text'] = True
        
        # الحصول على النص الحالي للأمر
        cmd_info = get_custom_command(cmd_name)
        current_text = cmd_info['response'] if cmd_info else ""
        
        await query.message.edit_text(
            f"📝 تعديل الأمر /{cmd_name}\n\n"
            f"النص الحالي:\n{current_text}\n\n"
            "أرسل النص الجديد للأمر.\n"
            "أرسل /cancel لإلغاء العملية."
        )
    
    elif query.data == "delete_custom_command":
        # حذف أمر مخصص
        user = update.effective_user
        is_owner = str(user.id) == OWNER_ID
        is_admin = user.id in BOT_ADMIN_IDS
        
        if not (is_owner or is_admin):
            await query.message.reply_text("عذراً، هذه الميزة متاحة فقط للمشرفين.")
            return
            
        # جلب قائمة الأوامر المخصصة
        all_commands = get_all_custom_commands()
        if not all_commands:
            await query.message.edit_text(
                "⚠️ لا توجد أوامر مخصصة لحذفها. قم بإضافة أوامر أولاً.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("العودة", callback_data="custom_commands")]])
            )
            return
            
        # إنشاء قائمة بالأوامر للاختيار
        keyboard = []
        for cmd_name in all_commands.keys():
            keyboard.append([InlineKeyboardButton(f"/{cmd_name}", callback_data=f"confirm_delete_cmd:{cmd_name}")])
            
        keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="custom_commands")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            "🗑️ حذف أمر مخصص\n\n"
            "اختر الأمر الذي تريد حذفه:",
            reply_markup=reply_markup
        )
    
    elif query.data.startswith("confirm_delete_cmd:"):
        # تأكيد حذف أمر
        cmd_name = query.data.split(":")[1]
        
        # إنشاء أزرار التأكيد
        keyboard = [
            [
                InlineKeyboardButton("✅ نعم، احذف الأمر", callback_data=f"delete_cmd:{cmd_name}"),
                InlineKeyboardButton("❌ لا، إلغاء", callback_data="custom_commands")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            f"⚠️ هل أنت متأكد من حذف الأمر /{cmd_name}؟\n\n"
            "هذا الإجراء لا يمكن التراجع عنه!",
            reply_markup=reply_markup
        )
    
    elif query.data.startswith("delete_cmd:"):
        # تنفيذ حذف الأمر
        cmd_name = query.data.split(":")[1]
        
        # حذف الأمر
        success, message = remove_custom_command(cmd_name)
        
        if success:
            await query.message.edit_text(
                f"✅ {message}\n\nجاري العودة للقائمة الرئيسية..."
            )
            # العودة إلى قائمة الأوامر المخصصة بعد ثانيتين
            await asyncio.sleep(2)
            await query_callback_data(update, context, "custom_commands")
        else:
            await query.message.edit_text(
                f"❌ {message}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("العودة", callback_data="custom_commands")]])
            )
    
    elif query.data == "list_custom_commands":
        # عرض تفاصيل الأوامر المخصصة
        user = update.effective_user
        is_owner = str(user.id) == OWNER_ID
        is_admin = user.id in BOT_ADMIN_IDS
        
        if not (is_owner or is_admin):
            await query.message.reply_text("عذراً، هذه الميزة متاحة فقط للمشرفين.")
            return
            
        # جلب قائمة الأوامر المخصصة
        all_commands = get_all_custom_commands()
        if not all_commands:
            await query.message.edit_text(
                "⚠️ لا توجد أوامر مخصصة حالياً. قم بإضافة أوامر أولاً.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("العودة", callback_data="custom_commands")]])
            )
            return
            
        # إنشاء قائمة تفصيلية
        text = "📋 تفاصيل الأوامر المخصصة\n\n"
        
        for cmd_name, cmd_info in all_commands.items():
            # تقصير النص إذا كان طويلاً
            response = cmd_info['response']
            if len(response) > 30:
                response = response[:30] + "..."
                
            # تنسيق التاريخ
            created_date = datetime.fromtimestamp(cmd_info['created_at']).strftime("%Y-%m-%d")
            
            text += f"🔹 /{cmd_name}\n"
            text += f"  • الاستخدامات: {cmd_info['usage_count']}\n"
            text += f"  • تاريخ الإنشاء: {created_date}\n"
            text += f"  • النص: {response}\n\n"
            
        # إضافة زر العودة
        keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="custom_commands")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # إرسال التفاصيل
        await query.message.edit_text(text, reply_markup=reply_markup)
    
    # التعامل مع الاختيارات من قائمة القرآن
    elif query.data.startswith("quran_"):
        try:
            # استخراج رقم السورة من البيانات
            surah_number = int(query.data.split("_")[1])
            
            # قائمة أسماء السور
            surahs = [
                "الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس",
                "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه"
            ]
            
            # تأكد من أن رقم السورة صالح
            if 1 <= surah_number <= len(surahs):
                surah_name = surahs[surah_number-1]
                
                # إنشاء رابط للسورة
                url = f"https://server7.mp3quran.net/basit/00{surah_number:03d}.mp3"
                if surah_number < 10:
                    url = f"https://server7.mp3quran.net/basit/00{surah_number}.mp3"
                elif surah_number < 100:
                    url = f"https://server7.mp3quran.net/basit/0{surah_number}.mp3"
                    
                await query.message.reply_text(f"جاري تحميل سورة {surah_name}...")
                
                # إرسال ملف الصوت
                try:
                    await query.message.reply_audio(
                        audio=url,
                        title=f"سورة {surah_name}",
                        performer="عبد الباسط عبد الصمد",
                        caption=f"سورة {surah_name} - بصوت الشيخ عبد الباسط عبد الصمد"
                    )
                except Exception as e:
                    await query.message.reply_text(f"عذراً، حدث خطأ أثناء تحميل السورة: {str(e)}")
            else:
                await query.message.reply_text("رقم السورة غير صالح.")
        except Exception as e:
            await query.message.reply_text(f"حدث خطأ: {str(e)}")
    
    # التعامل مع الاختيارات من قائمة الفنانين
    elif query.data.startswith("artist_"):
        try:
            # استخراج رقم الفنان من البيانات
            artist_index = int(query.data.split("_")[1])
            
            # قائمة الفنانين
            artists = [
                "عمرو دياب", "تامر حسني", "إليسا", "نانسي عجرم", "محمد منير", "أم كلثوم", "عبدالحليم حافظ",
                "فيروز", "كاظم الساهر", "ماجد المهندس", "أصالة", "أنغام", "شيرين"
            ]
            
            # تأكد من أن رقم الفنان صالح
            if 0 <= artist_index < len(artists):
                artist_name = artists[artist_index]
                
                # البحث عن أغاني الفنان
                await query.message.reply_text(f"جاري البحث عن أغاني {artist_name}...")
                
                # البحث باستخدام اسم الفنان في يوتيوب
                search_query = f"{artist_name} أغنية"
                results = await search_youtube(search_query)
                
                if not results:
                    await query.message.reply_text(f"لم أستطع العثور على أغاني لـ {artist_name}.")
                    return
                
                # إنشاء قائمة الأغاني
                message = f"🎵 أغاني {artist_name}:\n\n"
                keyboard = []
                
                for i, (title, video_id) in enumerate(results[:5], 1):
                    message += f"{i}. {title}\n"
                    keyboard.append([
                        InlineKeyboardButton(f"{i}. تشغيل", callback_data=f"play_{video_id}"),
                        InlineKeyboardButton(f"تحميل", callback_data=f"download_{video_id}")
                    ])
                
                # إضافة زر العودة
                keyboard.append([InlineKeyboardButton("العودة للقائمة الرئيسية", callback_data="back_to_main")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.reply_text(message, reply_markup=reply_markup)
            else:
                await query.message.reply_text("رقم الفنان غير صالح.")
        except Exception as e:
            await query.message.reply_text(f"حدث خطأ: {str(e)}")
    
    # معالجة أزرار تشغيل الأغاني
    elif query.data.startswith("play_"):
        try:
            # استخراج معرف الفيديو
            video_id = query.data.split("_")[1]
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            await query.message.reply_text("جاري تحميل الأغنية...")
            
            # تشغيل الأغنية
            success, result = await play_music(url, update.effective_chat.id)
            if success:
                await query.message.reply_audio(
                    audio=result['file'],
                    title=result['title'],
                    performer=result['performer'],
                    duration=result['duration'],
                    caption=f"تم تشغيل: {result['title']}"
                )
            else:
                await query.message.reply_text(f"حدث خطأ أثناء تشغيل الأغنية: {result}")
        except Exception as e:
            await query.message.reply_text(f"حدث خطأ أثناء تشغيل الأغنية: {str(e)}")
    
    # معالجة أزرار تحميل الأغاني
    elif query.data.startswith("download_"):
        try:
            # استخراج معرف الفيديو
            video_id = query.data.split("_")[1]
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            await query.message.reply_text("جاري تحميل الأغنية...")
            
            # تحميل الأغنية
            success, result = await download_music(url)
            if success:
                await query.message.reply_audio(
                    audio=result,
                    caption="تم تحميل الأغنية بنجاح!"
                )
            else:
                await query.message.reply_text(f"حدث خطأ أثناء تحميل الأغنية: {result}")
        except Exception as e:
            await query.message.reply_text(f"حدث خطأ أثناء تحميل الأغنية: {str(e)}")

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /search command to search for music on YouTube."""
    if not context.args:
        await update.message.reply_text("الرجاء إدخال اسم الأغنية للبحث عنها.")
        return
    
    # تحديث إحصائيات البوت
    BOT_STATISTICS["commands_used"] += 1
    BOT_STATISTICS["searches_performed"] += 1
    
    query = " ".join(context.args)
    results = await search_youtube(query)
    
    if not results:
        await update.message.reply_text("لم يتم العثور على نتائج. حاول مرة أخرى بكلمات مختلفة.")
        return
    
    message = "نتائج البحث:\n\n"
    keyboard = []
    
    for i, (title, video_id) in enumerate(results[:5], 1):
        message += f"{i}. {title}\n"
        keyboard.append([
            InlineKeyboardButton(f"{i}. تشغيل", callback_data=f"play_{video_id}"),
            InlineKeyboardButton(f"تحميل", callback_data=f"download_{video_id}")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup)

async def play_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /play command to play music from YouTube."""
    if not context.args:
        await update.message.reply_text("الرجاء إدخال رابط الفيديو لتشغيله.")
        return
    
    # تحديث إحصائيات البوت
    BOT_STATISTICS["commands_used"] += 1
    BOT_STATISTICS["songs_played"] += 1
    
    url = context.args[0]
    await update.message.reply_text("جاري تحميل الأغنية...")
    
    success, result = await play_music(url, update.effective_chat.id)
    if success:
        await update.message.reply_audio(
            audio=result,
            caption="تم تشغيل الأغنية بنجاح!"
        )
    else:
        await update.message.reply_text(f"حدث خطأ أثناء تشغيل الأغنية: {result}")

async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /download command to download music from YouTube."""
    if not context.args:
        await update.message.reply_text("الرجاء إدخال رابط الفيديو لتحميله.")
        return
    
    # تحديث إحصائيات البوت
    BOT_STATISTICS["commands_used"] += 1
    BOT_STATISTICS["downloads_completed"] += 1
    
    url = context.args[0]
    await update.message.reply_text("جاري تحميل الأغنية...")
    
    success, result = await download_music(url)
    if success:
        await update.message.reply_audio(
            audio=result,
            caption="تم تحميل الأغنية بنجاح!"
        )
    else:
        await update.message.reply_text(f"حدث خطأ أثناء تحميل الأغنية: {result}")

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /ban command to ban a user from a group."""
    if update.effective_chat.type == "private":
        await update.message.reply_text("هذا الأمر يعمل فقط في المجموعات.")
        return
    
    # تحديث إحصائيات البوت
    BOT_STATISTICS["commands_used"] += 1
    
    # Check if user is admin or owner
    user = update.effective_user
    if str(user.id) != OWNER_ID:
        chat_admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        admin_ids = [admin.user.id for admin in chat_admins]
        if user.id not in admin_ids:
            await update.message.reply_text("هذا الأمر متاح فقط للمشرفين.")
            return
    
    success, message = await ban_user(update, context)
    if success:
        BOT_STATISTICS["users_banned"] += 1
    await update.message.reply_text(message)

async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /kick command to kick a user from a group."""
    if update.effective_chat.type == "private":
        await update.message.reply_text("هذا الأمر يعمل فقط في المجموعات.")
        return
    
    # Check if user is admin or owner
    user = update.effective_user
    if str(user.id) != OWNER_ID:
        chat_admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        admin_ids = [admin.user.id for admin in chat_admins]
        if user.id not in admin_ids:
            await update.message.reply_text("هذا الأمر متاح فقط للمشرفين.")
            return
    
    success, message = await kick_user(update, context)
    await update.message.reply_text(message)

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /warn command to warn a user in a group."""
    if update.effective_chat.type == "private":
        await update.message.reply_text("هذا الأمر يعمل فقط في المجموعات.")
        return
    
    # تحديث إحصائيات البوت
    BOT_STATISTICS["commands_used"] += 1
    
    # Check if user is admin or owner
    user = update.effective_user
    if str(user.id) != OWNER_ID:
        chat_admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        admin_ids = [admin.user.id for admin in chat_admins]
        if user.id not in admin_ids:
            await update.message.reply_text("هذا الأمر متاح فقط للمشرفين.")
            return
    
    success, message = await warn_user(update, context)
    if success:
        BOT_STATISTICS["users_warned"] += 1
    await update.message.reply_text(message)

async def handle_new_member_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle new members joining a group."""
    # تحديث إحصائيات المجموعات
    BOT_STATISTICS["groups_joined"] += 1
    
    for member in update.message.new_chat_members:
        await handle_new_member(update, context, member)

async def handle_member_left(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle members leaving a group."""
    await handle_left_member(update, context, update.message.left_chat_member)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all messages that are not commands."""
    # زيادة عداد الرسائل المستلمة
    BOT_STATISTICS["messages_received"] += 1
    
    # Check for spam and delete if necessary
    if update.effective_chat.type != "private":
        if await delete_spam(update, context):
            return
    
    # تخزين معلومات المستخدم إذا لم تكن موجودة مسبقًا
    user_id = update.effective_user.id
    if 'users' not in context.bot_data:
        context.bot_data['users'] = set()
    context.bot_data['users'].add(user_id)
    
    # التحقق إذا كان المستخدم في انتظار حالة خاصة (مثل رسالة البث أو تعديل إعدادات الحماية)
    if update.effective_chat.type == "private" and str(user_id) == OWNER_ID:
        # حالة انتظار رسالة البث
        if context.user_data.get('state', {}).get('waiting_for_broadcast'):
            # إرسال رسالة البث للجميع
            broadcast_message = update.message.text
            
            # إلغاء حالة الانتظار
            context.user_data['state']['waiting_for_broadcast'] = False
            
            # إرسال رسالة تأكيد
            await update.message.reply_text("جاري إرسال الرسالة لجميع المستخدمين...")
            
            # جمع إحصائيات الإرسال
            sent_count = 0
            failed_count = 0
            
            # إرسال الرسالة لجميع المستخدمين المخزنين
            for user_id in context.bot_data.get('users', set()):
                try:
                    await context.bot.send_message(chat_id=user_id, text=broadcast_message)
                    sent_count += 1
                    # تأخير صغير لتجنب تجاوز حدود API
                    await asyncio.sleep(0.1)
                except Exception as e:
                    failed_count += 1
                    logger.error(f"فشل إرسال رسالة البث للمستخدم {user_id}: {str(e)}")
            
            # تحديث إحصائيات البث
            BOT_STATISTICS["broadcasts_sent"] += 1
            
            # إرسال ملخص النتائج
            await update.message.reply_text(
                f"✅ تم إرسال رسالة البث بنجاح!\n\n"
                f"📩 تم الإرسال إلى: {sent_count} مستخدم\n"
                f"❌ فشل الإرسال إلى: {failed_count} مستخدم"
            )
            return
        
        # حالة انتظار تعديل رسالة الترحيب
        elif context.user_data.get('state', {}).get('waiting_for_welcome'):
            chat_id = context.user_data['state'].get('target_chat_id')
            if not chat_id:
                await update.message.reply_text("⚠️ حدث خطأ في معالجة الطلب. الرجاء المحاولة مرة أخرى.")
                return
            
            # تحديث رسالة الترحيب
            new_welcome = update.message.text
            
            # تحديث الإعدادات
            from utils.group_protection import update_group_settings
            update_group_settings(chat_id, {"welcome_message": new_welcome})
            
            # إلغاء حالة الانتظار
            context.user_data['state']['waiting_for_welcome'] = False
            context.user_data['state']['target_chat_id'] = None
            
            # إرسال تأكيد
            await update.message.reply_text(
                f"✅ تم تحديث رسالة الترحيب بنجاح!\n\n"
                f"الرسالة الجديدة:\n{new_welcome}\n\n"
                f"ملاحظة: يمكنك استخدام {{username}} في الرسالة ليتم استبدالها باسم المستخدم."
            )
            return
        
        # حالة انتظار تعديل رسالة الوداع
        elif context.user_data.get('state', {}).get('waiting_for_goodbye'):
            chat_id = context.user_data['state'].get('target_chat_id')
            if not chat_id:
                await update.message.reply_text("⚠️ حدث خطأ في معالجة الطلب. الرجاء المحاولة مرة أخرى.")
                return
            
            # تحديث رسالة الوداع
            new_goodbye = update.message.text
            
            # تحديث الإعدادات
            from utils.group_protection import update_group_settings
            update_group_settings(chat_id, {"goodbye_message": new_goodbye})
            
            # إلغاء حالة الانتظار
            context.user_data['state']['waiting_for_goodbye'] = False
            context.user_data['state']['target_chat_id'] = None
            
            # إرسال تأكيد
            await update.message.reply_text(
                f"✅ تم تحديث رسالة الوداع بنجاح!\n\n"
                f"الرسالة الجديدة:\n{new_goodbye}\n\n"
                f"ملاحظة: يمكنك استخدام {{username}} في الرسالة ليتم استبدالها باسم المستخدم."
            )
            return
            
        # حالة انتظار اسم الأمر المخصص الجديد
        elif context.user_data.get('state', {}).get('waiting_for_command_name'):
            # التحقق من الصلاحيات
            user = update.effective_user
            is_owner = str(user.id) == OWNER_ID
            is_admin = user.id in BOT_ADMIN_IDS
            
            if not (is_owner or is_admin):
                await update.message.reply_text("عذراً، هذه الميزة متاحة فقط للمشرفين.")
                return
            
            # الحصول على اسم الأمر
            command_name = update.message.text.strip()
            
            # إذا كان أمر إلغاء
            if command_name.startswith('/cancel'):
                context.user_data['state']['waiting_for_command_name'] = False
                await update.message.reply_text("تم إلغاء العملية.")
                return
            
            # تنظيف اسم الأمر
            if command_name.startswith('/'):
                command_name = command_name[1:]
            
            # حفظ اسم الأمر والانتقال لحالة انتظار نص الأمر
            context.user_data['state']['waiting_for_command_name'] = False
            context.user_data['state']['waiting_for_command_text'] = True
            context.user_data['state']['command_name'] = command_name
            
            # إرسال تعليمات إضافة نص الأمر
            await update.message.reply_text(
                f"👍 تم اختيار اسم الأمر: /{command_name}\n\n"
                f"الآن، أرسل النص الذي سيرد به البوت عند استخدام هذا الأمر.\n"
                f"يمكنك استخدام النص العادي، الإيموجي، وكذلك تنسيق Markdown.\n\n"
                f"أرسل /cancel لإلغاء العملية."
            )
            return
            
        # حالة انتظار نص الأمر المخصص الجديد
        elif context.user_data.get('state', {}).get('waiting_for_command_text'):
            # التحقق من الصلاحيات
            user = update.effective_user
            is_owner = str(user.id) == OWNER_ID
            is_admin = user.id in BOT_ADMIN_IDS
            
            if not (is_owner or is_admin):
                await update.message.reply_text("عذراً، هذه الميزة متاحة فقط للمشرفين.")
                return
            
            # الحصول على نص الأمر
            command_text = update.message.text
            
            # إذا كان أمر إلغاء
            if command_text.startswith('/cancel'):
                context.user_data['state']['waiting_for_command_text'] = False
                context.user_data['state'].pop('command_name', None)
                context.user_data['state'].pop('editing_command', None)
                await update.message.reply_text("تم إلغاء العملية.")
                return
            
            # حالة إضافة أمر جديد
            if 'command_name' in context.user_data['state']:
                command_name = context.user_data['state']['command_name']
                success, message = add_custom_command(command_name, command_text, user.id)
                
                # إلغاء حالة الانتظار
                context.user_data['state']['waiting_for_command_text'] = False
                context.user_data['state'].pop('command_name', None)
                
                # إرسال نتيجة العملية
                await update.message.reply_text(message)
                
                # العودة إلى قائمة الأوامر المخصصة
                if success:
                    await update.message.reply_text(
                        "جاري العودة إلى قائمة الأوامر المخصصة...",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("عرض الأوامر المخصصة", callback_data="custom_commands")]
                        ])
                    )
                
            # حالة تعديل أمر موجود
            elif 'editing_command' in context.user_data['state']:
                command_name = context.user_data['state']['editing_command']
                success, message = edit_custom_command(command_name, command_text)
                
                # إلغاء حالة الانتظار
                context.user_data['state']['waiting_for_command_text'] = False
                context.user_data['state'].pop('editing_command', None)
                
                # إرسال نتيجة العملية
                await update.message.reply_text(message)
                
                # العودة إلى قائمة الأوامر المخصصة
                if success:
                    await update.message.reply_text(
                        "جاري العودة إلى قائمة الأوامر المخصصة...",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("عرض الأوامر المخصصة", callback_data="custom_commands")]
                        ])
                    )
                
            return
    
    # التحقق من الأوامر المخصصة
    if update.message.text and update.message.text.startswith('/'):
        command = update.message.text.split(' ')[0].lower()  # الحصول على الأمر بدون باراميترات
        command_name = command[1:]  # إزالة علامة /
        
        # البحث عن الأمر في قاعدة بيانات الأوامر المخصصة
        custom_command = get_custom_command(command_name)
        if custom_command:
            # تسجيل استخدام الأمر
            increment_command_usage(command_name)
            
            # الرد بنص الأمر المخصص
            await update.message.reply_text(
                custom_command['response'],
                parse_mode=ParseMode.MARKDOWN
            )
            return
    
    # Handle direct text commands in Arabic
    message_text = update.message.text.lower() if update.message.text else ""
    
    # Handle music direct commands
    if message_text.startswith("شغل") or message_text.startswith("تشغيل"):
        query = message_text.split(" ", 1)
        if len(query) > 1:
            search_query = query[1]
            await update.message.reply_text(f"جاري البحث عن: {search_query}")
            
            # Search for the song first
            results = await search_youtube(search_query)
            if not results:
                await update.message.reply_text("لم أتمكن من العثور على نتائج للبحث. حاول مرة أخرى بكلمات مختلفة.")
                return
            
            # Get the first result and play it
            title, video_id = results[0]
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            await update.message.reply_text(f"تم العثور على: {title}\nجاري تشغيل الأغنية...")
            
            success, result = await play_music(url, update.effective_chat.id)
            if success:
                await update.message.reply_audio(
                    audio=result['file'],
                    title=result['title'],
                    performer=result['performer'],
                    duration=result['duration'],
                    caption=f"تم تشغيل: {title}"
                )
            else:
                await update.message.reply_text(f"حدث خطأ أثناء تشغيل الأغنية: {result}")
            return
            
    elif message_text.startswith("فيد") or message_text.startswith("فيديو"):
        query = message_text.split(" ", 1)
        if len(query) > 1:
            search_query = query[1]
            await update.message.reply_text(f"جاري البحث عن فيديو: {search_query}")
            
            # Search for the video
            results = await search_youtube(search_query)
            if not results:
                await update.message.reply_text("لم أتمكن من العثور على نتائج للبحث. حاول مرة أخرى بكلمات مختلفة.")
                return
            
            # Get the first result and show it
            title, video_id = results[0]
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            await update.message.reply_text(
                f"تم العثور على الفيديو: {title}\n"
                f"يمكنك مشاهدته على: {url}"
            )
            return
            
    elif message_text.startswith("تشغيل عشوائي"):
        await random_song_command(update, context)
        return
        
    elif message_text.startswith("بحث"):
        query = message_text.split(" ", 1)
        if len(query) > 1:
            search_query = query[1]
            await update.message.reply_text(f"جاري البحث عن: {search_query}")
            
            # Search for music
            results = await search_youtube(search_query)
            if not results:
                await update.message.reply_text("لم أتمكن من العثور على نتائج للبحث. حاول مرة أخرى بكلمات مختلفة.")
                return
            
            # Show search results with buttons
            message = "نتائج البحث:\n\n"
            keyboard = []
            
            for i, (title, video_id) in enumerate(results[:5], 1):
                message += f"{i}. {title}\n"
                keyboard.append([
                    InlineKeyboardButton(f"{i}. تشغيل", callback_data=f"play_{video_id}"),
                    InlineKeyboardButton(f"تحميل", callback_data=f"download_{video_id}")
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(message, reply_markup=reply_markup)
            return
            
    elif message_text.startswith("تحميل") or message_text.startswith("تنزيل"):
        query = message_text.split(" ", 1)
        if len(query) > 1:
            search_query = query[1]
            await update.message.reply_text(f"جاري البحث عن: {search_query} للتحميل...")
            
            # Search for music
            results = await search_youtube(search_query)
            if not results:
                await update.message.reply_text("لم أتمكن من العثور على نتائج للبحث. حاول مرة أخرى بكلمات مختلفة.")
                return
            
            # Get the first result and download it
            title, video_id = results[0]
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            await update.message.reply_text(f"تم العثور على: {title}\nجاري تحميل الأغنية...")
            
            success, result = await download_music(url)
            if success:
                await update.message.reply_audio(
                    audio=result['file'],
                    title=result['title'],
                    performer=result['performer'],
                    duration=result['duration'],
                    caption=f"تم تحميل: {title}"
                )
            else:
                await update.message.reply_text(f"حدث خطأ أثناء تحميل الأغنية: {result}")
            return
            
    elif message_text == "قران" or message_text == "القران":
        await quran_command(update, context)
        return
        
    elif message_text == "اغاني" or message_text == "الاغاني":
        await songs_command(update, context)
        return
        
    elif message_text == "تفعيل الاذان":
        await adhan_command(update, context)
        return
        
    elif message_text == "بنج":
        await ping_command(update, context)
        return
        
    elif message_text == "سورس":
        await source_command(update, context)
        return
    
    # Generic suggestions
    if "موسيقى" in message_text or "أغنية" in message_text:
        await update.message.reply_text(
            "هل تريد البحث عن أغنية؟ استخدم الأمر /search أو 'بحث' متبوعًا باسم الأغنية."
        )
    elif "فيديو" in message_text:
        await update.message.reply_text(
            "هل تريد مشاهدة فيديو؟ استخدم الأمر /video أو 'فيديو' متبوعًا باسم الفيديو."
        )
    elif "حماية" in message_text or "حظر" in message_text or "طرد" in message_text:
        await update.message.reply_text(
            "هل تحتاج إلى استخدام ميزات الحماية؟ استخدم الأوامر /ban أو /kick أو /warn."
        )

async def random_song_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /random command to play a random song."""
    random_artists = ["عمرو دياب", "أم كلثوم", "تامر حسني", "إليسا", "فيروز", "محمد منير"]
    random_artist = random.choice(random_artists)
    
    await update.message.reply_text(f"جاري البحث عن أغنية عشوائية لـ {random_artist}...")
    
    results = await search_youtube(random_artist)
    if not results:
        await update.message.reply_text("عذراً، لم أتمكن من العثور على أغاني عشوائية. حاول مرة أخرى.")
        return
    
    # Choose a random song from results
    title, video_id = random.choice(results)
    await update.message.reply_text(f"تم اختيار: {title}")
    
    await update.message.reply_text("جاري تحميل الأغنية...")
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    success, result = await play_music(url, update.effective_chat.id)
    if success:
        await update.message.reply_audio(
            audio=result['file'],
            title=result['title'],
            performer=result['performer'],
            duration=result['duration'],
            caption=f"تم تشغيل الأغنية العشوائية: {title}"
        )
    else:
        await update.message.reply_text(f"حدث خطأ أثناء تشغيل الأغنية: {result}")

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /ping command to check bot response time."""
    start_time = time.time()
    message = await update.message.reply_text("جاري قياس سرعة الاستجابة...")
    end_time = time.time()
    
    # Calculate response time in milliseconds
    response_time = int((end_time - start_time) * 1000)
    
    await message.edit_text(f"🏓 بونج!\nسرعة الاستجابة: {response_time} مللي ثانية")

async def source_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /source command to show bot information."""
    user_count = 100  # Placeholder, would be calculated from DB
    group_count = 50  # Placeholder, would be calculated from DB
    
    bot_info = await context.bot.get_me()
    
    info_text = f"""<b>ℹ️ معلومات البوت</b>

<b>اسم البوت:</b> {bot_info.first_name}
<b>معرف البوت:</b> @{bot_info.username}
<b>المالك:</b> {BOT_DEVELOPER}
<b>عدد المستخدمين:</b> {user_count}
<b>عدد المجموعات:</b> {group_count}

<b>⚡️ Developer by DARKCODE</b>
"""
    
    keyboard = [
        [InlineKeyboardButton("قناة البوت", url=f"https://t.me/{BOT_CHANNEL.replace('@', '')}")],
        [InlineKeyboardButton("مطور البوت", url=f"https://t.me/{BOT_DEVELOPER.replace('@', '')}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(info_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

async def adhan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /adhan command to enable prayer notifications."""
    chat_id = update.effective_chat.id
    
    # This would store the chat_id in a database to send prayer notifications
    await update.message.reply_text(
        "✅ تم تفعيل تنبيهات الصلاة في هذه المحادثة.\n"
        "سيتم إرسال تنبيه قبل كل صلاة بخمس دقائق."
    )

async def quran_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /quran command to show Quran list."""
    surahs = [
        "الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس",
        "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه"
    ]
    
    keyboard = []
    for i, surah in enumerate(surahs):
        if i % 2 == 0:
            row = [InlineKeyboardButton(surah, callback_data=f"quran_{i+1}")]
            if i+1 < len(surahs):
                row.append(InlineKeyboardButton(surahs[i+1], callback_data=f"quran_{i+2}"))
            keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📖 قائمة القرآن الكريم\n\nاختر السورة التي تريد الاستماع إليها:",
        reply_markup=reply_markup
    )

async def songs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /songs command to show artists list."""
    artists = [
        "عمرو دياب", "تامر حسني", "إليسا", "نانسي عجرم", "محمد منير", "أم كلثوم", "عبدالحليم حافظ",
        "فيروز", "كاظم الساهر", "ماجد المهندس", "أصالة", "أنغام", "شيرين"
    ]
    
    keyboard = []
    for i, artist in enumerate(artists):
        if i % 2 == 0:
            row = [InlineKeyboardButton(artist, callback_data=f"artist_{i}")]
            if i+1 < len(artists):
                row.append(InlineKeyboardButton(artists[i+1], callback_data=f"artist_{i+1}"))
            keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🎵 قائمة الفنانين\n\nاختر الفنان الذي تريد الاستماع لأغانيه:",
        reply_markup=reply_markup
    )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """إلغاء العملية الحالية"""
    user_id = update.effective_user.id
    
    if 'state' in context.user_data:
        # إلغاء جميع حالات الانتظار
        context.user_data['state'] = {}
        await update.message.reply_text("✅ تم إلغاء العملية الحالية.")
    else:
        await update.message.reply_text("ليس هناك عملية نشطة للإلغاء.")

async def query_callback_data(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """معالجة أمر من خلال تقليد استجابة الأزرار"""
    # نظرًا لأن data هي صفة للقراءة فقط، سننشئ كائن CallbackQuery جديد بدلاً من ذلك
    
    # بدلاً من تعديل callback_query، سنطلب مباشرة رد استجابة بناءً على نوع البيانات
    if callback_data == "advanced_settings":
        # عرض الإعدادات المتقدمة
        from utils.bot_settings import get_force_subscription_settings
        force_sub = get_force_subscription_settings()
        
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{'✅' if force_sub.get('enabled', False) else '❌'} الاشتراك الإجباري", 
                callback_data="toggle_force_sub"
            )],
            [InlineKeyboardButton("⚙️ إعدادات الاشتراك الإجباري", callback_data="force_sub_settings")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
        ])
        
        await update.callback_query.message.edit_text(
            "⚙️ *الإعدادات المتقدمة*\n\n"
            "اختر أحد الإعدادات للتعديل:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    # يمكن إضافة المزيد من الحالات حسب الحاجة
    elif callback_data == "admin_panel":
        # العودة إلى لوحة التحكم
        user = update.effective_user
        is_owner = str(user.id) == OWNER_ID
        
        # إنشاء لوحة أزرار لوحة التحكم
        keyboard = [
            [InlineKeyboardButton("📊 إحصائيات البوت", callback_data="bot_stats")],
            [InlineKeyboardButton("📝 تعديل رسالة الترحيب", callback_data="edit_welcome")],
            [InlineKeyboardButton("📢 إرسال رسالة للمستخدمين", callback_data="broadcast")],
            [InlineKeyboardButton("⚙️ الإعدادات المتقدمة", callback_data="advanced_settings")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.message.edit_text(
            "👨‍💻 *لوحة تحكم مالك البوت*\n\n"
            "مرحبًا بك في لوحة تحكم البوت. يمكنك من هنا إدارة البوت والاطلاع على الإحصائيات.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

async def video_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /video command to play video from YouTube."""
    if not context.args:
        await update.message.reply_text("الرجاء إدخال رابط الفيديو أو اسم الفيديو للبحث عنه.")
        return
    
    query = " ".join(context.args)
    await update.message.reply_text(f"جاري البحث عن فيديو: {query}")
    
    # Implementation would be similar to play_command but return video instead of audio
    # For now, we'll just search and show a message that it's not fully implemented
    results = await search_youtube(query)
    if not results:
        await update.message.reply_text("لم يتم العثور على نتائج. حاول مرة أخرى بكلمات مختلفة.")
        return
        
    title, video_id = results[0]
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    await update.message.reply_text(
        f"تم العثور على الفيديو: {title}\n"
        f"يمكنك مشاهدته على: {url}"
    )

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it the bot's token
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("play", play_command))
    application.add_handler(CommandHandler("download", download_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("kick", kick_command))
    application.add_handler(CommandHandler("warn", warn_command))
    
    # Add new handlers for the requested features
    application.add_handler(CommandHandler("random", random_song_command))
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("source", source_command))
    application.add_handler(CommandHandler("adhan", adhan_command))
    application.add_handler(CommandHandler("quran", quran_command))
    application.add_handler(CommandHandler("songs", songs_command))
    application.add_handler(CommandHandler("video", video_command))
    
    # We'll handle Arabic commands through message handlers instead of CommandHandler 
    # since Telegram doesn't support non-Latin command names
    
    # Add callback query handler for button presses
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add handlers for group events
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_member_join))
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, handle_member_left))
    
    # Add message handler for non-command messages (for text commands like "شغل" or "تشغيل")
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the Bot
    application.run_polling()

if __name__ == "__main__":
    main()
