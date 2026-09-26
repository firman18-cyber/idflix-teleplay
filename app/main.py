import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .telegram import start_all, stop_all
from .routers import streaming_router

settings = get_settings()
logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_all()
    yield
    await stop_all()

app = FastAPI(title="IDFLIX Teleplay Server", version="0.1.0", lifespan=lifespan)
origins = settings.allowed_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=origins != ["*"],
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["Authorization", "Range", "Content-Type"],
    expose_headers=["Content-Range", "Accept-Ranges", "Content-Length", "Content-Disposition"],
)
app.include_router(streaming_router)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "idflix-teleplay"}
