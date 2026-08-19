"""Image preprocessing + base64 encoding for the Gemini API."""
from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image, ImageOps

from app.config import settings


def load_image(path: Path) -> Image.Image:
    image = Image.open(path)
    # Respect EXIF orientation
    image = ImageOps.exif_transpose(image)
    if image.mode not in {"RGB", "RGBA"}:
        image = image.convert("RGB")
    return image


def downscale(image: Image.Image, max_long_edge: int | None = None) -> Image.Image:
    """Cap the long edge to limit upload size to Gemini.

    The model performs well at 1024-2048 long-edge; anything larger wastes
    tokens with no quality gain.
    """
    limit = max_long_edge or settings.max_image_long_edge_px
    w, h = image.size
    long_edge = max(w, h)
    if long_edge <= limit:
        return image
    ratio = limit / long_edge
    new_size = (max(1, int(w * ratio)), max(1, int(h * ratio)))
    return image.resize(new_size, Image.LANCZOS)


def to_png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def to_base64(image: Image.Image) -> str:
    return base64.b64encode(to_png_bytes(image)).decode("ascii")


def save_png(image: Image.Image, path: Path) -> int:
    """Save a PIL image as PNG, return bytes written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)
    return path.stat().st_size
