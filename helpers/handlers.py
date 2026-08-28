"""
Message, Photo, Video, and Channel Linking Handlers for Ash Cover Bot
"""

import os
import logging
from telegram import Update, InputMediaVideo, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes
from config import LOG_CHANNEL_ID, HOME_MENU_BANNER_URL
from database import (
    save_thumbnail, get_thumbnail, delete_thumbnail, has_thumbnail,
    save_destination_channel, get_destination_channel,
    get_font_style, get_send_mode,
    get_custom_caption, save_custom_caption, delete_custom_caption,
    log_thumbnail_set, log_thumbnail_removed, format_log_message
)
from font import format_caption, get_font_name
from helpers.menus import (
    get_home_menu_text, get_home_menu_markup,
    get_settings_menu, get_fonts_menu, get_channel_menu, get_caption_menu
)

logger = logging.getLogger(__name__)


def bold_entities(text: str):
    from telegram import MessageEntity
    if not text:
        return []
    return [MessageEntity(type=MessageEntity.BOLD, offset=0, length=len(text))]


def apply_caption_template(template: str, filename: str = "", original: str = "") -> str:
    if not template:
        return original or ""
    result = template.replace("{filename}", filename or "")
    result = result.replace("{original}", original or "")
    result = result.replace("{caption}", original or "")
    result = result.replace("{name}", filename or "")
    return result.strip()


async def send_log(context: ContextTypes.DEFAULT_TYPE, message: str):
    if LOG_CHANNEL_ID:
        try:
            await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=message, parse_mode="HTML")
        except Exception as e:
            logger.debug(f"Log send error: {e}")


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = get_home_menu_text()
    kb = get_home_menu_markup(user_id)
    banner = HOME_MENU_BANNER_URL
    if banner:
        try:
            photo = InputFile(banner) if isinstance(banner, str) and os.path.isfile(banner) else banner
            return await update.message.reply_photo(photo=photo, caption=text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass
    await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 <b>Complete Guide</b>\n\n"
        "1. Send any photo to set thumbnail.\n"
        "2. /fonts — choose caption font.\n"
        "3. /caption — set Auto Caption template ({filename}).\n"
        "4. /channel — link destination channel.\n"
        "5. Send any video — cover + caption apply instantly!\n\n"
        "📢 Updates: @MoviesGroupG3\n"
        "👤 Owner: @movies_1780"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Updates", url="https://t.me/MoviesGroupG3"),
         InlineKeyboardButton("👤 Owner", url="https://t.me/movies_1780")]
    ])
    await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")


async def about_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 <b>About Ash Cover Bot</b>\n\n"
        "✅ Instant Thumbnail Replacement\n"
        "✅ 13+ Caption Font Styles\n"
        "✅ Auto Caption Template\n"
        "✅ Auto-send to Destination Channel\n\n"
        "📢 @MoviesGroupG3 | 👤 @movies_1780"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Updates", url="https://t.me/MoviesGroupG3"),
         InlineKeyboardButton("👤 Owner", url="https://t.me/movies_1780")]
    ])
    await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")


async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text, kb = get_settings_menu(user_id)
    await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")


async def fonts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text, kb = get_fonts_menu(user_id)
    await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")


