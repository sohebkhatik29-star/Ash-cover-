"""
MongoDB Database Module for Ash Cover Bot
Handles all database operations for user thumbnails
"""

import os
import logging
from datetime import datetime
from pymongo import MongoClient

logger = logging.getLogger(__name__)

MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.environ.get("MONGODB_DATABASE", "ash_cover_bot")

try:
    mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    db = mongo_client[MONGODB_DATABASE]
    users_collection = db["users"]
    mongo_client.server_info()
    logger.info("✅ MongoDB connected successfully")
    DB_AVAILABLE = True
except Exception as e:
    logger.warning(f"⚠️ MongoDB not available: {e}")
    logger.warning("⚠️ Bot will work with limited functionality (thumbnails won't persist)")
    DB_AVAILABLE = False
    users_collection = None

_memory_cache = {
    "thumbnails": {},
    "font_styles": {},
    "channels": {},
    "send_modes": {},
    "captions": {},
    "banned": {}
}


def save_thumbnail(user_id: int, photo_id: str) -> bool:
    _memory_cache["thumbnails"][user_id] = photo_id
    if not DB_AVAILABLE:
        return True
    try:
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "photo_id": photo_id, "updated_at": datetime.now()}},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"❌ Error saving thumbnail: {e}")
        return False


def get_thumbnail(user_id: int):
    if not DB_AVAILABLE:
        return _memory_cache["thumbnails"].get(user_id)
    try:
        user_record = users_collection.find_one({"user_id": user_id})
        if user_record and "photo_id" in user_record:
            return user_record["photo_id"]
        return _memory_cache["thumbnails"].get(user_id)
    except Exception as e:
        logger.error(f"❌ Error retrieving thumbnail: {e}")
        return _memory_cache["thumbnails"].get(user_id)


def delete_thumbnail(user_id: int) -> bool:
    had_thumb = user_id in _memory_cache["thumbnails"]
    _memory_cache["thumbnails"].pop(user_id, None)
    if not DB_AVAILABLE:
        return had_thumb
    try:
        result = users_collection.update_one({"user_id": user_id}, {"$unset": {"photo_id": ""}})
        return result.modified_count > 0 or had_thumb
    except Exception as e:
        logger.error(f"❌ Error deleting thumbnail: {e}")
        return False


def has_thumbnail(user_id: int) -> bool:
    if user_id in _memory_cache["thumbnails"]:
        return True
    if not DB_AVAILABLE:
        return False
    try:
        user_record = users_collection.find_one({"user_id": user_id})
        return user_record is not None and "photo_id" in user_record
    except Exception:
        return False


def save_font_style(user_id: int, font_style: str) -> bool:
    _memory_cache["font_styles"][user_id] = font_style
    if not DB_AVAILABLE:
        return True
    try:
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "font_style": font_style, "font_updated_at": datetime.now()}},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"❌ Error saving font style: {e}")
        return False


def get_font_style(user_id: int) -> str:
    if user_id in _memory_cache["font_styles"]:
        return _memory_cache["font_styles"][user_id]
    if not DB_AVAILABLE:
        return "bold"
    try:
        user_record = users_collection.find_one({"user_id": user_id})
        if user_record and "font_style" in user_record:
            return user_record["font_style"]
        return "bold"
    except Exception:
        return "bold"


def save_destination_channel(user_id: int, channel_id: str, channel_title: str = "", channel_username: str = "") -> bool:
    channel_data = {
        "channel_id": channel_id,
        "channel_title": channel_title,
        "channel_username": channel_username,
        "set_at": datetime.now().isoformat()
    }
    _memory_cache["channels"][user_id] = channel_data
    if not DB_AVAILABLE:
        return True
    try:
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "destination_channel": channel_data}},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"❌ Error saving destination channel: {e}")
        return False


def get_destination_channel(user_id: int):
    if user_id in _memory_cache["channels"]:
        return _memory_cache["channels"][user_id]
    if not DB_AVAILABLE:
        return None
    try:
        user_record = users_collection.find_one({"user_id": user_id})
        if user_record and "destination_channel" in user_record:
            return user_record["destination_channel"]
        return None
    except Exception:
        return None


def delete_destination_channel(user_id: int) -> bool:
    had_chan = user_id in _memory_cache["channels"]
    _memory_cache["channels"].pop(user_id, None)
    if not DB_AVAILABLE:
        return had_chan
    try:
        result = users_collection.update_one({"user_id": user_id}, {"$unset": {"destination_channel": ""}})
        return result.modified_count > 0 or had_chan
    except Exception:
        return False


def save_send_mode(user_id: int, mode: str) -> bool:
    _memory_cache["send_modes"][user_id] = mode
    if not DB_AVAILABLE:
        return True
    try:
        users_collection.update_one({"user_id": user_id}, {"$set": {"send_mode": mode}}, upsert=True)
        return True
    except Exception:
        return False


