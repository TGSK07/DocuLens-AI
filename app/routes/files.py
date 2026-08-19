"""Serve per-page PNG thumbnails."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core import storage

router = APIRouter()


@router.get("/files/{extraction_id}/page/{page_number}")
async def get_page(extraction_id: str, page_number: int) -> FileResponse:
    if not storage.get_extraction(extraction_id):
        raise HTTPException(status_code=404, detail="extraction not found")
    if page_number < 1:
        raise HTTPException(status_code=400, detail="invalid page number")
    path = storage.page_path(extraction_id, page_number)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="page not found")
    return FileResponse(
        path,
        media_type="image/png",
        headers={"cache-control": "private, max-age=86400"},
    )
