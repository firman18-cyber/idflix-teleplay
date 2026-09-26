import asyncio
import logging
from pathlib import Path
from pyrogram.types import Message
from .config import get_settings
from .patch import Client

settings = get_settings()
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
SESSION_DIR = BASE_DIR / "session"
clients: list[Client] = []
tg_client: Client | None = None


def build_clients() -> None:
    global tg_client
    if clients:
        return
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    for i, token in enumerate(settings.all_bot_tokens):
        c = Client(
            name=str(SESSION_DIR / f"bot_{i}"),
            api_id=settings.telegram_api_id,
            api_hash=settings.telegram_api_hash,
            bot_token=token,
            ipv6=False,
            max_concurrent_transmissions=settings.telegram_client_concurrency,
            no_updates=True,
        )
        c.pool_index = i
        clients.append(c)
    tg_client = clients[0]


async def start_one(i: int, client: Client):
    try:
        await client.start()
        me = await client.get_me()
        logger.info("Telegram client %d started: @%s", i, me.username)
    except Exception:
        logger.exception("Telegram client %d failed to start", i)
        raise


async def start_all():
    build_clients()
    await asyncio.gather(*(start_one(i, c) for i, c in enumerate(clients)))


async def stop_all():
    await asyncio.gather(*(c.stop() for c in clients if c.is_connected), return_exceptions=True)


async def get_message(message_id: int) -> Message:
    if tg_client is None:
        raise RuntimeError("Telegram client is not started")
    msg = await tg_client.get_messages(settings.telegram_chat_id, message_id)
    if not msg or getattr(msg, "empty", False):
        raise LookupError("Telegram message not found")
    return msg


def media_info(message: Message) -> dict:
    media = message.video or message.document or message.audio
    if media is None:
        raise ValueError("Message does not contain streamable media")
    file_size = int(getattr(media, "file_size", 0) or 0)
    if file_size <= 0:
        raise ValueError("Media has no usable file size")
    mime = getattr(media, "mime_type", None) or "application/octet-stream"
    filename = getattr(media, "file_name", None) or f"telegram-{message.id}"
    return {"size": file_size, "mime": mime, "filename": filename}
