import aiohttp

import config


async def fetch(url: str) -> dict:
    """
    Calls the YouTube download API and returns the 'result' section,
    which contains: title, thumbnail, downloads (sd / hd / audio links).
    """
    api_url = config.YOUTUBE_API.format(url=url)

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
            data = await response.json()

    if not data.get("status"):
        raise ValueError("YouTube API returned an error for this link.")

    return data["result"]
