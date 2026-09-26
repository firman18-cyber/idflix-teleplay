# IDFLIX Teleplay Server

Minimal FastAPI + Pyrogram MTProto streaming service for the existing IDFLIX Telegram Group.

## Endpoints

- `GET /health` — health check
- `HEAD /stream/{message_id}` — media metadata
- `GET /stream/{message_id}` — HTTP Range video streaming

## Environment

Copy `.env.example` to `.env` and fill in Telegram API credentials, the existing bot token, and the Telegram Group chat ID.

`STREAM_TOKEN` is a temporary protection for initial testing. The website should later use short-lived signed stream URLs instead of exposing a permanent token.

## Telegram requirements

The bot used by this service must be able to access the target messages in the existing IDFLIX Group/Supergroup. Topic/thread organization does not change the message ID used for retrieval.

## Local run

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Stream test

```text
GET /stream/<MESSAGE_ID>?token=<STREAM_TOKEN>
Range: bytes=0-
```
