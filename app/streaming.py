import asyncio
import logging
from typing import AsyncGenerator
from .telegram import clients
from .config import get_settings

settings = get_settings()
logger = logging.getLogger("idflix.teleplay.streaming")
_semaphores: dict[int, asyncio.Semaphore] = {}


def _sem(index: int) -> asyncio.Semaphore:
    if index not in _semaphores:
        _semaphores[index] = asyncio.Semaphore(settings.telegram_client_concurrency)
    return _semaphores[index]


async def parallel_stream_generator(message, offset: int, length: int,
                                    chunk_size: int = 1024 * 1024,
                                    concurrency: int | None = None):
    if not clients:
        raise RuntimeError("No Telegram clients are running")
    pool_size = len(clients)
    concurrency = max(1, min(concurrency or pool_size, pool_size))

    start_chunk = offset // chunk_size
    end_chunk = (offset + length - 1) // chunk_size
    total_chunks = end_chunk - start_chunk + 1
    chat_id = message.chat.id
    message_id = message.id

    async def fetch_msg(client, idx):
        try:
            msg = await client.get_messages(chat_id, message_id)
            if msg and (msg.document or msg.video or msg.audio):
                return idx, msg
        except Exception as e:
            logger.warning("client %s cannot fetch message %s: %s", idx, message_id, e)
        return idx, None

    fetched = await asyncio.gather(*[
        fetch_msg(clients[i % pool_size], i % pool_size) for i in range(concurrency)
    ])
    client_messages = {i: m for i, m in fetched if m is not None}
    if not client_messages:
        raise RuntimeError("No Telegram client can access the message")

    queue = asyncio.Queue()
    for chunk in range(start_chunk, end_chunk + 1):
        queue.put_nowait(chunk)

    loop = asyncio.get_running_loop()
    results = {chunk: loop.create_future() for chunk in range(start_chunk, end_chunk + 1)}

    async def worker(worker_id: int):
        client = clients[worker_id % pool_size]
        cidx = worker_id % pool_size
        msg = client_messages.get(cidx)
        if msg is None:
            return
        while True:
            try:
                chunk_index = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                async with _sem(cidx):
                    data = bytearray()
                    async for part in client.stream_media(msg, limit=1, offset=chunk_index):
                        data.extend(part)
                if not results[chunk_index].done():
                    results[chunk_index].set_result(bytes(data))
            except Exception as e:
                if not results[chunk_index].done():
                    results[chunk_index].set_exception(e)
            finally:
                queue.task_done()

    workers = [asyncio.create_task(worker(i)) for i in range(concurrency)]
    try:
        for chunk_index in range(start_chunk, end_chunk + 1):
            yield await results[chunk_index]
    finally:
        for task in workers:
            task.cancel()
        await asyncio.gather(*workers, return_exceptions=True)


async def stream_file(message, from_bytes: int, until_bytes: int) -> AsyncGenerator[bytes, None]:
    chunk_size = 1024 * 1024
    needed = until_bytes - from_bytes + 1
    yielded = 0
    skip = from_bytes % chunk_size

    async for chunk in parallel_stream_generator(message, from_bytes, needed, chunk_size):
        if skip:
            chunk = chunk[skip:]
            skip = 0
        remaining = needed - yielded
        if len(chunk) > remaining:
            chunk = chunk[:remaining]
        if chunk:
            yield chunk
            yielded += len(chunk)
        if yielded >= needed:
            break
