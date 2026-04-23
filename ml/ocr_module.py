from __future__ import annotations

import os
import re
import ssl
import threading
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


def _configure_ssl_for_downloads() -> None:
    """
    EasyOCR (first run) and similar code use urllib; macOS/embedded Pythons often fail with
    CERTIFICATE_VERIFY_FAILED unless a CA bundle is on SSL_CERT_FILE.
    By default we point SSL* env vars at certifi’s bundle. Set OCR_USE_CERTIFI=0 to skip.
    Set OCR_ALLOW_INSECURE_SSL=1 only on trusted networks (disables verification — dev use).
    """
    if os.environ.get("OCR_ALLOW_INSECURE_SSL", "").strip().lower() in {"1", "true", "yes", "on"}:
        ssl._create_default_https_context = ssl._create_unverified_context  # noqa: S506
        return
    if os.environ.get("OCR_USE_CERTIFI", "1").strip().lower() in {"0", "false", "no", "off"}:
        return
    try:
        import certifi

        ca = certifi.where()
    except ImportError:
        return
    os.environ["SSL_CERT_FILE"] = ca
    os.environ["REQUESTS_CA_BUNDLE"] = ca
    os.environ["CURL_CA_BUNDLE"] = ca


_configure_ssl_for_downloads()


@dataclass
class OCRResult:
    extracted_text: str
    engine_used: str
    notes: list[str]


RASTER_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}

_easyocr_lock = threading.Lock()
_easyocr_reader: object | None = None

_rapid_ocr_lock = threading.Lock()
_rapid_ocr: object | None = None


def _load_image_pages(path: Path) -> list[Image.Image]:
    """Each PIL frame (multi-page TIFF, etc.) as its own RGB page."""
    pages: list[Image.Image] = []
    with Image.open(path) as img:
        n = int(getattr(img, "n_frames", 1) or 1)
        for i in range(n):
            img.seek(i)
            pages.append(img.convert("RGB").copy())
    return pages


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _transcript_normalize(text: str) -> str:
    """Keep line breaks; clean spacing (better for answer scripts and neural OCR)."""
    lines: list[str] = []
    for line in text.splitlines():
        t = re.sub(r"[ \t]+", " ", line).strip()
        if t:
            lines.append(t)
    return "\n".join(lines) if lines else ""


def _spell_and_grammar_normalize(text: str) -> str:
    """Single-line style normalize (used for Tesseract / legacy path only)."""
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s([?.!,;:])", r"\1", text)
    return text


def _segment_lines_words(text: str) -> tuple[int, int]:
    lines = [line for line in text.splitlines() if line.strip()]
    words = [w for w in re.findall(r"[A-Za-z0-9']+", text) if w.strip()]
    return len(lines) if lines else (1 if text.strip() else 0), len(words)


def _word_count(s: str) -> int:
    return len(re.findall(r"\b[\w']+\b", s, re.UNICODE))


def _text_looks_suspiciously_noisy(s: str) -> bool:
    """Heuristic for skipping bad embedded-PDF text (not for filtering neural output). Kept lenient for short but valid answers."""
    s = s.strip()
    if len(s) < 8:
        return True
    letters = sum(1 for c in s if c.isalpha())
    if len(s) and letters / len(s) < 0.10:
        return True
    # Unusual control / replacement density
    bad = sum(1 for c in s if ord(c) > 0xFFFF or (ord(c) < 32 and c not in "\n\t"))
    if len(s) and bad / len(s) > 0.08:
        return True
    return False


def _transcript_quality_score(s: str) -> float:
    """
    Heuristic (higher = better): length matters — short correct answers no longer lose to long garbage.
    Used to pick between neural backends (RapidOCR vs EasyOCR).
    """
    s = s.strip()
    if not s:
        return 0.0
    letters = sum(1 for c in s if c.isalpha())
    words = _word_count(s)
    pipey = s.count("|") + s.count("~")
    alratio = letters / max(len(s), 1)
    # Reward raw length slightly so a fuller extraction wins when scores are close
    len_boost = min(len(s), 8000) * 0.00015
    return (words * 1.2 + letters * 0.08) * alratio - pipey * 0.25 + len_boost


