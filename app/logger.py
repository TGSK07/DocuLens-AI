import logging
import sys

from app.config import settings


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    if any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        return
    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)
    root.addHandler(handler)

    for name in ("uvicorn.access", "PIL", "matplotlib.font_manager"):
        logging.getLogger(name).setLevel(logging.WARNING)


logger = logging.getLogger("doc-extractor")
