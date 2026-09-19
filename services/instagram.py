import aiohttp

import config


async def fetch(url: str) -> dict:
    """
    Calls the Instagram download API and returns the 'result' section,
    which contains: download_url, file_type.
    """
    api_url = config.INSTAGRAM_API.format(url=url)

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
            data = await response.json()

    if not data.get("status"):
        raise ValueError("Instagram API returned an error for this link.")

    return data["result"]
