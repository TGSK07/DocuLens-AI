"""Google Gemini vision-based document extractor.

The flow:
  1. Build a JSON Schema from the selected document type.
  2. Send the page images + a text instruction to Gemini.
  3. Use `response_mime_type="application/json"` with `response_schema` so
     the model is forced to return structured JSON matching the schema.
  4. Parse the JSON response — that's our structured output.
  5. Validate with Pydantic (for predefined schemas) before returning.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types
from PIL import Image

from app.config import settings
from app.core.image import downscale, to_png_bytes
from app.core.prompts import build_custom_system_prompt, build_system_prompt
from app.core.schemas import (
    CustomFieldSpec,
    SchemaInfo,
    build_custom_schema,
    get_schema,
)
from app.logger import logger

_client = genai.Client(api_key=settings.gemini_api_key)


@dataclass
class ExtractionOutcome:
    data: dict[str, Any]
    page_count: int
    tokens_input: int
    tokens_output: int
    duration_ms: int
    schema_key: str
    schema_label: str
    custom_schema: dict[str, Any] | None


def _make_image_parts(images: list[Image.Image]) -> list[types.Part]:
    """Convert PIL images into Gemini inline-data parts."""
    parts: list[types.Part] = []
    for img in images[: settings.max_pages_per_request]:
        prepared = downscale(img)
        raw_bytes = to_png_bytes(prepared)
        parts.append(
            types.Part.from_bytes(data=raw_bytes, mime_type="image/png")
        )
    return parts


def _parse_response(response: types.GenerateContentResponse) -> dict[str, Any]:
    """Extract the structured JSON from Gemini's response."""
    text = response.text
    if not text:
        raise RuntimeError(
            "Gemini returned an empty response. "
            f"finish_reason={response.candidates[0].finish_reason if response.candidates else 'unknown'}"
        )
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Gemini returned invalid JSON: {exc}\nRaw response: {text[:500]}"
        ) from exc


def _get_usage(response: types.GenerateContentResponse) -> tuple[int, int]:
    """Extract input/output token counts from the response."""
    usage = response.usage_metadata
    if usage:
        return (usage.prompt_token_count or 0, usage.candidates_token_count or 0)
    return (0, 0)


def _strip_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """Inline `$defs` references so the schema is self-contained.

    Gemini accepts standard JSON Schema, but for clarity we keep a
    minimal, well-formed object.
    """
    return schema


# ─────────────────────────── Predefined schemas ───────────────────────────

def extract_with_predefined(images: list[Image.Image], schema_key: str) -> ExtractionOutcome:
    info: SchemaInfo = get_schema(schema_key)
    json_schema = _strip_refs(info.json_schema())

    system_prompt = build_system_prompt(info.label, info.guidance)

    image_parts = _make_image_parts(images)
    user_text = (
        f"Please extract this {info.label.lower()}. "
        f"The document has {len(image_parts)} page(s) — they are provided above in order."
    )

    contents = [*image_parts, user_text]

    started = time.perf_counter()
    response = _client.models.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=settings.gemini_max_tokens,
            response_mime_type="application/json",
            response_schema=json_schema,
        ),
    )
    duration_ms = int((time.perf_counter() - started) * 1000)

    raw = _parse_response(response)
    tokens_in, tokens_out = _get_usage(response)

    if info.model is not None:
        # Validate. If validation fails we surface a helpful error.
        validated = info.model.model_validate(raw)
        data = validated.model_dump(mode="json")
    else:
        data = raw

    logger.info(
        "extract.done schema=%s pages=%d tokens=(%d in / %d out) ms=%d",
        schema_key,
        len(image_parts),
        tokens_in,
        tokens_out,
        duration_ms,
    )

    return ExtractionOutcome(
        data=data,
        page_count=len(image_parts),
        tokens_input=tokens_in,
        tokens_output=tokens_out,
        duration_ms=duration_ms,
        schema_key=info.key,
        schema_label=info.label,
        custom_schema=None,
    )


# ─────────────────────────── Custom schema ───────────────────────────

def extract_with_custom(
    images: list[Image.Image],
    fields: list[CustomFieldSpec],
) -> ExtractionOutcome:
    if not fields:
        raise ValueError("Custom schema requires at least one field")

    json_schema = build_custom_schema(fields)

    field_summary = "\n".join(
        f"  - {f.name} ({f.type})" + (f": {f.description}" if f.description else "")
        for f in fields
    )

    system_prompt = build_custom_system_prompt(field_summary)

    image_parts = _make_image_parts(images)
    user_text = (
        f"Extract the user-defined fields from this document "
        f"({len(image_parts)} page(s) above, in order)."
    )

    contents = [*image_parts, user_text]

    started = time.perf_counter()
    response = _client.models.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=settings.gemini_max_tokens,
            response_mime_type="application/json",
            response_schema=json_schema,
        ),
    )
    duration_ms = int((time.perf_counter() - started) * 1000)

    raw = _parse_response(response)
    tokens_in, tokens_out = _get_usage(response)

    logger.info(
        "extract.done schema=custom pages=%d tokens=(%d in / %d out) ms=%d",
        len(image_parts),
        tokens_in,
        tokens_out,
        duration_ms,
    )

    return ExtractionOutcome(
        data=raw,
        page_count=len(image_parts),
        tokens_input=tokens_in,
        tokens_output=tokens_out,
        duration_ms=duration_ms,
        schema_key="custom",
        schema_label="Custom",
        custom_schema={
            "fields": [
                {"name": f.name, "type": f.type, "description": f.description}
                for f in fields
            ]
        },
    )
