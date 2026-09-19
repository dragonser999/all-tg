import asyncio
import logging
import re

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery

import config
from utils import download_direct_file, download_hls_stream, is_hls_url, cleanup_file
from keyboards import (
    youtube_format_keyboard,
    facebook_quality_keyboard,
    terabox_action_keyboard,
    spotify_track_keyboard,
)
from services import youtube, facebook, spotify, terabox, instagram

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Using api_id + api_hash (MTProto via Pyrogram) instead of the plain HTTP
# Bot API lets this bot send files up to 2 GB without a Local Bot API Server.
app = Client(
    "media_downloader_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
)

# Simple in-memory cache linking a "status" message id to the API result,
# so that when a user taps a button we know which data it refers to.
# NOTE: this cache is cleared if the bot restarts. For production use with
# many users, consider replacing this with Redis or a database.
SESSION_CACHE = {}

URL_PATTERNS = {
    "youtube": re.compile(r"(youtube\.com|youtu\.be)"),
    "facebook": re.compile(r"(facebook\.com|fb\.watch)"),
    "spotify": re.compile(r"open\.spotify\.com"),
    "terabox": re.compile(r"(terabox\.com|1024terabox\.com|teraboxapp\.com|teraboxlink\.com)"),
    "instagram": re.compile(r"instagram\.com"),
}


def detect_platform(url: str):
    for platform, pattern in URL_PATTERNS.items():
        if pattern.search(url):
            return platform
    return None


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

@app.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    await message.reply_text(
        "👋 Welcome to Media Downloader Bot!\n\n"
        "Send me a link from:\n"
        "🎬 YouTube\n"
        "📸 Instagram\n"
        "📘 Facebook\n"
        "🎵 Spotify (track or album)\n"
        "☁️ Terabox\n\n"
        "I will fetch it and send you the actual file here, up to 2 GB."
    )


@app.on_message(filters.text & ~filters.command("start"))
async def link_handler(client: Client, message: Message):
    url = message.text.strip()
    platform = detect_platform(url)

    if not platform:
        await message.reply_text(
            "⚠️ I couldn't recognize this link.\n"
            "Please send a valid YouTube, Facebook, Spotify, or Terabox link."
        )
        return

    status = await message.reply_text("⏳ Fetching info, please wait...")

    try:
        if platform == "youtube":
            data = await youtube.fetch(url)
            SESSION_CACHE[status.id] = {"platform": "youtube", "data": data}
            await status.edit_text(
                f"🎬 {data['title'][:100]}\n\nChoose a format:",
                reply_markup=youtube_format_keyboard(status.id),
            )

        elif platform == "instagram":
            data = await instagram.fetch(url)
            await status.edit_text("⬇️ Downloading Instagram media...")
            filename = "instagram_media.mp4"
            path = await download_direct_file(data["download_url"], filename)
            try:
                if "video" in data.get("file_type", "video"):
                    await client.send_video(message.chat.id, path, caption="📸 Instagram")
                else:
                    await client.send_photo(message.chat.id, path, caption="📸 Instagram")
                await status.delete()
            finally:
                cleanup_file(path)

        elif platform == "facebook":
            data = await facebook.fetch(url)
            SESSION_CACHE[status.id] = {"platform": "facebook", "data": data}
            await status.edit_text(
                "📘 Facebook video found.\n\nChoose quality:",
                reply_markup=facebook_quality_keyboard(status.id),
            )

        elif platform == "spotify":
            data = await spotify.fetch(url)
            SESSION_CACHE[status.id] = {"platform": "spotify", "data": data}

            if data["type"] == "track":
                track = data["tracks"][0]
                await status.edit_text(f"🎵 {track['title']} — {track['artist']}\n\nDownloading preview...")
                await send_spotify_track(client, message.chat.id, track)
                await status.delete()
                SESSION_CACHE.pop(status.id, None)
            else:
                meta = data["metadata"]
                await status.edit_text(
                    f"💿 Album: {meta['title']}\n"
                    f"Artist: {meta['artist']}\n"
                    f"Tracks: {meta['total_tracks']}\n\n"
                    "Choose a track (30-second preview each):",
                    reply_markup=spotify_track_keyboard(status.id, data["tracks"]),
                )

        elif platform == "terabox":
            data = await terabox.fetch(url)
            SESSION_CACHE[status.id] = {"platform": "terabox", "data": data}
            await status.edit_text(
                f"☁️ {data.get('total_files', len(data['result']))} file(s) found.\n\nChoose an action:",
                reply_markup=terabox_action_keyboard(status.id, data["result"]),
            )

    except Exception as e:
        logger.exception("Failed to fetch media info")
        await status.edit_text(f"❌ Failed to fetch this link.\nError: {e}")


# ---------------------------------------------------------------------------
# Callback query (button click) handler
# ---------------------------------------------------------------------------

@app.on_callback_query()
async def callback_handler(client: Client, callback_query: CallbackQuery):
    data = callback_query.data

    try:
        if data.startswith("yt_"):
            _, fmt, session_id = data.split("_")
            await handle_youtube_callback(client, callback_query, fmt, int(session_id))

        elif data.startswith("fb_"):
            _, quality, session_id = data.split("_")
            await handle_facebook_callback(client, callback_query, quality, int(session_id))

        elif data.startswith("tb_"):
            _, action, index, session_id = data.split("_")
            await handle_terabox_callback(client, callback_query, action, int(index), int(session_id))

        elif data.startswith("sp_"):
            _, index, session_id = data.split("_")
            await handle_spotify_callback(client, callback_query, int(index), int(session_id))

    except Exception as e:
        logger.exception("Callback handling failed")
        short_error = str(e)[:150]
        await callback_query.answer(f"Error: {short_error}", show_alert=True)