async def caption_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/caption — open Auto Caption menu (works even if button fails)."""
    user_id = update.effective_user.id
    text, kb = get_caption_menu(user_id)
    await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")


async def channel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text, kb = get_channel_menu(user_id)
    await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")


async def remove_thumbnail_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    if delete_thumbnail(user_id):
        log_data = log_thumbnail_removed(user_id, username)
        log_msg = format_log_message(user_id, username, log_data["action"])
        await send_log(context, log_msg)
        return await update.message.reply_text("✅ Thumbnail deleted! Send a new photo anytime.", parse_mode="HTML")
    await update.message.reply_text("⚠️ No saved thumbnail found.", parse_mode="HTML")


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    photo_id = update.message.photo[-1].file_id
    is_replace = has_thumbnail(user_id)
    save_thumbnail(user_id, photo_id)
    log_data = log_thumbnail_set(user_id, username, is_replace=is_replace)
    log_msg = format_log_message(user_id, username, log_data["action"])
    await send_log(context, log_msg)
    action = "Updated" if is_replace else "Saved"
    await update.message.reply_text(f"✅ Thumbnail {action}!\n\nNow send any video to apply this cover.", parse_mode="HTML")


async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "No Username"
    cover = get_thumbnail(user_id)
    if not cover:
        return await update.message.reply_text("❌ No thumbnail found!\nPlease send a photo first.", parse_mode="HTML")
    status_msg = await update.message.reply_text("⏳ Processing video...", parse_mode="HTML")

    filename = ""
    if update.message.video:
        video_id = update.message.video.file_id
        filename = getattr(update.message.video, "file_name", None) or ""
    elif update.message.document:
        video_id = update.message.document.file_id
        filename = getattr(update.message.document, "file_name", None) or ""
    else:
        return

    if not filename:
        filename = "Video"

    font_style = get_font_style(user_id)
    original_caption = update.message.caption or ""
    custom_template = get_custom_caption(user_id)

    if custom_template:
        raw_caption = apply_caption_template(custom_template, filename=filename, original=original_caption)
    else:
        raw_caption = original_caption

    new_caption = format_caption(raw_caption, font_style) if raw_caption else ""
    caption_entities = bold_entities(new_caption) if font_style == "bold" and new_caption else None
    dest_chan = get_destination_channel(user_id)
    send_mode = get_send_mode(user_id)
    media = InputMediaVideo(media=video_id, caption=new_caption, caption_entities=caption_entities, supports_streaming=True, cover=cover)
    try:
        sent_to_user = False
        if send_mode in ("both", "user_only") or not dest_chan:
            await context.bot.edit_message_media(chat_id=update.effective_chat.id, message_id=status_msg.message_id, media=media)
            sent_to_user = True
        dest_success = False
        if dest_chan and send_mode in ("both", "channel_only"):
            try:
                dest_chat_id = dest_chan["channel_id"]
                await context.bot.send_video(
                    chat_id=dest_chat_id, video=video_id, caption=new_caption,
                    caption_entities=caption_entities, supports_streaming=True, thumbnail=cover
                )
                dest_success = True
            except Exception as chan_err:
                logger.error(f"Error posting to channel: {chan_err}")
                await update.message.reply_text(
                    f"⚠️ Channel post failed:\n<code>{str(chan_err)[:120]}</code>\n\nEnsure bot is Admin with Post Messages.",
                    parse_mode="HTML"
                )
        if not sent_to_user and dest_success:
            chan_title = dest_chan.get("channel_title", "Channel")
            await status_msg.edit_text(f"✅ Video processed!\n\nPosted to: <b>{chan_title}</b>", parse_mode="HTML")
        elif sent_to_user and dest_success:
            chan_title = dest_chan.get("channel_title", "Channel")
            await update.message.reply_text(f"📢 Also posted to: <b>{chan_title}</b>", parse_mode="HTML")
        if LOG_CHANNEL_ID:
            try:
                log_caption = (
                    f"🎥 <b>Video Processed</b>\n"
                    f"👤 User: <code>{user_id}</code> (@{username})\n"
                    f"✍️ Font: <code>{get_font_name(font_style)}</code>\n"
                    f"📝 Caption: {(new_caption[:80] if new_caption else 'No Caption')}"
                )
                await context.bot.send_video(chat_id=LOG_CHANNEL_ID, video=video_id, caption=log_caption, supports_streaming=True, thumbnail=cover, parse_mode="HTML")
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Video processing failed: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Processing Failed: <code>{str(e)[:100]}</code>", parse_mode="HTML")


async def text_and_channel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    waiting_for = context.user_data.get("waiting_for")
    fwd_chat = getattr(update.message, "forward_from_chat", None)

    if waiting_for == "custom_caption":
        if not update.message.text:
            return
        raw = update.message.text.strip()
        if raw.lower() in ("/cancel", "cancel"):
            context.user_data.pop("waiting_for", None)
            return await update.message.reply_text("❌ Caption setup cancelled.", parse_mode="HTML")
        save_custom_caption(user_id, raw)
        context.user_data.pop("waiting_for", None)
        text = (
            "✅ <b>Auto Caption Template Saved!</b>\n\n"
            f"<code>{raw[:300]}</code>\n\n"
            "📌 <code>{{filename}}</code> → video name\n"
            "📌 <code>{{original}}</code> → original caption\n\n"
            "Ab har video pe ye caption auto lagega + your font."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 View / Edit", callback_data="submenu_caption")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")]
        ])
        return await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

    if waiting_for == "destination_channel" or (fwd_chat and fwd_chat.type == "channel"):
        channel_input = None
        if fwd_chat and fwd_chat.type == "channel":
            channel_input = fwd_chat.id
        elif update.message.text:
            raw = update.message.text.strip()
            if raw.lower() in ("/cancel", "cancel"):
                context.user_data.pop("waiting_for", None)
                return await update.message.reply_text("❌ Setup cancelled.", parse_mode="HTML")
            if "t.me/" in raw:
                channel_input = "@" + raw.rstrip("/").split("/")[-1]
            elif raw.startswith("-100") or raw.startswith("-"):
                try:
                    channel_input = int(raw)
                except ValueError:
                    channel_input = raw
            elif raw.startswith("@"):
                channel_input = raw
            else:
                try:
                    channel_input = int(raw)
                except ValueError:
                    channel_input = "@" + raw
        if not channel_input:
            return
        verify_msg = await update.message.reply_text("🔍 Verifying channel...", parse_mode="HTML")
        try:
            chat = await context.bot.get_chat(channel_input)
            bot_member = await context.bot.get_chat_member(chat_id=chat.id, user_id=context.bot.id)
            if bot_member.status not in ("administrator", "creator"):
                return await verify_msg.edit_text(
                    f"⚠️ Bot is not Admin in '{chat.title}'\n\nAdd bot as Admin with Post Messages permission.",
                    parse_mode="HTML"
                )
            save_destination_channel(user_id=user_id, channel_id=chat.id, channel_title=chat.title or "Channel", channel_username=chat.username or "")
            context.user_data.pop("waiting_for", None)
            mode_label = "Both" if get_send_mode(user_id) == "both" else ("Channel Only" if get_send_mode(user_id) == "channel_only" else "Chat Only")
            text = (
                f"✅ <b>Channel Connected!</b>\n\n"
                f"📢 <b>{chat.title}</b>\n"
                f"🆔 <code>{chat.id}</code>\n"
                f"📤 Mode: <code>{mode_label}</code>"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🧪 Test Post", callback_data="chan_test")],
                [InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")]
            ])
            await verify_msg.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            await verify_msg.edit_text(f"❌ Connection failed: <code>{str(e)[:120]}</code>", parse_mode="HTML")