def get_send_mode(user_id: int) -> str:
    if user_id in _memory_cache["send_modes"]:
        return _memory_cache["send_modes"][user_id]
    if not DB_AVAILABLE:
        return "both"
    try:
        user_record = users_collection.find_one({"user_id": user_id})
        if user_record and "send_mode" in user_record:
            return user_record["send_mode"]
        return "both"
    except Exception:
        return "both"


def save_custom_caption(user_id: int, custom_caption: str) -> bool:
    _memory_cache["captions"][user_id] = custom_caption
    if not DB_AVAILABLE:
        return True
    try:
        users_collection.update_one({"user_id": user_id}, {"$set": {"custom_caption": custom_caption}}, upsert=True)
        return True
    except Exception:
        return False


def get_custom_caption(user_id: int):
    if user_id in _memory_cache["captions"]:
        return _memory_cache["captions"][user_id]
    if not DB_AVAILABLE:
        return None
    try:
        user_record = users_collection.find_one({"user_id": user_id})
        if user_record and "custom_caption" in user_record:
            return user_record["custom_caption"]
        return None
    except Exception:
        return None


def delete_custom_caption(user_id: int) -> bool:
    had_cap = user_id in _memory_cache["captions"]
    _memory_cache["captions"].pop(user_id, None)
    if not DB_AVAILABLE:
        return had_cap
    try:
        result = users_collection.update_one({"user_id": user_id}, {"$unset": {"custom_caption": ""}})
        return result.modified_count > 0 or had_cap
    except Exception:
        return False


def is_admin(user_id: int) -> bool:
    try:
        from config import ADMIN_ID
        return bool(ADMIN_ID) and int(user_id) == int(ADMIN_ID)
    except Exception:
        return False


def ban_user(user_id: int, reason: str = "No reason") -> bool:
    _memory_cache["banned"][user_id] = True
    if not DB_AVAILABLE:
        return True
    try:
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "is_banned": True, "ban_reason": reason, "banned_at": datetime.now()}},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"❌ Error banning user {user_id}: {e}")
        return False


def unban_user(user_id: int) -> bool:
    _memory_cache["banned"].pop(user_id, None)
    if not DB_AVAILABLE:
        return True
    try:
        result = users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"is_banned": False, "unbanned_at": datetime.now()}}
        )
        return result.modified_count > 0
    except Exception:
        return False


def is_user_banned(user_id: int) -> bool:
    if user_id in _memory_cache["banned"]:
        return True
    if not DB_AVAILABLE:
        return False
    try:
        user_record = users_collection.find_one({"user_id": user_id})
        return bool(user_record and user_record.get("is_banned", False))
    except Exception:
        return False


def get_total_users() -> int:
    if not DB_AVAILABLE:
        return 0
    try:
        return users_collection.count_documents({})
    except Exception:
        return 0


def get_banned_users_count() -> int:
    if not DB_AVAILABLE:
        return 0
    try:
        return users_collection.count_documents({"is_banned": True})
    except Exception:
        return 0


def get_stats() -> dict:
    if not DB_AVAILABLE:
        return {"total_users": 0, "banned_users": 0, "active_users": 0, "users_with_thumbnail": 0, "total_thumbnails": 0}
    try:
        total = users_collection.count_documents({})
        banned = users_collection.count_documents({"is_banned": True})
        with_thumb = users_collection.count_documents({"photo_id": {"$exists": True}})
        return {
            "total_users": total,
            "banned_users": banned,
            "active_users": max(0, total - banned),
            "users_with_thumbnail": with_thumb,
            "total_thumbnails": with_thumb
        }
    except Exception:
        return {"total_users": 0, "banned_users": 0, "active_users": 0, "users_with_thumbnail": 0, "total_thumbnails": 0}


def create_log_entry(user_id: int, username: str, action: str, details: str = "") -> dict:
    return {
        "user_id": user_id,
        "username": f"@{username}" if username else "Unknown",
        "action": action,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }


def format_log_message(user_id: int, username: str, action: str, details: str = "") -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    username_str = f"@{username}" if username else "Unknown"
    log_msg = (
        f"📝 <b>{action}</b>\n\n"
        f"👤 User ID: <code>{user_id}</code>\n"
        f"📌 Username: {username_str}\n"
        f"⏰ Time: {now}\n"
    )
    if details:
        log_msg += f"📋 Details: {details}\n"
    return log_msg


def log_new_user(user_id: int, username: str, first_name: str) -> dict:
    return create_log_entry(user_id, username, "🆕 New User Started Bot", f"Name: {first_name}")


def log_user_banned(user_id: int, username: str, reason: str) -> dict:
    return create_log_entry(user_id, username, "🚫 User Banned", f"Reason: {reason}")


def log_user_unbanned(user_id: int, username: str) -> dict:
    return create_log_entry(user_id, username, "✅ User Unbanned")


def log_thumbnail_set(user_id: int, username: str, is_replace: bool = False) -> dict:
    action = "🖼 Thumbnail Replaced" if is_replace else "🖼 Thumbnail Set"
    return create_log_entry(user_id, username, action)


def log_thumbnail_removed(user_id: int, username: str) -> dict:
    return create_log_entry(user_id, username, "🗑️ Thumbnail Removed")
