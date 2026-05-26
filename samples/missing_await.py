import asyncio


async def pause_briefly():
    pause = asyncio.sleep(1)
    return pause
