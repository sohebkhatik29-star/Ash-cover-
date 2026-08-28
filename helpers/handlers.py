"""
Message, Photo, Video, and Channel Linking Handlers for Ash Cover Bot
"""

import os
import re
import html
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


def looks_like_html(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(
        r"<(a|b|i|u|s|code|pre|blockquote|tg-spoiler|tg-emoji|strong|em)\b|/?(a|b|i|u|s|code|pre|blockquote|strong|em)>",
        text,
        re.I
    ))


def sanitize_telegram_html(text: str) -> str:
    """
    Clean HTML so Telegram can parse it reliably.
    Handles common movie-channel templates that have:
    - <b><blockquote>...</blockquote></b>  (invalid nesting)
    - newlines inside tags
    - unclosed / mismatched / orphan tags
    - extra spaces inside <a> tags
    """
    if not text:
        return text

    # 1. Normalize newlines / whitespace inside tags
    text = re.sub(r"</\s*\n\s*([a-zA-Z0-9]+)\s*>", r"</\1>", text)
    text = re.sub(r"<\s*\n\s*([a-zA-Z0-9]+)", r"<\1", text)
    text = re.sub(r"\n\s*(</?(?:a|b|i|u|s|code|pre|blockquote|strong|em)[^>]*>)", r"\1", text)
    text = re.sub(r"(</?(?:a|b|i|u|s|code|pre|blockquote|strong|em)[^>]*>)\s*\n", r"\1", text)

    # 2. Fix <a href=...> without quotes
    text = re.sub(
        r'<a\s+href=([^"\'\s>]+)(\s|>)',
        r'<a href="\1"\2',
        text,
        flags=re.I
    )

    # 3. Remove outer <b> / <strong> around <blockquote> (Telegram forbids this)
    #    <b><blockquote>xxx</blockquote></b>  →  <blockquote>xxx</blockquote>
    text = re.sub(
        r"<(?:b|strong)>\s*<blockquote>(.*?)</blockquote>\s*</(?:b|strong)>",
        r"<blockquote>\1</blockquote>",
        text,
        flags=re.I | re.S
    )

    # 4. Fix leftover broken patterns like:
    #    </blockquote></b><b><blockquote>  or  </blockquote></b>
    text = re.sub(r"</blockquote>\s*</(?:b|strong)>\s*<(?:b|strong)>\s*<blockquote>", "</blockquote>\n<blockquote>", text, flags=re.I)
    text = re.sub(r"</blockquote>\s*</(?:b|strong)>", "</blockquote>", text, flags=re.I)
    text = re.sub(r"<(?:b|strong)>\s*<blockquote>", "<blockquote>", text, flags=re.I)

    # 5. Clean empty bold/italic tags
    text = re.sub(r"<(b|i|u|s|strong|em)>\s*</\1>", "", text, flags=re.I)

    # 6. Ensure <a> content is clean (remove leading/trailing spaces inside)
    text = re.sub(
        r'(<a\s+href="[^"]*">)\s+',
        r'\1',
        text,
        flags=re.I
    )
    text = re.sub(
        r'\s+(</a>)',
        r'\1',
        text,
        flags=re.I
    )

    # 7. Fix double-nested or broken <a> closings
    text = re.sub(r"</a>\s*</a>", "</a>", text, flags=re.I)

    # 8. Remove orphan closing tags (closing without matching open) — safer than adding
    def remove_orphan_closers(src: str, tag: str) -> str:
        result = []
        balance = 0
        pos = 0
        for m in re.finditer(rf"(<{tag}\b[^>]*>|</{tag}>)", src, re.I):
            result.append(src[pos:m.start()])
            tok = m.group(0)
            if tok.lower().startswith("</"):
                if balance > 0:
                    result.append(tok)
                    balance -= 1
                # else: orphan closer → skip
            else:
                result.append(tok)
                balance += 1
            pos = m.end()
        result.append(src[pos:])
        # Close any remaining open tags
        result.append(f"</{tag}>" * balance)
        return "".join(result)

    for tag in ("a", "b", "i", "u", "s", "strong", "em", "blockquote", "code", "pre"):
        text = remove_orphan_closers(text, tag)

    # 9. Final cleanup of consecutive empty lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def strip_html_tags(text: str) -> str:
    """Remove all HTML tags for plain-text fallback. Keep link text + URL readable."""
    if not text:
        return text
    text = re.sub(r'<a\s+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r'\2 (\1)', text, flags=re.I | re.S)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    return text.strip()


def apply_caption_template(template: str, filename: str = "", original: str = "") -> str:
    if not template:
        return original or ""
    name = filename or ""
    name_no_ext = re.sub(r"\.(mp4|mkv|avi|mov|webm|m4v)$", "", name, flags=re.I) if name else ""
    result = template
    for key, val in [
        ("{filename}", name),
        ("{file_name}", name),
        ("{file name}", name),
        ("{name}", name),
        ("{FILE_NAME}", name),
        ("{FILENAME}", name),
        ("{original}", original or ""),
        ("{caption}", original or ""),
        ("{title}", name_no_ext or name),
    ]:
        result = result.replace(key, val)
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
        "3. /caption — set Auto Caption template.\n"
        "   Supports HTML: <a> <b> <blockquote>\n"
        "   Placeholders: {filename} {file_name} {original}\n"
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
        "✅ Auto Caption Template (HTML + plain)\n"
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


async def _build_media(video_id, cover, caption, use_html):
    """Build InputMediaVideo with HTML or plain caption."""
    kwargs = {
        "media": video_id,
        "caption": caption or None,
        "supports_streaming": True,
        "cover": cover,
    }
    if use_html and caption:
        kwargs["parse_mode"] = "HTML"
    return InputMediaVideo(**kwargs)


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
        filename = (update.message.caption or "").split("\n")[0][:80] or "Video"

    font_style = get_font_style(user_id)
    original_caption = update.message.caption or ""
    custom_template = get_custom_caption(user_id)

    if custom_template:
        raw_caption = apply_caption_template(custom_template, filename=filename, original=original_caption)
    else:
        raw_caption = original_caption

    use_html = looks_like_html(raw_caption)

    if use_html:
        new_caption = sanitize_telegram_html(raw_caption)
        parse_mode_html = True
    else:
        new_caption = format_caption(raw_caption, font_style) if raw_caption else ""
        parse_mode_html = False

    dest_chan = get_destination_channel(user_id)
    send_mode = get_send_mode(user_id)

    async def try_edit_media(caption_text, as_html):
        media = await _build_media(video_id, cover, caption_text, as_html)
        await context.bot.edit_message_media(
            chat_id=update.effective_chat.id,
            message_id=status_msg.message_id,
            media=media
        )

    async def try_send_channel(caption_text, as_html):
        dest_chat_id = dest_chan["channel_id"]
        kwargs = {
            "chat_id": dest_chan["channel_id"],
            "video": video_id,
            "caption": caption_text or None,
            "supports_streaming": True,
            "thumbnail": cover,
        }
        if as_html and caption_text:
            kwargs["parse_mode"] = "HTML"
        await context.bot.send_video(**kwargs)

    try:
        sent_to_user = False
        final_caption = new_caption
        final_html = parse_mode_html

        if send_mode in ("both", "user_only") or not dest_chan:
            try:
                await try_edit_media(new_caption, parse_mode_html)
                sent_to_user = True
            except Exception as parse_err:
                err_str = str(parse_err).lower()
                if parse_mode_html and ("parse" in err_str or "entities" in err_str or "tag" in err_str):
                    logger.warning(f"HTML caption failed, trying extra clean: {parse_err}")
                    cleaned2 = sanitize_telegram_html(raw_caption)
                    try:
                        await try_edit_media(cleaned2, True)
                        sent_to_user = True
                        final_caption = cleaned2
                        final_html = True
                    except Exception:
                        logger.warning("Still failed after extra clean, falling back to plain")
                        final_caption = strip_html_tags(raw_caption)
                        final_html = False
                        try:
                            await try_edit_media(final_caption, False)
                            sent_to_user = True
                            await update.message.reply_text(
                                "⚠️ HTML caption me error tha, plain text se bhej diya.\n"
                                "Template thik karo: Settings → Auto Caption → Change",
                                parse_mode="HTML"
                            )
                        except Exception as e2:
                            raise e2
                else:
                    raise parse_err

        dest_success = False
        if dest_chan and send_mode in ("both", "channel_only"):
            try:
                await try_send_channel(final_caption, final_html)
                dest_success = True
            except Exception as chan_err:
                err_str = str(chan_err).lower()
                if final_html and ("parse" in err_str or "entities" in err_str or "tag" in err_str):
                    try:
                        plain = strip_html_tags(raw_caption)
                        await try_send_channel(plain, False)
                        dest_success = True
                    except Exception as e2:
                        logger.error(f"Channel post failed: {e2}")
                        await update.message.reply_text(
                            f"⚠️ Channel post failed:\n<code>{html.escape(str(e2)[:120])}</code>",
                            parse_mode="HTML"
                        )
                else:
                    logger.error(f"Channel post failed: {chan_err}")
                    await update.message.reply_text(
                        f"⚠️ Channel post failed:\n<code>{html.escape(str(chan_err)[:120])}</code>\n\nEnsure bot is Admin with Post Messages.",
                        parse_mode="HTML"
                    )

        if not sent_to_user and dest_success:
            chan_title = html.escape(str(dest_chan.get("channel_title", "Channel")))
            await status_msg.edit_text(f"✅ Video processed!\n\nPosted to: <b>{chan_title}</b>", parse_mode="HTML")
        elif sent_to_user and dest_success:
            chan_title = html.escape(str(dest_chan.get("channel_title", "Channel")))
            await update.message.reply_text(f"📢 Also posted to: <b>{chan_title}</b>", parse_mode="HTML")

        if LOG_CHANNEL_ID:
            try:
                log_caption = (
                    f"🎥 <b>Video Processed</b>\n"
                    f"👤 User: <code>{user_id}</code> (@{html.escape(username)})\n"
                    f"✍️ Font: <code>{html.escape(get_font_name(font_style))}</code>\n"
                    f"📝 Mode: {'HTML' if final_html else 'Plain/Font'}\n"
                    f"📝 Caption: {html.escape((final_caption or 'No Caption')[:80])}"
                )
                await context.bot.send_video(
                    chat_id=LOG_CHANNEL_ID, video=video_id,
                    caption=log_caption, supports_streaming=True,
                    thumbnail=cover, parse_mode="HTML"
                )
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Video processing failed: {e}", exc_info=True)
        try:
            await status_msg.edit_text(
                f"❌ Processing Failed: <code>{html.escape(str(e)[:150])}</code>",
                parse_mode="HTML"
            )
        except Exception:
            await update.message.reply_text(
                f"❌ Processing Failed: <code>{html.escape(str(e)[:150])}</code>",
                parse_mode="HTML"
            )


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

        # Sanitize before save so future videos work
        cleaned = sanitize_telegram_html(raw) if looks_like_html(raw) else raw
        save_custom_caption(user_id, cleaned)
        context.user_data.pop("waiting_for", None)

        is_html = looks_like_html(cleaned)
        preview = html.escape(cleaned[:400])
        mode_note = "🔗 HTML mode (links + bold will work)" if is_html else "✍️ Plain / Font mode"

        text = (
            "✅ <b>Auto Caption Template Saved!</b>\n\n"
            f"{mode_note}\n\n"
            f"<b>Template:</b>\n<code>{preview}</code>\n\n"
            "📌 Placeholders:\n"
            "• <code>{filename}</code> or <code>{file_name}</code> → video name\n"
            "• <code>{original}</code> → original caption\n\n"
            "Ab har video pe ye caption auto lagega."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 View / Edit", callback_data="submenu_caption")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")]
        ])

        # Try delete the old prompt message for cleaner UI
        prompt_id = context.user_data.pop("caption_prompt_msg_id", None)
        if prompt_id:
            try:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=prompt_id)
            except Exception:
                pass

        try:
            return await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Caption save confirm failed: {e}")
            return await update.message.reply_text(
                "✅ Caption template saved!\n\nAb video bhejo — auto apply hoga.",
                reply_markup=kb
            )

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
                    f"⚠️ Bot is not Admin in '{html.escape(chat.title or '')}'\n\nAdd bot as Admin with Post Messages permission.",
                    parse_mode="HTML"
                )
            save_destination_channel(
                user_id=user_id, channel_id=chat.id,
                channel_title=chat.title or "Channel",
                channel_username=chat.username or ""
            )
            context.user_data.pop("waiting_for", None)
            mode_label = "Both" if get_send_mode(user_id) == "both" else (
                "Channel Only" if get_send_mode(user_id) == "channel_only" else "Chat Only"
            )
            text = (
                f"✅ <b>Channel Connected!</b>\n\n"
                f"📢 <b>{html.escape(chat.title or 'Channel')}</b>\n"
                f"🆔 <code>{chat.id}</code>\n"
                f"📤 Mode: <code>{mode_label}</code>"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🧪 Test Post", callback_data="chan_test")],
                [InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")]
            ])
            await verify_msg.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            await verify_msg.edit_text(
                f"❌ Connection failed: <code>{html.escape(str(e)[:120])}</code>",
                parse_mode="HTML"
            )