def _maybe_preprocess_for_ocr(arr: np.ndarray) -> np.ndarray:
    """Optional CLAHE in LAB (helps faint pen / lighting). Set OCR_PREPROCESS=0 to skip."""
    if not _env_bool("OCR_PREPROCESS", True):
        return arr
    try:
        import cv2
    except ImportError:
        return arr
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l_ch, a_ch, b_ch = cv2.split(lab)
    clip = float(os.getenv("OCR_CLAHE_CLIP", "1.5"))
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8))
    l2 = clahe.apply(l_ch)
    merged = cv2.merge((l2, a_ch, b_ch))
    bgr2 = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
    return cv2.cvtColor(bgr2, cv2.COLOR_BGR2RGB)


def _bbox_reading_order_key(bbox) -> tuple[float, float]:
    """
    Sort key: top edge, then left — natural reading order for detected text boxes
    (same idea as layout-ordered LINE output in cloud document OCR, without network cost).
    """
    if bbox is None:
        return (0.0, 0.0)
    try:
        arr = np.asarray(bbox, dtype=np.float64).reshape(-1, 2)
        if arr.size == 0:
            return (0.0, 0.0)
        return (float(np.min(arr[:, 1])), float(np.min(arr[:, 0])))
    except Exception:
        return (0.0, 0.0)


def _upscale_if_small_raster(im: Image.Image) -> Image.Image:
    """
    Phone / screenshot uploads are often < ~1000 px wide; models work better on larger text.
    Set OCR_UPSCALE_SMALL_IMAGES=0 to disable, OCR_MIN_IMAGE_EDGE to change threshold (px).
    """
    if not _env_bool("OCR_UPSCALE_SMALL_IMAGES", True):
        return im
    w, h = im.size
    min_edge = int(float(os.getenv("OCR_MIN_IMAGE_EDGE", "1000")))
    m = max(w, h)
    if m >= min_edge or m < 1:
        return im
    scale = (min_edge / m) * 1.02
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    return im.resize((nw, nh), Image.Resampling.LANCZOS)


# --- Tesseract / OCRmyPDF (optional legacy) -------------------------------------------------


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _tesseract_languages() -> list[str]:
    raw = os.getenv("OCRMYPDF_LANGUAGE", "eng")
    parts = [p.strip() for p in re.split(r"[,+]", raw) if p.strip()]
    return parts if parts else ["eng"]


def _tesseract_thresholding_int() -> int | None:
    name = os.getenv("OCRMYPDF_TESSERACT_THRESHOLDING", "adaptive-otsu").strip().lower()
    if name in {"", "default", "auto"}:
        return None
    try:
        from ocrmypdf._exec.tesseract import ThresholdingMethod
    except ImportError:
        return None
    mapping = {
        "otsu": ThresholdingMethod.OTSU,
        "adaptive-otsu": ThresholdingMethod.ADAPTIVE_OTSU,
        "sauvola": ThresholdingMethod.SAUVOLA,
    }
    m = mapping.get(name)
    return int(m) if m is not None else int(ThresholdingMethod.ADAPTIVE_OTSU)


def _ocrmypdf_base_kwargs() -> dict:
    return {
        "force_ocr": _env_bool("OCRMYPDF_FORCE_OCR", True),
        "oversample": int(os.getenv("OCRMYPDF_OVERSAMPLE", "600")),
        "optimize": int(os.getenv("OCRMYPDF_OPTIMIZE", "1")),
        "deskew": _env_bool("OCRMYPDF_DESKEW", True),
        "rotate_pages": _env_bool("OCRMYPDF_ROTATE_PAGES", True),
        "language": _tesseract_languages(),
        "skip_text": _env_bool("OCRMYPDF_SKIP_TEXT", False),
        "clean": _env_bool("OCRMYPDF_CLEAN", True),
        "clean_final": _env_bool("OCRMYPDF_CLEAN_FINAL", True),
        "jpg_quality": int(os.getenv("OCRMYPDF_JPG_QUALITY", "95")),
        "png_quality": int(os.getenv("OCRMYPDF_PNG_QUALITY", "95")),
    }


def _ocrmypdf_tesseract_kwargs() -> dict:
    out: dict = {
        "tesseract_oem": int(os.getenv("OCRMYPDF_TESSERACT_OEM", "1")),
        "tesseract_timeout": float(os.getenv("OCRMYPDF_TESSERACT_TIMEOUT", "600")),
        "tesseract_non_ocr_timeout": float(os.getenv("OCRMYPDF_TESSERACT_NON_OCR_TIMEOUT", "180")),
        "progress_bar": False,
    }
    psm = os.getenv("OCRMYPDF_TESSERACT_PSM", "3").strip()
    if psm:
        out["tesseract_pagesegmode"] = int(psm)
    tthr = _tesseract_thresholding_int()
    if tthr is not None:
        out["tesseract_thresholding"] = tthr
    return out


