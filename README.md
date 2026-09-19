# Telegram Media Downloader Bot

A Telegram bot that downloads media (YouTube, Facebook, Spotify, Terabox) and
sends the actual file directly in Telegram — up to 2 GB — using Pyrogram
(MTProto, via `api_id` + `api_hash`), so no Local Bot API Server is needed.

## Features

- **YouTube** — send a link, choose 🎥 MP4 or 🎵 MP3 via buttons
- **Instagram** — send a reel/post link, the video/photo is downloaded and sent automatically (only one quality is provided by the API, so no buttons needed)
- **Facebook** — send a link, choose 🔴 HD or ⚪ SD via buttons
- **Spotify** — track or album links; lets you pick a track and get a
  30-second preview clip (Spotify does not allow full-song downloads via
  public APIs)
- **Terabox** — send a link, choose ⬇️ Downloader (sends the actual file) or
  ▶️ Stream (sends the HLS stream link for external players)
## 1. Requirements

- Python 3.9+
- `ffmpeg` installed on the system (needed for Terabox files that come as
  `.m3u8` HLS streams)

```bash
# Ubuntu / Debian
sudo apt update && sudo apt install ffmpeg -y
```

## 2. Install dependencies

```bash
cd telegram-media-bot
pip install -r requirements.txt
```

## 3. Get your credentials

1. **api_id + api_hash** — go to https://my.telegram.org, log in, open
   "API development tools", create an app, copy the `api_id` and `api_hash`.
2. **Bot token** — open Telegram, chat with **@BotFather**, send `/newbot`,
   follow the steps, copy the token it gives you.

## 4. Configure

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```
API_ID=1234567
API_HASH=your_api_hash_here
BOT_TOKEN=your_bot_token_here
```

## 5. Run the bot

```bash
python bot.py
```

If everything is correct, you'll see `Starting Media Downloader Bot...` in
the terminal, and the bot will respond to `/start` on Telegram.

## Project structure

```
telegram-media-bot/
├── bot.py                # Main bot: handlers, callbacks, routing
├── config.py             # Credentials + API endpoints
├── utils.py              # File download helpers (direct + HLS via ffmpeg)
├── keyboards.py          # Inline button layouts
├── services/
│   ├── youtube.py
│   ├── instagram.py
│   ├── facebook.py
│   ├── spotify.py
│   └── terabox.py
├── requirements.txt
├── .env.example
└── downloads/            # Temporary storage, auto-cleaned after each send
```

## Notes / limitations

- **Spotify**: only 30-second preview clips are sent — this is a limitation
  of the public API used, not the bot itself.
- **Terabox "Stream"**: Telegram cannot play `.m3u8` links natively, so the
  bot sends the raw stream URL for you to open in VLC, MX Player, etc.
  "Downloader" instead downloads and converts the stream into a normal
  `.mp4` file using ffmpeg before sending it.
- **Session cache**: the bot keeps API results in memory (`SESSION_CACHE`)
  between the link message and the button click. If the bot restarts before
  you tap a button, you'll need to resend the link.
- **2 GB limit**: this is Telegram's own limit for bot uploads via MTProto
  (Pyrogram). It's a platform limit, not something the bot can increase further.
