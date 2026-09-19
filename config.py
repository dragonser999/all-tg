import os
from dotenv import load_dotenv

load_dotenv()

# ---- Telegram credentials ----
# API_ID / API_HASH: from https://my.telegram.org
# BOT_TOKEN: from @BotFather
# Using api_id + api_hash (MTProto, via Pyrogram) lets the bot upload files
# up to 2 GB directly, without needing a self-hosted Local Bot API Server.
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Local folder used to temporarily store files before uploading them to Telegram
DOWNLOAD_DIR = "downloads"

# ---- External download APIs (provided by the user) ----
YOUTUBE_API = "https://yt-api-s2tl.vercel.app/api/yt-download?url={url}"
FACEBOOK_API = "https://fb-api-cyan.vercel.app/api/fb-download?url={url}"
SPOTIFY_API = "https://spotify-api-five-beige.vercel.app/api/spotify-download?url={url}"
TERABOX_API = "https://terabox-api-psi-navy.vercel.app/api/terabox-download?url={url}"

INSTAGRAM_API = "https://insta-api-fawn.vercel.app/api/insta-download?url={url}"