def _ocrmypdf_kwargs(*, image_dpi: int | None) -> dict:
    kw = {**_ocrmypdf_base_kwargs(), **_ocrmypdf_tesseract_kwargs()}
    if image_dpi is not None and image_dpi > 0:
        kw["image_dpi"] = int(image_dpi)
    return kw


def _fitz_extract_from_pdf(path: Path) -> str:
    import fitz

    out: list[str] = []
    doc = fitz.open(str(path))
    try:
        for page in doc:
            t = (page.get_text() or "").strip()
            if t:
                out.append(t)
    finally:
        doc.close()
    return "\n\n".join(out)


def _fitz_extract_normalized(pdf_path: Path, notes: list[str]) -> str:
    import fitz

    full_text = ""
    doc = fitz.open(str(pdf_path))
    try:
        n = len(doc)
        for page in doc:
            full_text += page.get_text() or ""
        notes.append(f"fitz: read {n} page(s) from OCRmyPDF output.")
    finally:
        doc.close()
    return _spell_and_grammar_normalize(full_text)


def _temp_pdf_path() -> Path:
    t = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    t.close()
    return Path(t.name)


def _run_ocrmypdf(input_pdf: Path, notes: list[str], *, image_dpi: int | None = None) -> str:
    try:
        import ocrmypdf
    except ImportError as exc:
        raise RuntimeError(
            "ocrmypdf is not installed. Run: pip install ocrmypdf "
            "and install Tesseract + Ghostscript (e.g. brew install tesseract ghostscript)."
        ) from exc

    tmp_in = _temp_pdf_path()
    tmp_out = _temp_pdf_path()
    try:
        tmp_in.write_bytes(input_pdf.read_bytes())
        notes.append(f"Staged PDF for OCRmyPDF (temp input): {tmp_in}")
        if image_dpi is not None:
            notes.append(f"image_dpi={image_dpi} (must match embedded raster resolution).")

        ocrmypdf.ocr(
            str(tmp_in),
            str(tmp_out),
            **_ocrmypdf_kwargs(image_dpi=image_dpi),
        )
        notes.append("OCRmyPDF output (temp file).")
        return _fitz_extract_normalized(tmp_out, notes)
    finally:
        tmp_in.unlink(missing_ok=True)
        tmp_out.unlink(missing_ok=True)


def _raster_embed_dpi() -> int:
    return int(float(os.getenv("OCR_IMAGE_TO_PDF_DPI", "500")))


def _images_to_temp_pdf(images: list[Image.Image], notes: list[str]) -> tuple[Path, int]:
    if not images:
        raise ValueError("No images to convert.")
    out = _temp_pdf_path()
    dpi = _raster_embed_dpi()
    res = float(dpi)
    first, *rest = [im.convert("RGB") for im in images]
    if rest:
        first.save(str(out), "PDF", resolution=res, save_all=True, append_images=rest)
    else:
        first.save(str(out), "PDF", resolution=res)
    notes.append(f"Wrapped {len(images)} raster page(s) in temp PDF at {dpi} dpi: {out}")
    return out, dpi


# --- EasyOCR (neural; better for handwriting / uneven scans than Tesseract) ---------------


def _easyocr_min_conf() -> float:
    return float(os.getenv("EASYOCR_MIN_CONFIDENCE", "0.01"))


def _get_easyocr_reader():
    global _easyocr_reader
    with _easyocr_lock:
        if _easyocr_reader is not None:
            return _easyocr_reader
        import easyocr

        raw = os.getenv("EASYOCR_LANG", "en")
        langs = [p.strip() for p in re.split(r"[,+]", raw) if p.strip()] or ["en"]
        gpu = os.getenv("EASYOCR_USE_GPU", "0").strip().lower() in {"1", "true", "yes", "on"}
        _easyocr_reader = easyocr.Reader(langs, gpu=gpu, verbose=False)  # type: ignore[assignment]
        return _easyocr_reader


def _pil_to_rgb_numpy(im: Image.Image) -> np.ndarray:
    return _maybe_preprocess_for_ocr(np.asarray(im.convert("RGB")))


def _get_rapid_ocr():
    global _rapid_ocr
    with _rapid_ocr_lock:
        if _rapid_ocr is not None:
            return _rapid_ocr
        from rapidocr_onnxruntime import RapidOCR

        _rapid_ocr = RapidOCR()
        return _rapid_ocr


