"""
Optional cloud OCR: Google Cloud Vision (document text) and Azure Document Intelligence (prebuilt-read).

Enable only when you set credentials; otherwise the pipeline uses local neural OCR.

- OCR_USE_GOOGLE_VISION=1
  - GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json, or
  - OCR_GCP_USE_ADC=1 (Application Default Credentials, e.g. gcloud auth application-default login)
- OCR_USE_AZURE_READ=1
  - AZURE_FORM_RECOGNIZER_ENDPOINT=https://<resource>.cognitiveservices.azure.com/
  - AZURE_FORM_RECOGNIZER_KEY=<key>
  Aliases: AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT, AZURE_DOCUMENT_INTELLIGENCE_KEY

Control blend with local models via OCR_CLOUD_MODE: cascade (default) | ensemble | off.
See ml/ocr_module.py _run_best_ocr_on_pages.
"""

from __future__ import annotations

import io
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

_MAX_PNG_BYTES = 3_800_000
_MAX_LONG_EDGE = 3000


def _env_on(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def google_vision_wanted() -> bool:
    return _env_on("OCR_USE_GOOGLE_VISION")


def azure_read_wanted() -> bool:
    return _env_on("OCR_USE_AZURE_READ")


def _azure_endpoint() -> str:
    for key in (
        "AZURE_FORM_RECOGNIZER_ENDPOINT",
        "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT",
    ):
        v = os.getenv(key, "").strip()
        if v:
            return v.rstrip("/")
    return ""


def _azure_key() -> str:
    for key in (
        "AZURE_FORM_RECOGNIZER_KEY",
        "AZURE_DOCUMENT_INTELLIGENCE_KEY",
    ):
        v = os.getenv(key, "").strip()
        if v:
            return v
    return ""


def google_configured() -> bool:
    if not google_vision_wanted():
        return False
    if _env_on("OCR_GCP_USE_ADC"):
        return True
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip():
        return True
    return bool(os.getenv("GOOGLE_API_KEY", "").strip())


def azure_configured() -> bool:
    if not azure_read_wanted():
        return False
    return bool(_azure_endpoint() and _azure_key())


def any_cloud_configured() -> bool:
    return google_configured() or azure_configured()


def _shrink_for_api(im: "Image.Image") -> "Image.Image":
    from PIL import Image

    w, h = im.size
    m = max(w, h)
    if m <= _MAX_LONG_EDGE:
        return im
    scale = _MAX_LONG_EDGE / m
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    return im.resize((nw, nh), resample=Image.Resampling.LANCZOS)


def _page_to_png_bytes(im: "Image.Image") -> bytes:
    from PIL import Image

    if not isinstance(im, Image.Image):
        raise TypeError("expected PIL.Image")
    im = im.convert("RGB")
    im = _shrink_for_api(im)
    quality = 90
    while quality >= 40:
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True, compress_level=6)
        data = buf.getvalue()
        if len(data) <= _MAX_PNG_BYTES:
            return data
        w, h = im.size
        im = im.resize((max(1, int(w * 0.88)), max(1, int(h * 0.88))), resample=Image.Resampling.LANCZOS)
        quality -= 10
    return data


def google_document_text(pages: list, notes: list[str]) -> str:
    from google.cloud import vision

    client = vision.ImageAnnotatorClient()
    blocks: list[str] = []
    for i, page in enumerate(pages):
        content = _page_to_png_bytes(page)
        image = vision.Image(content=content)
        response = client.document_text_detection(image=image)
        err = getattr(response, "error", None)
        if err and getattr(err, "message", None):
            code = getattr(err, "code", 0) or 0
            notes.append(f"Google Vision page {i + 1}: API error {code} {err.message}.")
            continue
        t = (response.full_text_annotation.text or "").strip() if response.full_text_annotation else ""
        if t:
            blocks.append(t)
        else:
            notes.append(f"Google Vision page {i + 1}: no text returned.")
    if not blocks:
        return ""
    return "\n\n".join(blocks)


def azure_read_text(pages: list, notes: list[str]) -> str:
    from azure.ai.formrecognizer import DocumentAnalysisClient
    from azure.core.credentials import AzureKeyCredential

    endpoint = _azure_endpoint()
    key = _azure_key()
    if not endpoint or not key:
        return ""
    client = DocumentAnalysisClient(endpoint, AzureKeyCredential(key))
    blocks: list[str] = []
    for i, page in enumerate(pages):
        png = _page_to_png_bytes(page)
        poller = client.begin_analyze_document(
            "prebuilt-read",
            document=io.BytesIO(png),
        )
        result = poller.result()
        raw = (getattr(result, "content", None) or "").strip()
        if raw:
            blocks.append(raw)
            continue
        lines: list[str] = []
        if result.paragraphs:
            for p in result.paragraphs:
                c = (p.content or "").strip()
                if c:
                    lines.append(c)
        elif result.pages:
            for pg in result.pages:
                for line in getattr(pg, "lines", None) or []:
                    c = (getattr(line, "content", None) or "").strip()
                    if c:
                        lines.append(c)
        if lines:
            blocks.append("\n".join(lines))
        else:
            notes.append(f"Azure Read page {i + 1}: no text returned.")
    if not blocks:
        return ""
    return "\n\n".join(blocks)
