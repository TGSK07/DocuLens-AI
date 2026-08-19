"""FastAPI application entry."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.storage import init_schema
from app.logger import configure_logging, logger
from app.routes import extract, files, pages


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    init_schema()
    logger.info("Multimodal Document OCR — ready")
    yield


app = FastAPI(
    title="Multimodal Document OCR + Extraction",
    version="0.1.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(pages.router)
app.include_router(extract.router)
app.include_router(files.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