def _run_rapid_on_pages(pages: list[Image.Image], notes: list[str]) -> str:
    ocr = _get_rapid_ocr()
    min_s = float(os.getenv("RAPID_OCR_LINE_MIN_SCORE", "0.1"))
    box_thresh = float(os.getenv("RAPID_OCR_BOX_THRESH", "0.2"))
    blocks: list[str] = []
    for i, im in enumerate(pages):
        im = _upscale_if_small_raster(im)
        arr = np.asarray(im.convert("RGB"))
        arr = _maybe_preprocess_for_ocr(arr)
        ocr_res, _times = ocr(
            arr,
            box_thresh=box_thresh,
            text_score=float(os.getenv("RAPID_OCR_TEXT_SCORE", "0.25")),
        )
        scored: list[tuple[tuple[float, float], str]] = []
        if ocr_res:
            for row in ocr_res:
                if not row or len(row) < 2:
                    continue
                text = row[1]
                if not isinstance(text, str) or not text.strip():
                    continue
                sc = 1.0
                if len(row) > 2 and isinstance(row[2], (int, float)):
                    sc = float(row[2])
                if sc < min_s:
                    continue
                key = _bbox_reading_order_key(row[0])
                scored.append((key, text.strip()))
        scored.sort(key=lambda x: (x[0][0], x[0][1]))
        page_lines = [t[1] for t in scored]
        page_text = "\n".join(page_lines) if page_lines else ""
        if page_text:
            blocks.append(page_text)
        notes.append(f"RapidOCR page {i + 1}/{len(pages)}: {len(page_lines)} line(s).")
    return _transcript_normalize("\n\n".join(blocks))


def _easyocr_readtext_item(item) -> tuple[str, float] | None:
    """EasyOCR may return (bbox, text, conf) or (bbox, text) with paragraph=True, or a plain str if detail=0."""
    if isinstance(item, str):
        return (item, 1.0)
    if not isinstance(item, (list, tuple)) or len(item) < 2:
        return None
    if len(item) == 2:
        text, conf = item[1], 1.0
    else:
        text, conf = item[1], item[2]
    if not isinstance(text, str):
        return None
    c = 1.0 if conf is None else float(conf)
    return (text, c)


def _run_easyocr_on_pages(pages: list[Image.Image], notes: list[str]) -> str:
    reader = _get_easyocr_reader()
    min_c = _easyocr_min_conf()
    use_paragraph = _env_bool("EASYOCR_PARAGRAPH", False)
    rt_kw = {
        "detail": 1,
        "paragraph": use_paragraph,
        "mag_ratio": float(os.getenv("EASYOCR_MAG_RATIO", "1.5")),
        "canvas_size": int(os.getenv("EASYOCR_CANVAS_SIZE", "2560")),
        "text_threshold": float(os.getenv("EASYOCR_TEXT_THRESHOLD", "0.32")),
        "low_text": float(os.getenv("EASYOCR_LOW_TEXT", "0.22")),
    }
    blocks: list[str] = []
    for i, im in enumerate(pages):
        im = _upscale_if_small_raster(im)
        arr = _pil_to_rgb_numpy(im)
        raw = reader.readtext(arr, **rt_kw)
        scored: list[tuple[tuple[float, float], str]] = []
        for row in raw:
            parsed = _easyocr_readtext_item(row)
            if not parsed:
                continue
            text, conf = parsed
            if not text or conf < min_c:
                continue
            if isinstance(row, str):
                bbox = None
            else:
                bbox = row[0] if isinstance(row, (list, tuple)) and len(row) > 0 else None
            scored.append((_bbox_reading_order_key(bbox), text.strip()))
        scored.sort(key=lambda x: (x[0][0], x[0][1]))
        page_lines = [t[1] for t in scored]
        page_text = "\n".join(page_lines) if page_lines else ""
        if page_text:
            blocks.append(page_text)
        notes.append(f"EasyOCR page {i + 1}/{len(pages)}: {len(page_lines)} text region(s).")
    return _transcript_normalize("\n\n".join(blocks))


def _neural_backend_mode() -> str:
    # best = run both RapidOCR + EasyOCR when possible, keep transcript with higher _transcript_quality_score
    m = os.getenv("OCR_NEURAL_BACKEND", "best").strip().lower()
    if m in ("best", "ensemble", "auto", "both"):
        return "best"
    if m in ("rapid", "rapidocr", "paddle", "onnx"):
        return "rapid"
    if m in ("easy", "easyocr", "craft"):
        return "easyocr"
    return "best"


