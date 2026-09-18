import os
import re
import asyncio
import requests
import aiohttp
import aiofiles
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

# -------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------
API_ID = int(os.environ.get("API_ID", "1234567"))
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")

app = Client("media_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# In-memory session store for multi-step button selections
USER_DATA = {}

# -------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------
def get_clean_filename(url, default_ext="mp4"):
    filename = url.split('/')[-1].split('?')[0]
    if not filename or '.' not in filename:
        filename = f"file.{default_ext}"
    return filename

async def download_file(url, destination_path, message_to_edit=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"HTTP Error: {response.status}")
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            async with aiofiles.open(destination_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(1024 * 1024):
                    if chunk:
                        await f.write(chunk)
                        downloaded += len(chunk)
                        if message_to_edit and total_size > 0:
                            percent = (downloaded / total_size) * 100
                            if downloaded % (5 * 1024 * 1024) < (1024 * 1024):  # Edit message sparingly
                                try:
                                    await message_to_edit.edit_text(f"📥 Downloading file... {percent:.1f}%")
                                except Exception:
                                    pass
    return destination_path

# -------------------------------------------------------------
# COMMAND HANDLERS
# -------------------------------------------------------------
@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    await message.reply_text(
        "👋 **Hello! Welcome to Media Downloader Bot.**\n\n"
        "Send me any valid link from YouTube, Facebook, Instagram, Spotify, or Terabox to download content."
    )

@app.on_message(filters.private & filters.text & ~filters.command(["start"]))
async def process_media_url(client: Client, message: Message):
    url = message.text.strip()
    user_id = message.from_user.id

    # 1. YOUTUBE
    if "youtube.com" in url or "youtu.be" in url:
        status_msg = await message.reply_text("🔎 Fetching YouTube video details...")
        api_url = f"https://yt-api-s2tl.vercel.app/api/yt-download?url={url}"
        try:
            res = requests.get(api_url).json()
            if res.get("status") and res.get("result"):
                result = res["result"]
                USER_DATA[user_id] = {
                    "type": "youtube",
                    "title": result.get("title", "YouTube Media"),
                    "downloads": result.get("downloads", {})
                }
                buttons = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🎵 MP3 Audio", callback_data="yt_audio"),
                        InlineKeyboardButton("🎬 MP4 Video (SD)", callback_data="yt_sd")
                    ],
                    [
                        InlineKeyboardButton("🎥 MP4 Video (HD)", callback_data="yt_hd")
                    ]
                ])
                await status_msg.edit_text(" Choose your preferred format for Youtube:", reply_markup=buttons)
            else:
                await status_msg.edit_text("❌ Failed to parse YouTube link or video not found.")
        except Exception as e:
            await status_msg.edit_text(f"❌ Error fetching YouTube link: {str(e)}")

    # 2. FACEBOOK
    elif "facebook.com" in url or "fb.watch" in url:
        status_msg = await message.reply_text("🔎 Fetching Facebook media details...")
        api_url = f"https://fb-api-cyan.vercel.app/api/fb-download?url={url}"
        try:
            res = requests.get(api_url).json()
            if res.get("status") and res.get("result"):
                downloads = res["result"].get("downloads", {})
                USER_DATA[user_id] = {
                    "type": "facebook",
                    "downloads": downloads
                }
                buttons = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("📹 Facebook SD Quality", callback_data="fb_sd"),
                        InlineKeyboardButton("🎥 Facebook HD Quality", callback_data="fb_hd")
                    ]
                ])
                await status_msg.edit_text(" Choose quality option for Facebook Video:", reply_markup=buttons)
            else:
                await status_msg.edit_text("❌ Failed to parse Facebook link.")
        except Exception as e:
            await status_msg.edit_text(f"❌ Error fetching Facebook link: {str(e)}")

    # 3. INSTAGRAM
    elif "instagram.com" in url:
        status_msg = await message.reply_text("📥 Processing Instagram link...")
        api_url = f"https://insta-api-fawn.vercel.app/api/insta-download?url={url}"
        try:
            res = requests.get(api_url).json()
            if res.get("status") and res.get("result"):
                media_url = res["result"].get("download_url")
                file_path = f"insta_{user_id}.mp4"
                await status_msg.edit_text("⏬ Downloading Instagram media...")
                await download_file(media_url, file_path, status_msg)
                await status_msg.edit_text("📤 Uploading media to Telegram...")
                await client.send_video(chat_id=message.chat.id, video=file_path)
                await status_msg.delete()
                if os.path.exists(file_path):
                    os.remove(file_path)
            else:
                await status_msg.edit_text("❌ Failed to download Instagram media.")
        except Exception as e:
            await status_msg.edit_text(f"❌ Error downloading Instagram file: {str(e)}")

    # 4. SPOTIFY
    elif "spotify.com" in url:
        status_msg = await message.reply_text("🔎 Fetching Spotify metadata...")
        api_url = f"https://spotify-api-five-beige.vercel.app/api/spotify-download?url={url}"
        try:
            res = requests.get(api_url).json()
            if res.get("status") and res.get("tracks"):
                tracks = res["tracks"]
                await status_msg.edit_text(f"🎶 Processing {len(tracks)} track(s)...")
                for index, track in enumerate(tracks):
                    preview_url = track.get("preview_url")
                    title = track.get("title", f"Track_{index+1}")
                    artist = track.get("artist", "Unknown Artist")
                    if preview_url:
                        file_path = f"spotify_{user_id}_{index}.mp3"
                        await download_file(preview_url, file_path)
                        await client.send_audio(
                            chat_id=message.chat.id,
                            audio=file_path,
                            title=title,
                            performer=artist
                        )
                        if os.path.exists(file_path):
                            os.remove(file_path)
                await status_msg.edit_text("✅ All available Spotify track previews sent!")
            else:
                await status_msg.edit_text("❌ Failed to process Spotify URL.")
        except Exception as e:
            await status_msg.edit_text(f"❌ Error fetching Spotify track: {str(e)}")

    # 5. TERABOX
    elif "terabox" in url or "1024terabox" in url:
        status_msg = await message.reply_text("🔎 Fetching Terabox file metadata...")
        api_url = f"https://terabox-api-psi-navy.vercel.app/api/terabox-download?url={url}"
        try:
            res = requests.get(api_url).json()
            if res.get("status") and res.get("result"):
                item = res["result"][0]
                USER_DATA[user_id] = {
                    "type": "terabox",
                    "file_name": item.get("file_name", "terabox_file.mp4"),
                    "download_url": item.get("download_url"),
                    "stream_url": item.get("stream_url")
                }
                buttons = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("⬇️ Downloader", callback_data="tb_dl"),
                        InlineKeyboardButton("📺 Stream Link", callback_data="tb_stream")
                    ]
                ])
                await status_msg.edit_text(
                    f"📁 **File Name:** {item.get('file_name')}\n"
                    f"📦 **Size:** {item.get('file_size')}\n\n"
                    f"Select an option below:",
                    reply_markup=buttons
                )
            else:
                await status_msg.edit_text("❌ Failed to retrieve Terabox link details.")
        except Exception as e:
            await status_msg.edit_text(f"❌ Error processing Terabox URL: {str(e)}")

    else:
        await message.reply_text("❌ Unsupported link platform. Please provide YouTube, Facebook, Instagram, Spotify, or Terabox link.")

