import aiohttp

import config


async def fetch(url: str) -> dict:
    """
    Calls the Terabox download API and returns the full response, which
    contains a 'result' list of files, each with download_url, stream_url,
    file_name, file_size, etc.
    """
    api_url = config.TERABOX_API.format(url=url)

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
            data = await response.json()

    if not data.get("status"):
        raise ValueError("Terabox API returned an error for this link.")

    return data