def _run_neural_ocr_on_pages(pages: list[Image.Image], notes: list[str]) -> tuple[str, str]:
    """
    Returns (transcript, engine label). Default runs RapidOCR + EasyOCR and picks the better transcript.
    """
    mode = _neural_backend_mode()
    if mode == "rapid":
        try:
            return _run_rapid_on_pages(pages, notes), "rapidocr"
        except Exception as exc:
            notes.append(f"RapidOCR failed ({exc!s}); trying EasyOCR.")
            return _run_easyocr_on_pages(pages, notes), "easyocr"

    if mode == "easyocr":
        return _run_easyocr_on_pages(pages, notes), "easyocr"

    # best: two candidates, no extra cost if one stack missing
    candidates: list[tuple[str, str, float]] = []
    try:
        t_r = _run_rapid_on_pages(pages, notes)
        if t_r.strip():
            candidates.append((t_r, "rapidocr", _transcript_quality_score(t_r)))
    except Exception as exc:
        notes.append(f"RapidOCR: {exc!s}")
    try:
        t_e = _run_easyocr_on_pages(pages, notes)
        if t_e.strip():
            candidates.append((t_e, "easyocr", _transcript_quality_score(t_e)))
    except Exception as exc:
        notes.append(f"EasyOCR: {exc!s}")
    if not candidates:
        return "", "none"
    # Prefer higher quality score; if within ~12%, take the longer transcript (often more complete)
    c_sorted = sorted(candidates, key=lambda x: x[2], reverse=True)
    top, second = c_sorted[0], c_sorted[1] if len(c_sorted) > 1 else None
    pick = top
    if second is not None and top[2] > 0 and (top[2] - second[2]) / top[2] < 0.12:
        if len(second[0].strip()) > len(top[0].strip()) * 1.08:
            pick = second
            notes.append("OCR: quality scores close — picked longer extraction.")
    notes.append(
        f"OCR_NEURAL_BACKEND=best: chose {pick[1]} (quality={pick[2]:.2f}; "
        + ", ".join(f"{c[1]}={c[2]:.2f}" for c in candidates)
        + ")."
    )
    return pick[0], pick[1]


def _pdf_render_dpi() -> int:
    return int(float(os.getenv("OCR_PDF_RENDER_DPI", "400")))


def _pdf_max_pages() -> int:
    return int(os.getenv("OCR_PDF_MAX_PAGES", "30"))


def _pdf_to_page_images(pdf_path: Path, notes: list[str]) -> list[Image.Image]:
    import fitz

    dpi = _pdf_render_dpi()
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pages_out: list[Image.Image] = []
    doc = fitz.open(str(pdf_path))
    try:
        n = min(len(doc), _pdf_max_pages())
        if len(doc) > n:
            notes.append(f"PDF: processing first {n} of {len(doc)} page(s) (OCR_PDF_MAX_PAGES).")
        for i in range(n):
            page = doc[i]
            pix = page.get_pixmap(matrix=mat, alpha=False)
            im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            pages_out.append(im)
    finally:
        doc.close()
    return pages_out


def _should_use_fitz_text_only(embedded: str) -> bool:
    if not _env_bool("OCR_PDF_PREFER_FITZ", True):
        return False
    min_words = int(os.getenv("OCR_PDF_MIN_FITZ_WORDS", "10"))
    if _word_count(embedded) < min_words:
        return False
    if _text_looks_suspiciously_noisy(embedded):
        return False
    return True


# --- Public router -------------------------------------------------------------------------


def _engine_mode() -> str:
    m = os.getenv("OCR_ENGINE", "neural").strip().lower()
    if m in ("tesseract", "ocrmypdf"):
        return "ocrmypdf"
    if m in ("neural", "auto"):
        return m
    return "neural"


def _extract_ocrmypdf_only(path: Path, notes: list[str], *, image_dpi: int | None) -> str:
    if path.suffix.lower() == ".pdf":
        return _run_ocrmypdf(path, notes, image_dpi=image_dpi)
    pages = _load_image_pages(path)
    tmp_pdf, embed_dpi = _images_to_temp_pdf(pages, notes)
    try:
        return _run_ocrmypdf(tmp_pdf, notes, image_dpi=embed_dpi)
    finally:
        tmp_pdf.unlink(missing_ok=True)


