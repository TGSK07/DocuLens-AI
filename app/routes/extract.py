"""Upload + extract + save endpoint."""
from __future__ import annotations

import csv
import io
import json
import shutil
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel

from app.config import settings
from app.core import storage
from app.core.extractor import extract_with_custom, extract_with_predefined
from app.core.image import load_image, save_png
from app.core.pdf import render_pdf
from app.core.schemas import SCHEMAS, CustomFieldSpec
from app.logger import logger

router = APIRouter()


SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
SUPPORTED_PDF_SUFFIXES = {".pdf"}
SUPPORTED_SUFFIXES = SUPPORTED_IMAGE_SUFFIXES | SUPPORTED_PDF_SUFFIXES


@router.post("/extract")
async def extract(
    file: UploadFile = File(...),
    schema_key: str = Form(...),
    custom_fields_json: str | None = Form(default=None),
) -> RedirectResponse:
    if file.filename is None:
        raise HTTPException(status_code=400, detail="Missing filename")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type {suffix!r}. Supported: {', '.join(sorted(SUPPORTED_SUFFIXES))}",
        )

    # Generate the extraction id up front so we can persist files alongside it
    placeholder = storage.create_extraction(
        filename=file.filename,
        schema_key=schema_key if schema_key in SCHEMAS else "custom",
        schema_label="(processing)",
        page_count=0,
        data={},
        custom_schema=None,
        tokens_input=0,
        tokens_output=0,
        duration_ms=0,
    )

    # Save the original upload
    original = storage.original_path(placeholder, suffix)
    with original.open("wb") as f:
        shutil.copyfileobj(file.file, f, length=1024 * 1024)
    size = original.stat().st_size
    if size > settings.max_upload_mb * 1024 * 1024:
        original.unlink(missing_ok=True)
        storage.delete_extraction(placeholder)
        raise HTTPException(status_code=413, detail=f"File too large; limit is {settings.max_upload_mb} MB")

    # Render to PIL images
    try:
        if suffix in SUPPORTED_PDF_SUFFIXES:
            images = render_pdf(original)
        else:
            images = [load_image(original)]
        if not images:
            raise ValueError("No pages to extract")
    except Exception as exc:
        original.unlink(missing_ok=True)
        storage.delete_extraction(placeholder)
        logger.exception("extract.render_failed")
        raise HTTPException(status_code=400, detail=f"Failed to render file: {exc}") from exc

    # Persist per-page PNG thumbnails for the result page
    for i, img in enumerate(images, start=1):
        save_png(img, storage.page_path(placeholder, i))

    # Run extraction
    try:
        if schema_key == "custom":
            custom_fields = _parse_custom_fields(custom_fields_json)
            outcome = extract_with_custom(images, custom_fields)
        else:
            if schema_key not in SCHEMAS:
                raise HTTPException(status_code=400, detail=f"Unknown schema: {schema_key}")
            outcome = extract_with_predefined(images, schema_key)
    except Exception as exc:
        original.unlink(missing_ok=True)
        storage.delete_extraction(placeholder)
        logger.exception("extract.api_failed")
        raise HTTPException(status_code=502, detail=f"Extraction failed: {exc}") from exc

    # Update the placeholder row with the real values.
    db = storage.get_connection()
    db.execute(
        """
        UPDATE extractions SET
            schema_key = ?, schema_label = ?, page_count = ?, data_json = ?,
            custom_schema_json = ?, tokens_input = ?, tokens_output = ?, duration_ms = ?
        WHERE id = ?
        """,
        (
            outcome.schema_key,
            outcome.schema_label,
            outcome.page_count,
            json.dumps(outcome.data, default=str),
            json.dumps(outcome.custom_schema) if outcome.custom_schema else None,
            outcome.tokens_input,
            outcome.tokens_output,
            outcome.duration_ms,
            placeholder,
        ),
    )
    db.commit()

    return RedirectResponse(url=f"/result/{placeholder}", status_code=303)


def _parse_custom_fields(raw: str | None) -> list[CustomFieldSpec]:
    if not raw:
        raise HTTPException(status_code=400, detail="Custom schema requires fields")
    try:
        items = json.loads(raw)
        return [CustomFieldSpec.model_validate(it) for it in items]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid custom_fields_json: {exc}") from exc


# ─────────────────────── Edit / save / delete ───────────────────────

class SaveBody(BaseModel):
    data: dict


@router.post("/result/{extraction_id}/save")
async def save_data(extraction_id: str, body: SaveBody) -> JSONResponse:
    if not storage.get_extraction(extraction_id):
        raise HTTPException(status_code=404, detail="not found")
    ok = storage.update_extraction_data(extraction_id, body.data)
    return JSONResponse({"ok": ok})


@router.delete("/result/{extraction_id}")
async def delete_result(extraction_id: str) -> JSONResponse:
    if not storage.get_extraction(extraction_id):
        raise HTTPException(status_code=404, detail="not found")
    shutil.rmtree(storage.extraction_dir(extraction_id), ignore_errors=True)
    storage.delete_extraction(extraction_id)
    return JSONResponse({"ok": True})


# ─────────────────────── API export endpoints ───────────────────────

@router.get("/api/result/{extraction_id}.json")
async def export_json(extraction_id: str) -> JSONResponse:
    ext = storage.get_extraction(extraction_id)
    if not ext:
        raise HTTPException(status_code=404, detail="not found")
    return JSONResponse(content={
        "id": ext.id,
        "filename": ext.filename,
        "schema": ext.schema_key,
        "data": ext.data,
        "created_at": ext.created_at,
    })


@router.get("/api/result/{extraction_id}.csv")
async def export_csv(extraction_id: str) -> StreamingResponse:
    """Export tabular fragments (invoice line items, receipt items, custom lists) as CSV."""
    ext = storage.get_extraction(extraction_id)
    if not ext:
        raise HTTPException(status_code=404, detail="not found")
    data = ext.data

    rows: list[dict] = []
    if ext.schema_key == "invoice":
        for item in data.get("line_items", []) or []:
            rows.append(item)
    elif ext.schema_key == "receipt":
        for item in data.get("items", []) or []:
            rows.append(item)
    else:
        # Flatten top-level scalar fields into a single row
        flat: dict = {}
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                flat[k] = json.dumps(v, default=str)
            else:
                flat[k] = v
        rows = [flat]

    if not rows:
        raise HTTPException(status_code=204, detail="no tabular data")

    field_set: list[str] = []
    for r in rows:
        for k in r.keys():
            if k not in field_set:
                field_set.append(k)

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=field_set)
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k, "") for k in field_set})
    buf.seek(0)

    filename = f"{ext.id}_{ext.schema_key}.csv"
    return StreamingResponse(
        iter([buf.getvalue().encode("utf-8")]),
        media_type="text/csv",
        headers={"content-disposition": f'attachment; filename="{filename}"'},
    )
