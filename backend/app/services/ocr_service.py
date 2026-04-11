"""OCR service: Tesseract (+ optional EasyOCR) with preprocessing."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from app.config import get_settings
from app.schemas.submission import OCRResult
from app.services.image_preprocess import preprocess_for_ocr

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None  # type: ignore

try:
    import pytesseract
except ImportError:  # pragma: no cover
    pytesseract = None  # type: ignore


def _lang_tesseract(language_hint: str) -> str:
    if language_hint.lower().startswith("hi"):
        return "hin+eng"
    return "eng"


def _pil_to_cv_bgr(pil_image: Image.Image) -> np.ndarray:
    rgb = np.array(pil_image.convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def _bytes_to_pil(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGB")


def extract_text_from_image_bytes(
    data: bytes,
    language_hint: str = "en",
    mime_type: Optional[str] = None,
) -> OCRResult:
    """
    Run preprocessing + Tesseract OCR on image bytes.

    For PDF, caller should rasterize pages first (see `extract_text_from_pdf_bytes`).
    """
    settings = get_settings()
    if pytesseract is None:
        raise RuntimeError("pytesseract is not installed.")
    if cv2 is None:
        raise RuntimeError("opencv is not installed.")
    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

    pil = _bytes_to_pil(data)
    bgr = _pil_to_cv_bgr(pil)
    pre = preprocess_for_ocr(bgr)
    pil_bin = Image.fromarray(cv2.cvtColor(pre.binary_bgr, cv2.COLOR_BGR2RGB))

    lang = _lang_tesseract(language_hint)
    custom_config = r"--oem 3 --psm 3"
    text = pytesseract.image_to_string(pil_bin, lang=lang, config=custom_config)
    text = text.strip()
    return OCRResult(text=text, preprocessing_notes=pre.notes)


def extract_text_from_pdf_bytes(data: bytes, language_hint: str = "en") -> OCRResult:
    """Rasterize each PDF page and concatenate OCR text."""
    try:
        from pdf2image import convert_from_bytes
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("pdf2image required for PDF OCR; install poppler in Docker.") from e

    images = convert_from_bytes(data, dpi=200)
    parts: list[str] = []
    all_notes: list[str] = []
    for i, pil in enumerate(images):
        buf = io.BytesIO()
        pil.save(buf, format="PNG")
        page = extract_text_from_image_bytes(buf.getvalue(), language_hint=language_hint, mime_type="image/png")
        parts.append(page.text)
        all_notes.extend([f"Page {i + 1}: {n}" for n in page.preprocessing_notes])
    return OCRResult(text="\n\n".join(parts).strip(), preprocessing_notes=all_notes)


def extract_text_auto(
    data: bytes,
    filename: str,
    language_hint: str = "en",
    mime_type: Optional[str] = None,
) -> OCRResult:
    """Dispatch by file extension / mime for PDF vs image."""
    ext = Path(filename or "").suffix.lower()
    is_pdf = ext == ".pdf" or (mime_type and "pdf" in mime_type.lower())
    if is_pdf:
        return extract_text_from_pdf_bytes(data, language_hint=language_hint)
    return extract_text_from_image_bytes(data, language_hint=language_hint, mime_type=mime_type)
