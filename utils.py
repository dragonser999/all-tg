import os
import re
import subprocess

import aiohttp

import config


def sanitize_filename(name: str, max_length: int = 60) -> str:
    """Remove characters that are not safe for file names, and trim length."""
    name = re.sub(r'[\\/:*?"<>|\n\r]+', "", name)
    name = name.strip()
    return name[:max_length] if name else "file"


async def download_direct_file(url: str, filename: str) -> str:
    """
    Download a normal (non-HLS) file from a direct URL and save it to the
    local downloads folder. Returns the local file path.
    """
    os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
    path = os.path.join(config.DOWNLOAD_DIR, sanitize_filename(filename))

    timeout = aiohttp.ClientTimeout(total=None)  # no timeout, large files allowed
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            response.raise_for_status()
            with open(path, "wb") as f:
                async for chunk in response.content.iter_chunked(1024 * 1024):
                    f.write(chunk)

    return path


def download_hls_stream(m3u8_url: str, filename: str) -> str:
    """
    Download an HLS (.m3u8) stream and remux it into a single .mp4 file
    using ffmpeg. Needed for sources (like Terabox) that expose a stream
    playlist instead of a plain direct file link.

    Requires ffmpeg to be installed on the system (apt install ffmpeg).
    This function is blocking, so call it with asyncio.to_thread(...).
    """
    os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
    name = sanitize_filename(filename)
    if not name.lower().endswith(".mp4"):
        name += ".mp4"
    path = os.path.join(config.DOWNLOAD_DIR, name)

    command = [
        "ffmpeg", "-y",
        "-i", m3u8_url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        path,
    ]
    subprocess.run(command, check=True, capture_output=True)
    return path


def is_hls_url(url: str) -> bool:
    return ".m3u8" in url.lower()


def cleanup_file(path: str):
    """Delete a local file after it has been uploaded to Telegram."""
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
