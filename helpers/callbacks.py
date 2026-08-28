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
    query = update.callback_query
    data = query.data or ""
    uid = query.from_user.id

    try:
        await query.answer()
    except Exception:
        pass

    try:
        if data in ("menu_back", "menu_home"):
            text = get_home_menu_text()
            kb = get_home_menu_markup(uid)
            await _safe_edit(query, text, kb)
            return

        if data.startswith("menu_"):
            key = data.replace("menu_", "")

            if key == "help":
                text = (
                    "📖 <b>Complete Guide & Features</b>\n\n"
                    "1. <b>Upload Cover:</b> Send any photo to set as thumbnail.\n"
                    "2. <b>Caption Font:</b> Pick a stylish font from /fonts.\n"
                    "3. <b>Auto Caption:</b> Settings → Auto Caption (use {filename}).\n"
                    "4. <b>Destination Channel:</b> Link your channel via /channel.\n"
                    "5. <b>Apply:</b> Send any video — thumbnail & caption apply instantly!\n\n"
                    "📢 <b>Updates Channel:</b> @MoviesGroupG3\n"
                    "👤 <b>Owner:</b> @movies_1780\n"
                    "💬 <b>Support:</b> @movies_1780"
                )
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 Updates", url="https://t.me/MoviesGroupG3"),
                     InlineKeyboardButton("👤 Owner", url="https://t.me/movies_1780")],
                    [InlineKeyboardButton("⬅️ Back", callback_data="menu_back")]
                ])
            elif key == "about":
                text = (
                    "🤖 <b>About This Bot</b>\n\n"
                    "✨ Fastest Video Cover & Caption Styler Bot\n"
                    "• High speed video processing\n"
                    "• 13+ Caption Unicode Font Styles\n"
                    "• Auto Caption Template (HTML supported)\n"
                    "• Automated Destination Channel Forwarding\n\n"
                    "📢 @MoviesGroupG3 | 👤 @movies_1780"
                )
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 Updates", url="https://t.me/MoviesGroupG3"),
                     InlineKeyboardButton("👤 Owner", url="https://t.me/movies_1780")],
                    [InlineKeyboardButton("⬅️ Back", callback_data="menu_back")]
                ])
            elif key == "developer":
                text = (
                    "👨‍💻 <b>Developer & Support</b>\n\n"
                    "📢 Telegram Channel: @MoviesGroupG3\n"
                    "👤 Owner: @movies_1780\n"
                    "💬 Contact: @movies_1780\n\n"
                    "<i>Feel free to contact for queries, updates, and custom bots!</i>"
                )
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 Join Channel", url="https://t.me/MoviesGroupG3"),
                     InlineKeyboardButton("👤 Owner", url="https://t.me/movies_1780")],
                    [InlineKeyboardButton("⬅️ Back", callback_data="menu_back")]
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
                "📝 <b>Set Auto Caption Template</b>\n\n"
                "Apna caption template likh kar bhejo.\n\n"
                "<b>📌 Placeholders:</b>\n"
                "• <code>{filename}</code> or <code>{file_name}</code> → Video file name\n"
                "• <code>{original}</code> → Original caption\n\n"
                "<b>📌 Plain example:</b>\n"
                "<code>{filename}\n\n📢 @MoviesGroupG3</code>\n\n"
                "<b>📌 HTML example (copy exactly):</b>\n"
                "<code>&lt;a href=\"https://t.me/sky_movies_0\"&gt;&lt;b&gt;{file_name}&lt;/b&gt;&lt;/a&gt;\n\n"
                "&lt;blockquote&gt;Powered By ➥ &lt;a href=\"https://t.me/MoviesGroupG3\"&gt;UPDATE CHANNEL&lt;/a&gt;&lt;/blockquote&gt;\n"
                "&lt;blockquote&gt;Powered By ➥ &lt;a href=\"https://t.me/+5Ev6MbE3WSM3YmM1\"&gt;@MOVIE REQUEST GROUP&lt;/a&gt;&lt;/blockquote&gt;\n"
                "🤗</code>\n\n"
                "👇 <i>Abhi template bhejo (ya /cancel):</i>"
            )
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="submenu_caption")]])
            ok = await _safe_edit(query, text, kb)
            # Save prompt message id so we can delete it after save
            try:
                context.user_data["caption_prompt_msg_id"] = query.message.message_id
            except Exception:
                pass
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
                "📢 <b>Connect Your Destination Channel</b>\n\n"
                "<b>1.</b> Add this bot as an <b>Admin</b> in your channel with <i>Post Messages</i> permission.\n"
                "<b>2.</b> Send me the <b>Channel ID</b>, <b>@username</b>, or <b>forward any message</b> from your channel.\n\n"
                "👇 <i>Send channel details now:</i>"
            )
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="submenu_channel")]])
            await _safe_edit(query, text, kb)
            return

        if data == "chan_toggle_mode":
            current = get_send_mode(uid)
            next_mode = "channel_only" if current == "both" else ("user_only" if current == "channel_only" else "both")
            save_send_mode(uid, next_mode)
            mode_label = "📤 Both" if next_mode == "both" else ("📢 Channel Only" if next_mode == "channel_only" else "👤 Chat Only")
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
                        "🧪 <b>Ash Cover Bot Connection Test</b>\n\n"
                        "✅ Your channel connection is working perfectly!\n\n"
                        "📢 Updates: @MoviesGroupG3 | 👤 Owner: @movies_1780"
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
                text = "🖼️ <b>Your Saved Thumbnail</b>\n\n✅ Active and ready to apply."
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🗑️ Delete Thumbnail", callback_data="thumb_delete")],
                    [InlineKeyboardButton("⬅️ Back To Settings", callback_data="menu_settings")]
                ])
                try:
                    await query.message.reply_photo(photo=thumb, caption=text, reply_markup=kb, parse_mode="HTML")
                except Exception:
                    await _safe_edit(query, text, kb)
            else:
                text = "🖼️ <b>No Thumbnail Saved</b>\n\nSend any photo to this chat to save it as your video thumbnail."
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back To Settings", callback_data="menu_settings")]])
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
                    "📊 <b>Bot Statistics</b>\n\n"
                    f"👥 <b>Total Users:</b> <code>{total}</code>\n"
                    f"✅ <b>Active:</b> <code>{active}</code>\n"
                    f"🚫 <b>Banned:</b> <code>{banned}</code>"
                )
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]])
                await _safe_edit(query, text, kb)
            elif data == "admin_back":
                total = get_total_users()
                banned = get_banned_users_count()
                text = (
                    "🛡️ <b>Admin Control Panel</b>\n\n"
                    f"📊 <b>Users:</b> <code>{total}</code> | 🚫 <b>Banned:</b> <code>{banned}</code>"
                )
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
                    [InlineKeyboardButton("⬅️ Close Panel", callback_data="menu_back")]
                ])
                await _safe_edit(query, text, kb)
            return

    except Exception as e:
        logger.error(f"Callback error for data={data}: {e}", exc_info=True)
        try:
            await query.answer(f"Error: {str(e)[:100]}", show_alert=True)
        except Exception:
            pass
