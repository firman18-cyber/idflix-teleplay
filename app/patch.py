import asyncio
from pyrogram import Client as PyroClient, errors, raw, session

class Client(PyroClient):
    async def invoke(self, query: raw.core.TLObject,
                     retries: int = session.Session.MAX_RETRIES,
                     timeout: float = session.Session.WAIT_TIMEOUT,
                     sleep_threshold: float = None):
        while True:
            try:
                return await super().invoke(
                    query=query,
                    retries=retries,
                    timeout=timeout,
                    sleep_threshold=sleep_threshold,
                )
            except errors.FloodWait as e:
                await asyncio.sleep(e.value + 2)
