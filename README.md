# 🎬 Ash Cover Bot

Professional Telegram bot for adding custom covers / thumbnails to videos instantly.

**Owner:** [@movies_1780](https://t.me/movies_1780)  
**Updates:** [@MoviesGroupG3](https://t.me/MoviesGroupG3)

## Features

- 📸 Upload photo as video thumbnail
- ✍️ 13+ caption font styles
- 📢 Destination channel auto-post
- 🔒 Force subscribe
- 👥 Admin panel (ban / unban / stats)
- 💾 MongoDB + in-memory fallback
- 🐳 Docker ready (Render free Web Service compatible)

## Quick Start

```bash
git clone https://github.com/sohebkhatik29-star/Ash-cover-.git
cd Ash-cover-
pip install -r requirements.txt
cp env.example config.env
# edit config.env
python bot.py
```

## Environment

See `env.example`:

- `BOT_TOKEN` – from @BotFather
- `OWNER_ID` – your Telegram user id
- `OWNER_USERNAME` – `movies_1780`
- `FORCE_SUB_CHANNEL_INVITE_LINK` – `https://t.me/MoviesGroupG3`
- `MONGODB_URI` / `MONGODB_DATABASE`
- `LOG_CHANNEL_ID`

## Deploy on Render (Free Web Service)

1. New **Web Service** from this repo
2. Start command: `python bot.py` (or Docker)
3. Set env vars
4. Deploy – health server binds to `PORT` automatically

## Commands

| Command | Description |
|---------|-------------|
| /start | Main menu |
| /help | Guide |
| /settings | Preferences |
| /fonts | Caption fonts |
| /channel | Destination channel |
| /remove | Delete thumbnail |
| /admin | Admin panel |
| /stats | Statistics |

## Support

- Updates: https://t.me/MoviesGroupG3
- Contact: https://t.me/movies_1780
