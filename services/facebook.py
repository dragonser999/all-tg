import aiohttp

import config


async def fetch(url: str) -> dict:
    """
    Calls the Facebook download API and returns the 'result' section,
    which contains: thumbnail, downloads (hd / sd links).
    """
    api_url = config.FACEBOOK_API.format(url=url)

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
            data = await response.json()

    if not data.get("status"):
        raise ValueError("Facebook API returned an error for this link.")

    return data["result"]
