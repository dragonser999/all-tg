import aiohttp

import config


async def fetch(url: str) -> dict:
    """
    Calls the Spotify download API and returns the full response, which
    contains: type ('track' or 'album'), metadata, and a list of tracks.

    NOTE: this API only returns 'preview_url' for each track, which is a
    30-second preview clip. Spotify does not allow full-song downloads
    through public APIs, so full tracks cannot be sent — only previews.
    """
    api_url = config.SPOTIFY_API.format(url=url)

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
            data = await response.json()

    if not data.get("status"):
        raise ValueError("Spotify API returned an error for this link.")

    return data
