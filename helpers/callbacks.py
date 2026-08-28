"""
Callback Query Dispatcher & Handlers for Ash Cover Bot
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import OWNER_USERNAME
from database import (
    get_thumbnail, delete_thumbnail,
    save_font_style, get_destination_channel,
    delete_destination_channel, save_send_mode, get_send_mode,
    delete_custom_caption,
    is_admin, get_total_users, get_banned_users_count
)
from font import get_font_name
from helpers.menus import (
    get_home_menu_text, get_home_menu_markup,
    get_settings_menu, get_fonts_menu, get_channel_menu, get_caption_menu
)

logger = logging.getLogger(__name__)


async def _safe_edit(query, text, kb):
    """Edit message safely; if edit fails, send a new message."""
    try:
        if getattr(query.message, "photo", None):
            await query.message.edit_caption(caption=text, reply_markup=kb, parse_mode="HTML")
        else:
            await query.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        return True
    except Exception as e:
        logger.debug(f"Edit failed, sending new message: {e}")
        try:
            await query.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
            return True
        except Exception as e2:
            logger.error(f"Reply also failed: {e2}")
            return False


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main callback query router"""
    query = update.callback_query
    data = query.data or ""
    uid = query.from_user.id

    try:
        await query.answer()
    except Exception:
        pass

    if data in ("menu_back", "menu_home"):
        text = get_home_menu_text()
        kb = get_home_menu_markup(uid)
        await _safe_edit(query, text, kb)
        return

    if data.startswith("menu_"):
        key = data.replace("menu_", "")

        if key == "help":
            text = (
                "📖 <b>𝐂ᴏᴍᴘʟᴇᴛᴇ 𝐆ᴜɪᴅᴇ & 𝐅ᴇᴀᴛᴜʀᴇs</b>\n\n"
                "1️⃣ <b>𝐔ᴘʟᴏᴀᴅ 𝐂ᴏᴠᴇʀ:</b> 𝐒ᴇɴᴅ ᴀɴʏ ᴘʜᴏᴛᴏ ᴛᴏ sᴇᴛ ᴀs ᴛʜᴜᴍʙɴᴀɪʟ.\n"
                "2️⃣ <b>𝐂ᴀᴘᴛɪᴏɴ 𝐅ᴏɴᴛ:</b> 𝐏ɪᴄᴋ ᴀ sᴛʏʟɪsʜ ꜰᴏɴᴛ ꜰʀᴏᴍ /fonts.\n"
                "3️⃣ <b>𝐀ᴜᴛᴏ 𝐂ᴀᴘᴛɪᴏɴ:</b> 𝐒ᴇᴛᴛɪɴɢs → 𝐀ᴜᴛᴏ 𝐂ᴀᴘᴛɪᴏɴ (use {filename}).\n"
                "4️⃣ <b>𝐃ᴇsᴛɪɴᴀᴛɪᴏɴ 𝐂ʜᴀɴɴᴇʟ:</b> 𝐋ɪɴᴋ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴠɪᴀ /channel.\n"
                "5️⃣ <b>𝐀ᴘᴘʟʏ:</b> 𝐒ᴇɴᴅ ᴀɴʏ ᴠɪᴅᴇᴏ — ᴛʜᴜᴍʙɴᴀɪʟ & ᴄᴀᴘᴛɪᴏɴ ᴀᴘᴘʟʏ ɪɴsᴛᴀɴᴛʟʏ!\n\n"
                "📢 <b>𝐔ᴘᴅᴀᴛᴇs 𝐂ʜᴀɴɴᴇʟ:</b> @MoviesGroupG3\n"
                "👤 <b>𝐎ᴡɴᴇʀ:</b> @movies_1780\n"
                "💬 <b>𝐒ᴜᴘᴘᴏʀᴛ & 𝐃ᴏᴜʙᴛs:</b> @movies_1780"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 𝐔ᴘᴅᴀᴛᴇs", url="https://t.me/MoviesGroupG3"),
                 InlineKeyboardButton("👤 𝐎ᴡɴᴇʀ", url="https://t.me/movies_1780")],
                [InlineKeyboardButton("💬 𝐒ᴜᴘᴘᴏʀᴛ", url="https://t.me/movies_1780")],
                [InlineKeyboardButton("⬅️ 𝐁ᴀᴄᴋ", callback_data="menu_back")]
            ])
        elif key == "about":
            text = (
                "🤖 <b>𝐀ʙᴏᴜᴛ 𝐓ʜɪs 𝐁ᴏᴛ</b>\n\n"
                "✨ <b>𝐅ᴀsᴛᴇsᴛ 𝐕ɪᴅᴇᴏ 𝐂ᴏᴠᴇʀ & 𝐂ᴀᴘᴛɪᴏɴ 𝐒ᴛʏʟᴇʀ 𝐁ᴏᴛ</b>\n"
                "• 𝐒ᴜᴘᴘᴏʀᴛs ʜɪɢʜ sᴘᴇᴇᴅ ᴠɪᴅᴇᴏ ᴘʀᴏᴄᴇssɪɴɢ\n"
                "• 𝟏𝟑+ 𝐂ᴀᴘᴛɪᴏɴ 𝐔ɴɪᴄᴏᴅᴇ 𝐅ᴏɴᴛ 𝐒ᴛʏʟᴇs\n"
                "• 𝐀ᴜᴛᴏ 𝐂ᴀᴘᴛɪᴏɴ 𝐓ᴇᴍᴘʟᴀᴛᴇ ({filename})\n"
                "• 𝐀ᴜᴛᴏᴍᴀᴛᴇᴅ 𝐃ᴇsᴛɪɴᴀᴛɪᴏɴ 𝐂ʜᴀɴɴᴇʟ 𝐅ᴏʀᴡᴀʀᴅɪɴɢ\n\n"
                "📢 <b>𝐔ᴘᴅᴀᴛᴇs 𝐂ʜᴀɴɴᴇʟ:</b> @MoviesGroupG3\n"
                "👤 <b>𝐎ᴡɴᴇʀ:</b> @movies_1780\n"
                "💬 <b>𝐀sᴋ 𝐃ᴏᴜʙᴛ 𝐂ᴏɴᴛᴀᴄᴛ:</b> @movies_1780"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 𝐔ᴘᴅᴀᴛᴇs", url="https://t.me/MoviesGroupG3"),
                 InlineKeyboardButton("👤 𝐎ᴡɴᴇʀ", url="https://t.me/movies_1780")],
                [InlineKeyboardButton("💬 𝐂ᴏɴᴛᴀᴄᴛ", url="https://t.me/movies_1780")],
                [InlineKeyboardButton("⬅️ 𝐁ᴀᴄᴋ", callback_data="menu_back")]
            ])
        elif key == "developer":
            text = (
                "👨‍💻 <b>𝐃ᴇᴠᴇʟᴏᴘᴇʀ & 𝐒ᴜᴘᴘᴏʀᴛ</b>\n\n"
                "📢 <b>𝐓ᴇʟᴇɢʀᴀᴍ 𝐂ʜᴀɴɴᴇʟ:</b> @MoviesGroupG3\n"
                "👤 <b>𝐎ᴡɴᴇʀ:</b> @movies_1780\n"
                "💬 <b>𝐀sᴋ 𝐃ᴏᴜʙᴛ 𝐂ᴏɴᴛᴀᴄᴛ:</b> @movies_1780\n\n"
                "<i>𝐅ᴇᴇʟ ꜰʀᴇᴇ ᴛᴏ ᴄᴏɴᴛᴀᴄᴛ ᴜs ꜰᴏʀ ǫᴜᴇʀɪᴇs, ᴜᴘᴅᴀᴛᴇs, ᴀɴᴅ ᴄᴜsᴛᴏᴍ ʙᴏᴛs!</i>"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 𝐉ᴏɪɴ 𝐂ʜᴀɴɴᴇʟ", url="https://t.me/MoviesGroupG3"),
                 InlineKeyboardButton("👤 𝐎ᴡɴᴇʀ", url="https://t.me/movies_1780")],
                [InlineKeyboardButton("💬 𝐂ᴏɴᴛᴀᴄᴛ 𝐌ᴇ", url="https://t.me/movies_1780")],
                [InlineKeyboardButton("⬅️ 𝐁ᴀᴄᴋ", callback_data="menu_back")]
            ])
        elif key == "settings":
            text, kb = get_settings_menu(uid)
        else:
            return

        await _safe_edit(query, text, kb)
        return

    if data == "submenu_fonts" or data.startswith("set_font_"):
        if data.startswith("set_font_"):
            chosen_font = data.replace("set_font_", "")
            save_font_style(uid, chosen_font)
            try:
                await query.answer(f"✅ Font set to {get_font_name(chosen_font)}", show_alert=False)
            except Exception:
                pass
        text, kb = get_fonts_menu(uid)
        await _safe_edit(query, text, kb)
        return

    # --- Auto Caption ---
    if data == "submenu_caption":
        text, kb = get_caption_menu(uid)
        await _safe_edit(query, text, kb)
        return

    if data == "cap_set_prompt":
        context.user_data["waiting_for"] = "custom_caption"
        text = (
            "📝 <b>𝐒ᴇᴛ 𝐀ᴜᴛᴏ 𝐂ᴀᴘᴛɪᴏɴ 𝐓ᴇᴍᴘʟᴀᴛᴇ</b>\n\n"
            "𝐀ᴘɴᴀ ᴄᴀᴘᴛɪᴏɴ ᴛᴇᴍᴘʟᴀᴛᴇ ʟɪᴋʜ ᴋᴀʀ ʙʜᴇᴊᴏ.\n\n"
            "<b>📌 Placeholders:</b>\n"
            "• <code>{filename}</code> → Video file name\n"
            "• <code>{original}</code> → Original caption\n\n"
            "<b>📌 Example:</b>\n"
            "<code>{filename}\n\n📢 @MoviesGroupG3</code>\n\n"
            "Ya:\n"
            "<code>🎬 {filename}\n{original}\n\n🔗 Join @MoviesGroupG3</code>\n\n"
            "👇 <i>Abhi template bhejo (ya /cancel):</i>"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="submenu_caption")]])
        await _safe_edit(query, text, kb)
        return

    if data == "cap_delete":
        delete_custom_caption(uid)
        try:
            await query.answer("🗑️ Auto Caption removed!", show_alert=False)
        except Exception:
            pass
        text, kb = get_caption_menu(uid)
        await _safe_edit(query, text, kb)
        return

    if data == "submenu_channel":
        text, kb = get_channel_menu(uid)
        await _safe_edit(query, text, kb)
        return

    if data == "chan_set_prompt":
        context.user_data["waiting_for"] = "destination_channel"
        text = (
            "📢 <b>𝐂ᴏɴɴᴇᴄᴛ 𝐘ᴏᴜʀ 𝐃ᴇsᴛɪɴᴀᴛɪᴏɴ 𝐂ʜᴀɴɴᴇʟ</b>\n\n"
            "<b>1.</b> 𝐀ᴅᴅ ᴛʜɪs ʙᴏᴛ ᴀs ᴀɴ <b>𝐀ᴅᴍɪɴ</b> ɪɴ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴡɪᴛʜ <i>𝐏ᴏsᴛ 𝐌ᴇssᴀɢᴇs</i> ᴘᴇʀᴍɪssɪᴏɴ.\n"
            "<b>2.</b> 𝐒ᴇɴᴅ ᴍᴇ ᴛʜᴇ <b>𝐂ʜᴀɴɴᴇʟ 𝐈𝐃</b>, <b>@username</b>, ᴏʀ <b>ꜰᴏʀᴡᴀʀᴅ ᴀɴʏ ᴍᴇssᴀɢᴇ</b> ꜰʀᴏᴍ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟ.\n\n"
            "👇 <i>𝐒ᴇɴᴅ ᴄʜᴀɴɴᴇʟ ᴅᴇᴛᴀɪʟs ɴᴏᴡ:</i>"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ 𝐂ᴀɴᴄᴇʟ", callback_data="submenu_channel")]])
        await _safe_edit(query, text, kb)
        return

    if data == "chan_toggle_mode":
        current = get_send_mode(uid)
        next_mode = "channel_only" if current == "both" else ("user_only" if current == "channel_only" else "both")
        save_send_mode(uid, next_mode)
        mode_label = "📤 𝐁ᴏᴛʜ" if next_mode == "both" else ("📢 𝐂ʜᴀɴɴᴇʟ 𝐎ɴʟʏ" if next_mode == "channel_only" else "👤 𝐂ʜᴀᴛ 𝐎ɴʟʏ")
        try:
            await query.answer(f"✅ Mode: {mode_label}", show_alert=False)
        except Exception:
            pass
        text, kb = get_channel_menu(uid)
        await _safe_edit(query, text, kb)
        return

    if data == "chan_test":
        dest_chan = get_destination_channel(uid)
        if not dest_chan:
            try:
                await query.answer("❌ No channel connected!", show_alert=True)
            except Exception:
                pass
            return
        chan_id = dest_chan.get("channel_id")
        try:
            await context.bot.send_message(
                chat_id=chan_id,
                text=(
                    "🧪 <b>𝐀sʜ 𝐂ᴏᴠᴇʀ 𝐁ᴏᴛ 𝐂ᴏɴɴᴇᴄᴛɪᴏɴ 𝐓ᴇsᴛ</b>\n\n"
                    "✅ <b>𝐘ᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴄᴏɴɴᴇᴄᴛɪᴏɴ ɪs ᴡᴏʀᴋɪɴɢ ᴘᴇʀꜰᴇᴄᴛʟʏ!</b>\n\n"
                    "📢 <b>𝐔ᴘᴅᴀᴛᴇs:</b> @MoviesGroupG3 | 👤 <b>𝐎ᴡɴᴇʀ:</b> @movies_1780"
                ),
                parse_mode="HTML"
            )
            await query.answer("✅ Test post successful! Check your channel.", show_alert=True)
        except Exception as e:
            try:
                await query.answer(f"❌ Failed: {str(e)[:80]}\nBot must be Admin with Post Messages!", show_alert=True)
            except Exception:
                pass
        return

    if data == "chan_delete":
        delete_destination_channel(uid)
        try:
            await query.answer("🗑️ Channel removed!", show_alert=False)
        except Exception:
            pass
        text, kb = get_channel_menu(uid)
        await _safe_edit(query, text, kb)
        return

    if data == "submenu_thumbnails":
        thumb = get_thumbnail(uid)
        if thumb:
            text = "🖼️ <b>𝐘ᴏᴜʀ 𝐒ᴀᴠᴇᴅ 𝐓ʜᴜᴍʙɴᴀɪʟ</b>\n\n✅ <b>𝐀ᴄᴛɪᴠᴇ ᴀɴᴅ ʀᴇᴀᴅʏ ᴛᴏ ᴀᴘᴘʟʏ.</b>"
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑️ 𝐃ᴇʟᴇᴛᴇ 𝐓ʜᴜᴍʙɴᴀɪʟ", callback_data="thumb_delete")],
                [InlineKeyboardButton("⬅️ 𝐁ᴀᴄᴋ 𝐓ᴏ 𝐒ᴇᴛᴛɪɴɢs", callback_data="menu_settings")]
            ])
            try:
                await query.message.reply_photo(photo=thumb, caption=text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                await _safe_edit(query, text, kb)
        else:
            text = "🖼️ <b>𝐍ᴏ 𝐓ʜᴜᴍʙɴᴀɪʟ 𝐒ᴀᴠᴇᴅ</b>\n\n𝐒ᴇɴᴅ ᴀɴʏ ᴘʜᴏᴛᴏ ᴛᴏ ᴛʜɪs ᴄʜᴀᴛ ᴛᴏ sᴀᴠᴇ ɪᴛ ᴀs ʏᴏᴜʀ ᴠɪᴅᴇᴏ ᴛʜᴜᴍʙɴᴀɪʟ."
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 𝐁ᴀᴄᴋ 𝐓ᴏ 𝐒ᴇᴛᴛɪɴɢs", callback_data="menu_settings")]])
            await _safe_edit(query, text, kb)
        return

    if data == "thumb_delete":
        delete_thumbnail(uid)
        try:
            await query.answer("🗑️ Thumbnail deleted!", show_alert=False)
        except Exception:
            pass
        text, kb = get_settings_menu(uid)
        await _safe_edit(query, text, kb)
        return

    if data.startswith("admin_"):
        if not is_admin(uid):
            try:
                await query.answer("❌ Unauthorized", show_alert=True)
            except Exception:
                pass
            return
        if data == "admin_stats":
            total = get_total_users()
            banned = get_banned_users_count()
            active = total - banned
            text = (
                "📊 <b>𝐁ᴏᴛ 𝐒ᴛᴀᴛɪsᴛɪᴄs</b>\n\n"
                f"👥 <b>𝐓ᴏᴛᴀʟ 𝐔sᴇʀs:</b> <code>{total}</code>\n"
                f"✅ <b>𝐀ᴄᴛɪᴠᴇ:</b> <code>{active}</code>\n"
                f"🚫 <b>𝐁ᴀɴɴᴇᴅ:</b> <code>{banned}</code>"
            )
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 𝐁ᴀᴄᴋ", callback_data="admin_back")]])
            await _safe_edit(query, text, kb)
        elif data == "admin_back":
            total = get_total_users()
            banned = get_banned_users_count()
            text = (
                "🛡️ <b>𝐀ᴅᴍɪɴ 𝐂ᴏɴᴛʀᴏʟ 𝐏ᴀɴᴇʟ</b>\n\n"
                f"📊 <b>𝐔sᴇʀs:</b> <code>{total}</code> | 🚫 <b>𝐁ᴀɴɴᴇᴅ:</b> <code>{banned}</code>"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 𝐒ᴛᴀᴛs", callback_data="admin_stats")],
                [InlineKeyboardButton("⬅️ 𝐂ʟᴏsᴇ 𝐏ᴀɴᴇʟ", callback_data="menu_back")]
            ])
            await _safe_edit(query, text, kb)
        return
