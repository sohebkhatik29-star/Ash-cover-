"""
Telegram Instant Video Cover Bot - Ash Cover Bot
Clean, Modular Main Entrypoint
"""

import logging
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters
)
from telegram import BotCommand

from config import BOT_TOKEN, LOG_CHANNEL_ID
from helpers.forcesub import check_force_sub
from helpers.callbacks import handle_callback_query
from helpers.admin import admin_panel_cmd, ban_cmd, unban_cmd, stats_cmd
from helpers.handlers import (
    start_cmd, help_cmd, about_cmd, settings_cmd, fonts_cmd,
    caption_cmd, channel_cmd, remove_thumbnail_cmd, photo_handler, video_handler,
    text_and_channel_handler
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Ash Cover Bot is running")

    def log_message(self, format, *args):
        return


def start_health_server():
    port = int(os.environ.get("PORT", "10000"))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        logger.info(f"✅ Health server listening on port {port}")
        server.serve_forever()
    except Exception as e:
        logger.warning(f"Health server failed to start: {e}")


def wrap_sub(handler_fn):
    async def wrapper(update, context):
        waiting = context.user_data.get("waiting_for")
        if waiting in ("custom_caption", "destination_channel"):
            return await handler_fn(update, context)
        if not await check_force_sub(update, context):
            return
        return await handler_fn(update, context)
    return wrapper


async def post_init(application):
    try:
        commands = [
            BotCommand("start", "Start Bot & Main Menu"),
            BotCommand("help", "Complete Guide"),
            BotCommand("settings", "Bot Preferences"),
            BotCommand("fonts", "Caption Font Style"),
            BotCommand("caption", "Auto Caption Template"),
            BotCommand("channel", "Destination Channel"),
            BotCommand("remove", "Remove Saved Cover"),
            BotCommand("about", "About & Credits"),
            BotCommand("admin", "Admin Panel"),
            BotCommand("stats", "Bot Stats"),
        ]
        await application.bot.set_my_commands(commands)
        logger.info("✅ Bot commands registered")

        if LOG_CHANNEL_ID:
            try:
                await application.bot.send_message(
                    chat_id=LOG_CHANNEL_ID,
                    text="🚀 <b>Ash Cover Bot Started!</b>\n📢 @MoviesGroupG3 | 💬 @movies_1780",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Post init error: {e}")


def main():
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN missing!")
        sys.exit(1)

    print("=" * 50)
    print("🚀 Ash Cover Bot Starting...")
    print("📢 @MoviesGroupG3 | 💬 @movies_1780")
    print("=" * 50)

    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", wrap_sub(start_cmd), filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("help", wrap_sub(help_cmd), filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("about", wrap_sub(about_cmd), filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("settings", wrap_sub(settings_cmd), filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler(["fonts", "font"], wrap_sub(fonts_cmd), filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler(["caption", "captions"], wrap_sub(caption_cmd), filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler(["channel", "channels"], wrap_sub(channel_cmd), filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler(["remove", "delete"], wrap_sub(remove_thumbnail_cmd), filters=filters.ChatType.PRIVATE))

    app.add_handler(CommandHandler("admin", admin_panel_cmd, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("ban", ban_cmd, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("unban", unban_cmd, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("stats", stats_cmd, filters=filters.ChatType.PRIVATE))

    app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, wrap_sub(photo_handler)))
    app.add_handler(MessageHandler(filters.VIDEO & filters.ChatType.PRIVATE, wrap_sub(video_handler)))
    app.add_handler(MessageHandler(filters.Document.VIDEO & filters.ChatType.PRIVATE, wrap_sub(video_handler)))

    app.add_handler(MessageHandler(filters.FORWARDED & filters.ChatType.PRIVATE, wrap_sub(text_and_channel_handler)))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, wrap_sub(text_and_channel_handler)))

    app.add_handler(CallbackQueryHandler(handle_callback_query))

    logger.info("✅ All handlers registered. Bot listening...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