async def handle_youtube_callback(client: Client, callback_query: CallbackQuery, fmt: str, session_id: int):
    session = SESSION_CACHE.get(session_id)
    if not session:
        await callback_query.answer("Session expired, please send the link again.", show_alert=True)
        return

    await callback_query.answer("⏳ Downloading...")
    data = session["data"]
    chat_id = callback_query.message.chat.id
    title = data["title"][:50]

    if fmt == "mp4":
        url = data["downloads"].get("hd") or data["downloads"].get("sd")
        filename = f"{title}.mp4"
    else:
        url = data["downloads"].get("audio")
        filename = f"{title}.mp3"

    if not url:
        await callback_query.message.reply_text(f"❌ {fmt.upper()} is not available for this video.")
        return

    await callback_query.message.edit_text(f"⬇️ Downloading {fmt.upper()}...")
    path = await download_direct_file(url, filename, headers={"Referer": "https://www.youtube.com/"})

    try:
        if fmt == "mp4":
            await client.send_video(chat_id, path, caption=title)
        else:
            await client.send_audio(chat_id, path, caption=title)
        await callback_query.message.delete()
    finally:
        cleanup_file(path)
        SESSION_CACHE.pop(session_id, None)


async def handle_facebook_callback(client: Client, callback_query: CallbackQuery, quality: str, session_id: int):
    session = SESSION_CACHE.get(session_id)
    if not session:
        await callback_query.answer("Session expired, please send the link again.", show_alert=True)
        return

    await callback_query.answer("⏳ Downloading...")
    data = session["data"]
    chat_id = callback_query.message.chat.id

    url = data["downloads"].get(quality)
    if not url:
        await callback_query.message.reply_text(f"❌ {quality.upper()} is not available.")
        return

    filename = f"facebook_video_{quality}.mp4"
    await callback_query.message.edit_text(f"⬇️ Downloading {quality.upper()}...")
    path = await download_direct_file(url, filename, headers={"Referer": "https://www.facebook.com/"})

    try:
        await client.send_video(chat_id, path, caption=f"📘 Facebook video ({quality.upper()})")
        await callback_query.message.delete()
    finally:
        cleanup_file(path)
        SESSION_CACHE.pop(session_id, None)


async def handle_terabox_callback(client: Client, callback_query: CallbackQuery, action: str, index: int, session_id: int):
    session = SESSION_CACHE.get(session_id)
    if not session:
        await callback_query.answer("Session expired, please send the link again.", show_alert=True)
        return

    files = session["data"]["result"]
    file_info = files[index]
    chat_id = callback_query.message.chat.id

    if action == "st":
        # Telegram cannot natively play .m3u8 streams, so we share the link
        # itself for the user to open in VLC / MX Player / a browser.
        await callback_query.answer()
        await callback_query.message.reply_text(
            f"▶️ Stream link (open in VLC or another HLS-capable player):\n{file_info['stream_url']}"
        )
        return

    await callback_query.answer("⏳ Downloading...")
    url = file_info["download_url"]
    filename = file_info.get("file_name", f"terabox_file_{index}.mp4")

    await callback_query.message.edit_text("⬇️ Downloading file, this may take a while for large files...")

    if is_hls_url(url):
        # ffmpeg is blocking (subprocess), so run it in a thread to avoid
        # freezing the bot's event loop while it downloads/remuxes.
        path = await asyncio.to_thread(download_hls_stream, url, filename)
    else:
        path = await download_direct_file(url, filename)

    try:
        await client.send_document(chat_id, path, caption=filename)
        await callback_query.message.delete()
    finally:
        cleanup_file(path)
        SESSION_CACHE.pop(session_id, None)


async def handle_spotify_callback(client: Client, callback_query: CallbackQuery, index: int, session_id: int):
    session = SESSION_CACHE.get(session_id)
    if not session:
        await callback_query.answer("Session expired, please send the link again.", show_alert=True)
        return

    await callback_query.answer("⏳ Downloading preview...")
    track = session["data"]["tracks"][index]
    chat_id = callback_query.message.chat.id
    await send_spotify_track(client, chat_id, track)


async def send_spotify_track(client: Client, chat_id: int, track: dict):
    """
    Downloads and sends a Spotify track's 30-second preview clip.
    Full-length songs are not available through this API (Spotify only
    exposes short previews publicly), so this is clearly labeled to the user.
    """
    if not track.get("preview_url"):
        await client.send_message(chat_id, f"❌ No preview available for {track['title']}.")
        return

    filename = f"{track['title'][:50]}.mp3"
    path = await download_direct_file(track["preview_url"], filename)

    try:
        await client.send_audio(
            chat_id,
            path,
            title=track["title"],
            performer=track["artist"],
            caption="🎵 30-second preview only — Spotify does not allow full track downloads via public APIs.",
        )
    finally:
        cleanup_file(path)


if __name__ == "__main__":
    logger.info("Starting Media Downloader Bot...")
    app.run()
