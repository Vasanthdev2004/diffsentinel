import asyncio
import requests


async def fetch_user(url):
    response = requests.get(url)
    return response.json()
