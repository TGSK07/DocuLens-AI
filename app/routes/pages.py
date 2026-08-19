"""HTML pages."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core import storage
from app.core.schemas import SCHEMAS

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    recent = storage.list_recent_extractions(limit=15)
    schemas = [
        {"key": s.key, "label": s.label, "description": s.description}
        for s in SCHEMAS.values()
    ]
    schemas.append(
        {"key": "custom", "label": "Custom", "description": "Define your own fields."}
    )
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request, "schemas": schemas, "recent": recent},
    )


@router.get("/result/{extraction_id}", response_class=HTMLResponse)
async def result_page(request: Request, extraction_id: str) -> HTMLResponse:
    ext = storage.get_extraction(extraction_id)
    if not ext:
        raise HTTPException(status_code=404, detail="Extraction not found")
    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={"request": request, "extraction": ext},
    )
