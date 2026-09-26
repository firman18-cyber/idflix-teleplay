import re
from urllib.parse import quote
from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from ..config import get_settings
from ..telegram import get_message, media_info
from ..streaming import stream_file

settings = get_settings()
router = APIRouter(prefix="/stream", tags=["Streaming"])


def parse_range(value: str | None, size: int) -> tuple[int, int, bool]:
    if not value:
        return 0, size - 1, False
    m = re.fullmatch(r"bytes=(\d+)-(\d*)", value.strip())
    if not m:
        raise HTTPException(416, "Invalid Range header", headers={"Content-Range": f"bytes */{size}"})
    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else size - 1
    if start >= size or end < start:
        raise HTTPException(416, "Range not satisfiable", headers={"Content-Range": f"bytes */{size}"})
    return start, min(end, size - 1), True


def check_token(token: str | None, authorization: str | None):
    expected = settings.stream_token.strip()
    if not expected:
        return
    bearer = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization[7:].strip()
    supplied = token or bearer
    if supplied != expected:
        raise HTTPException(401, "Unauthorized")


@router.get("/{message_id}")
async def stream(message_id: int, request: Request,
                 token: str | None = Query(None),
                 authorization: str | None = Header(None)):
    check_token(token, authorization)
    try:
        message = await get_message(message_id)
        info = media_info(message)
    except LookupError:
        raise HTTPException(404, "Telegram message not found")
    except ValueError as e:
        raise HTTPException(415, str(e))

    start, end, is_range = parse_range(request.headers.get("range"), info["size"])
    length = end - start + 1
    disposition = "inline" if info["mime"].startswith(("video/", "audio/")) else "attachment"
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Range": f"bytes {start}-{end}/{info['size']}",
        "Content-Length": str(length),
        "Content-Disposition": f"{disposition}; filename*=utf-8''{quote(info['filename'])}",
        "Cache-Control": "private, no-store",
    }

    return StreamingResponse(
        stream_file(message, start, end),
        status_code=206 if is_range else 200,
        media_type=info["mime"],
        headers=headers,
    )


@router.head("/{message_id}")
async def stream_head(message_id: int,
                      token: str | None = Query(None),
                      authorization: str | None = Header(None)):
    check_token(token, authorization)
    try:
        message = await get_message(message_id)
        info = media_info(message)
    except LookupError:
        raise HTTPException(404, "Telegram message not found")
    except ValueError as e:
        raise HTTPException(415, str(e))
    return Response(headers={
        "Accept-Ranges": "bytes",
        "Content-Length": str(info["size"]),
        "Content-Type": info["mime"],
        "Content-Disposition": f"inline; filename*=utf-8''{quote(info['filename'])}",
    })
