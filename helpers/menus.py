"""
Menu and UI Layout Handlers for Ash Cover Bot
"""

import html
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import OWNER_USERNAME
from database import (
    has_thumbnail, get_font_style, get_destination_channel,
    get_send_mode, is_admin, get_custom_caption
)
from font import get_font_name, format_caption, FONT_STYLES

logger = logging.getLogger(__name__)


def get_home_menu_markup(user_id: int) -> InlineKeyboardMarkup:
    kb_rows = [
        [InlineKeyboardButton("❓ Help", callback_data="menu_help"),
         InlineKeyboardButton("ℹ️ About", callback_data="menu_about")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
         InlineKeyboardButton("👨‍💻 Developer", callback_data="menu_developer")]
    ]
    if is_admin(user_id):
        kb_rows.append([InlineKeyboardButton("🛡️ Admin Panel", callback_data="admin_back")])
    return InlineKeyboardMarkup(kb_rows)


def get_home_menu_text() -> str:
    return (
        "<b>Welcome To Ash Cover Bot</b>\n\n"
        "🎬 <b>Professional Video Cover Tool</b>\n\n"
        "⚡ <b>Quick Start:</b>\n\n"
        "📸 <b>Upload Photo</b> — thumbnail saves automatically\n"
        "🎥 <b>Send Video</b> — thumbnail applies instantly\n\n"
        "🌟 <b>Key Features:</b>\n"
        "✅ One-Click Application\n"
        "✅ High-Quality Covers\n"
        "✅ 13+ Caption Font Styles\n"
        "✅ Auto Caption Template\n"
        "✅ Auto-Send To Channel\n\n"
        "💡 <b>Commands:</b>\n"
        "/help /settings /fonts /caption /channel\n\n"
        "📢 Updates: @MoviesGroupG3 | 💬 Support: @movies_1780"
    )


def get_settings_menu(user_id: int):
    thumb_status = "✅ Saved" if has_thumbnail(user_id) else "❌ Not Saved"
    font_key = get_font_style(user_id)
    font_name = get_font_name(font_key)
    dest_chan = get_destination_channel(user_id)
    send_mode = get_send_mode(user_id)
    custom_cap = get_custom_caption(user_id)

    mode_str = "Both (Chat + Channel)" if send_mode == "both" else ("Channel Only" if send_mode == "channel_only" else "Chat Only")
    chan_str = f"✅ {html.escape(str(dest_chan.get('channel_title', 'Channel')))}" if dest_chan else "❌ Not Configured"
    cap_str = "✅ Set" if custom_cap else "❌ Not Set"

    text = (
        "⚙️ <b>Bot Settings & Preferences</b>\n\n"
        f"👤 <b>User ID:</b> <code>{user_id}</code>\n\n"
        f"🖼️ <b>Thumbnail:</b> {thumb_status}\n"
        f"✍️ <b>Caption Font:</b> <code>{html.escape(str(font_name))}</code>\n"
        f"📝 <b>Auto Caption:</b> {cap_str}\n"
        f"📢 <b>Destination Channel:</b> {chan_str}\n"
        f"📤 <b>Delivery Mode:</b> <code>{mode_str}</code>\n\n"
        "Select an option below to configure:"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼 Thumbnail", callback_data="submenu_thumbnails"),
         InlineKeyboardButton("✍️ Caption Font", callback_data="submenu_fonts")],
        [InlineKeyboardButton("📝 Auto Caption", callback_data="submenu_caption")],
        [InlineKeyboardButton("📢 Destination Channel", callback_data="submenu_channel")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu_back")]
    ])
    return text, kb