# -------------------------------------------------------------
# CALLBACK QUERY HANDLERS (BUTTON CLICKS)
# -------------------------------------------------------------
@app.on_callback_query()
async def handle_callbacks(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    if user_id not in USER_DATA:
        await callback_query.answer("⚠️ Session expired. Please paste the media link again.", show_alert=True)
        return

    session = USER_DATA[user_id]
    await callback_query.message.edit_reply_markup(reply_markup=None)  # Remove buttons after selection

    # --- YOUTUBE CALLBACKS ---
    if data in ["yt_audio", "yt_sd", "yt_hd"]:
        downloads = session.get("downloads", {})
        if data == "yt_audio":
            download_url = downloads.get("audio")
            ext = "mp3"
        elif data == "yt_sd":
            download_url = downloads.get("sd")
            ext = "mp4"
        else:
            download_url = downloads.get("hd")
            ext = "mp4"

        if not download_url:
            await callback_query.message.edit_text("❌ Download URL not found for selected option.")
            return

        file_path = f"yt_media_{user_id}.{ext}"
        await callback_query.message.edit_text("⏬ Downloading selected YouTube format...")
        try:
            await download_file(download_url, file_path, callback_query.message)
            await callback_query.message.edit_text("📤 Uploading file to Telegram...")
            if ext == "mp3":
                await client.send_audio(chat_id=callback_query.message.chat.id, audio=file_path, title=session.get("title"))
            else:
                await client.send_video(chat_id=callback_query.message.chat.id, video=file_path, caption=session.get("title"))
            await callback_query.message.delete()
        except Exception as e:
            await callback_query.message.edit_text(f"❌ Upload failed: {str(e)}")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    # --- FACEBOOK CALLBACKS ---
    elif data in ["fb_sd", "fb_hd"]:
        downloads = session.get("downloads", {})
        download_url = downloads.get("sd") if data == "fb_sd" else downloads.get("hd")

        if not download_url:
            await callback_query.message.edit_text("❌ Selected Facebook video quality not available.")
            return

        file_path = f"fb_video_{user_id}.mp4"
        await callback_query.message.edit_text("⏬ Downloading Facebook video...")
        try:
            await download_file(download_url, file_path, callback_query.message)
            await callback_query.message.edit_text("📤 Uploading video to Telegram...")
            await client.send_video(chat_id=callback_query.message.chat.id, video=file_path)
            await callback_query.message.delete()
        except Exception as e:
            await callback_query.message.edit_text(f"❌ Upload failed: {str(e)}")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    # --- TERABOX CALLBACKS ---
    elif data == "tb_dl":
        download_url = session.get("download_url")
        file_name = session.get("file_name", "terabox_download.mp4")
        file_path = f"tb_{user_id}_{file_name}"

        await callback_query.message.edit_text("⏬ Downloading file from Terabox server...")
        try:
            await download_file(download_url, file_path, callback_query.message)
            await callback_query.message.edit_text("📤 Uploading media file to Telegram...")
            await client.send_document(chat_id=callback_query.message.chat.id, document=file_path, file_name=file_name)
            await callback_query.message.delete()
        except Exception as e:
            await callback_query.message.edit_text(f"❌ Failed to send Terabox file: {str(e)}")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    elif data == "tb_stream":
        stream_url = session.get("stream_url")
        await callback_query.message.edit_text(
            f"🔗 **Terabox Fast Stream Link:**\n\n`{stream_url}`\n\n"
            f"You can copy and paste this link in VLC Media Player to stream."
        )

# -------------------------------------------------------------
# RUN BOT
# -------------------------------------------------------------
if __name__ == "__main__":
    print("Bot is starting...")
    app.run()