def extract_text(path: Path) -> OCRResult:
    notes: list[str] = []
    suffix = path.suffix.lower()
    mode = _engine_mode()

    if suffix == ".txt":
        return OCRResult(extracted_text=_read_text_file(path), engine_used="none", notes=["Used direct typed-text file."])

    if mode == "ocrmypdf":
        if suffix == ".pdf":
            notes.append("OCR pipeline: Tesseract via OCRmyPDF (OCR_ENGINE=ocrmypdf).")
            text = _run_ocrmypdf(path, notes, image_dpi=None)
        else:
            notes.append("OCR pipeline: raster → Tesseract via OCRmyPDF (OCR_ENGINE=ocrmypdf).")
            tmp_pdf: Path | None = None
            try:
                pages = _load_image_pages(path)
                tmp_pdf, embed_dpi = _images_to_temp_pdf(pages, notes)
                text = _run_ocrmypdf(tmp_pdf, notes, image_dpi=embed_dpi)
            finally:
                if tmp_pdf is not None:
                    tmp_pdf.unlink(missing_ok=True)
        normalized = _spell_and_grammar_normalize(text) if text else ""
        nlines, nwords = _segment_lines_words(normalized)
        notes.append(f"Detected ~{nlines} line(s), ~{nwords} word segments.")
        return OCRResult(extracted_text=normalized, engine_used="ocrmypdf", notes=notes)

    # Default: local neural (RapidOCR/EasyOCR, best model picked); box reading-order like layout OCR
    if suffix in RASTER_SUFFIXES:
        try:
            notes.append(
                "OCR pipeline: local neural (OCR_NEURAL_BACKEND=best|rapid|easyocr; "
                "text boxes ordered top-to-bottom, left-to-right)."
            )
            pages = _load_image_pages(path)
            text, label = _run_neural_ocr_on_pages(pages, notes)
            if not text.strip() and mode == "auto":
                notes.append("Neural OCR empty; falling back to OCRmyPDF.")
                text = _extract_ocrmypdf_only(path, notes, image_dpi=None)
                normalized = _spell_and_grammar_normalize(text) if text else ""
                nlines, nwords = _segment_lines_words(normalized)
                notes.append(f"Fallback: ~{nlines} line(s), ~{nwords} word segments.")
                return OCRResult(extracted_text=normalized, engine_used="ocrmypdf", notes=notes)
            nlines, nwords = _segment_lines_words(text)
            notes.append(f"Detected ~{nlines} line(s), ~{nwords} word segments.")
            return OCRResult(extracted_text=text, engine_used=label, notes=notes)
        except Exception as exc:
            if mode == "auto":
                notes.append(f"Neural OCR failed ({exc!s}); trying OCRmyPDF.")
                text = _extract_ocrmypdf_only(path, notes, image_dpi=None)
                normalized = _spell_and_grammar_normalize(text) if text else ""
                return OCRResult(extracted_text=normalized, engine_used="ocrmypdf", notes=notes)
            raise

    if suffix == ".pdf":
        try:
            embedded = _fitz_extract_from_pdf(path)
        except Exception as exc:
            notes.append(f"PyMuPDF text read failed: {exc}; will render and run neural OCR.")
            embedded = ""
        if _should_use_fitz_text_only(embedded):
            text = _transcript_normalize(embedded)
            notes.append("PDF: used native/embedded text layer (no visual OCR).")
            nlines, nwords = _segment_lines_words(text)
            notes.append(f"Detected ~{nlines} line(s), ~{nwords} word segments.")
            return OCRResult(extracted_text=text, engine_used="pymupdf", notes=notes)
        notes.append("PDF: rendering pages + local neural OCR (RapidOCR/EasyOCR; see OCR_NEURAL_BACKEND).")
        pages = _pdf_to_page_images(path, notes)
        text, label = _run_neural_ocr_on_pages(pages, notes)
        if not text.strip() and mode == "auto":
            notes.append("Neural OCR empty; falling back to Tesseract (OCRmyPDF).")
            text = _run_ocrmypdf(path, notes, image_dpi=None)
            normalized = _spell_and_grammar_normalize(text) if text else ""
            nlines, nwords = _segment_lines_words(normalized)
            return OCRResult(extracted_text=normalized, engine_used="ocrmypdf", notes=notes)
        nlines, nwords = _segment_lines_words(text)
        notes.append(f"Detected ~{nlines} line(s), ~{nwords} word segments.")
        return OCRResult(extracted_text=text, engine_used=label, notes=notes)

    return OCRResult(
        extracted_text="",
        engine_used="none",
        notes=[f"Unsupported or unhandled type: {suffix}"],
    )
