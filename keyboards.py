from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def youtube_format_keyboard(session_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎥 MP4 (Video)", callback_data=f"yt_mp4_{session_id}"),
            InlineKeyboardButton("🎵 MP3 (Audio)", callback_data=f"yt_mp3_{session_id}"),
        ]
    ])


def facebook_quality_keyboard(session_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔴 HD", callback_data=f"fb_hd_{session_id}"),
            InlineKeyboardButton("⚪ SD", callback_data=f"fb_sd_{session_id}"),
        ]
    ])


def terabox_action_keyboard(session_id: int, files: list) -> InlineKeyboardMarkup:
    """One 'Downloader / Stream' row per file found in the Terabox link."""
    rows = []
    for index, file_info in enumerate(files):
        label = file_info.get("file_name", f"File {index + 1}")[:20]
        rows.append([
            InlineKeyboardButton(f"⬇️ Downloader ({label})", callback_data=f"tb_dl_{index}_{session_id}"),
        ])
        rows.append([
            InlineKeyboardButton(f"▶️ Stream ({label})", callback_data=f"tb_st_{index}_{session_id}"),
        ])
    return InlineKeyboardMarkup(rows)


def spotify_track_keyboard(session_id: int, tracks: list) -> InlineKeyboardMarkup:
    rows = []
    for index, track in enumerate(tracks):
        label = f"{index + 1}. {track['title'][:30]}"
        rows.append([InlineKeyboardButton(label, callback_data=f"sp_{index}_{session_id}")])
    return InlineKeyboardMarkup(rows)
