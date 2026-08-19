"""PDF → list of PIL images using pypdfium2 (pure Python, no system deps)."""
from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image

from app.config import settings


def render_pdf(path: Path) -> list[Image.Image]:
    """Rasterise every page of a PDF to a PIL image.

    Returns at most ``settings.max_pages_per_request`` pages.
    """
    pdf = pdfium.PdfDocument(str(path))
    n_pages = len(pdf)
    max_pages = max(1, settings.max_pages_per_request)

    images: list[Image.Image] = []
    try:
        for i in range(min(n_pages, max_pages)):
            page = pdf[i]
            # pypdfium2 wants a "scale" in PDF units; 72 dpi is 1:1, so scale = dpi/72
            scale = settings.pdf_render_dpi / 72
            bitmap = page.render(scale=scale)
            pil_image = bitmap.to_pil()
            # Convert palette modes to RGB so Pillow can resize predictably
            if pil_image.mode not in {"RGB", "RGBA"}:
                pil_image = pil_image.convert("RGB")
            images.append(pil_image)
    finally:
        pdf.close()
    return images