def get_caption_menu(user_id: int):
    """Build Auto Caption template menu — HTML-safe."""
    custom_cap = get_custom_caption(user_id)
    if custom_cap:
        preview = html.escape(custom_cap[:300])
        if len(custom_cap) > 300:
            preview += "..."
        text = (
            "📝 <b>Auto Caption Template</b>\n\n"
            "✅ <b>Status:</b> Active\n\n"
            "<b>Your Template:</b>\n"
            f"<code>{preview}</code>\n\n"
            "<b>Placeholders:</b>\n"
            "• <code>{{filename}}</code> → video file name\n"
            "• <code>{{original}}</code> → original caption\n\n"
            "💡 Every video pe ye template auto apply hoga + your font."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Change Template", callback_data="cap_set_prompt")],
            [InlineKeyboardButton("🗑️ Remove Caption", callback_data="cap_delete")],
            [InlineKeyboardButton("⬅️ Back To Settings", callback_data="menu_settings")]
        ])
    else:
        text = (
            "📝 <b>Auto Caption Template</b>\n\n"
            "❌ <b>Status:</b> Not Set\n\n"
            "Apna custom caption template save karo.\n"
            "Har video pe ye automatically lag jayega.\n\n"
            "<b>Placeholders:</b>\n"
            "• <code>{{filename}}</code> → video file name\n"
            "• <code>{{original}}</code> → original caption\n\n"
            "<b>Example:</b>\n"
            "<code>{{filename}}\n\n📢 @MoviesGroupG3</code>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Set Caption Template", callback_data="cap_set_prompt")],
            [InlineKeyboardButton("⬅️ Back To Settings", callback_data="menu_settings")]
        ])
    return text, kb


def get_fonts_menu(user_id: int):
    current_font = get_font_style(user_id)
    font_name = get_font_name(current_font)
    sample_preview = format_caption("Movie Name (2024) [1080p Web-DL]", current_font)

    text = (
        "✍️ <b>Caption Font Style</b>\n\n"
        f"<b>Current Font:</b> <code>{html.escape(str(font_name))}</code>\n\n"
        f"<b>Live Preview:</b>\n"
        f"<code>{html.escape(sample_preview)}</code>\n\n"
        "<i>Click any font button below to apply:</i>"
    )

    font_buttons = []
    row = []
    for s in FONT_STYLES:
        is_active = (s["key"] == current_font)
        btn_text = f"✅ {s['name']}" if is_active else s["name"]
        row.append(InlineKeyboardButton(btn_text, callback_data=f"set_font_{s['key']}"))
        if len(row) == 2:
            font_buttons.append(row)
            row = []
    if row:
        font_buttons.append(row)
    font_buttons.append([InlineKeyboardButton("⬅️ Back To Settings", callback_data="menu_settings")])

    return text, InlineKeyboardMarkup(font_buttons)


def get_channel_menu(user_id: int):
    dest_chan = get_destination_channel(user_id)
    send_mode = get_send_mode(user_id)
    mode_label = "Both (Chat + Channel)" if send_mode == "both" else ("Channel Only" if send_mode == "channel_only" else "Private Chat Only")

    if dest_chan:
        chan_id = dest_chan.get("channel_id", "Unknown")
        chan_title = html.escape(str(dest_chan.get("channel_title", "Channel")))
        chan_user = dest_chan.get("channel_username", "") or ""
        user_disp = f" (@{html.escape(chan_user)})" if chan_user else ""

        text = (
            "📢 <b>Destination Channel</b>\n\n"
            f"✅ <b>Status:</b> Connected\n"
            f"📢 <b>Channel:</b> <b>{chan_title}</b>{user_disp}\n"
            f"🆔 <b>ID:</b> <code>{chan_id}</code>\n"
            f"📤 <b>Mode:</b> <code>{mode_label}</code>\n\n"
            "💡 When you send any video, thumbnail + font + caption apply and post here."
        )
        chan_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🔄 Mode: {mode_label}", callback_data="chan_toggle_mode")],
            [InlineKeyboardButton("🧪 Test Connection", callback_data="chan_test"),
             InlineKeyboardButton("🔄 Change Channel", callback_data="chan_set_prompt")],
            [InlineKeyboardButton("🗑️ Remove Channel", callback_data="chan_delete")],
            [InlineKeyboardButton("⬅️ Back To Settings", callback_data="menu_settings")]
        ])
    else:
        text = (
            "📢 <b>Destination Channel</b>\n\n"
            "❌ <b>Status:</b> Not Connected\n\n"
            "Connect your Telegram channel. Videos will auto apply thumbnail, font, caption and post there.\n\n"
            "<b>Quick Setup:</b>\n"
            "1. Add this bot as <b>Admin</b> with <i>Post Messages</i> permission.\n"
            "2. Click the button below to connect."
        )
        chan_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Connect Channel", callback_data="chan_set_prompt")],
            [InlineKeyboardButton("⬅️ Back To Settings", callback_data="menu_settings")]
        ])
    return text, chan_kb
