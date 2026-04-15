from __future__ import annotations

import os
import re
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from ml.preprocessing import preprocess_image

_trocr_lock = threading.Lock()
_trocr_processor = None
_trocr_model = None


@dataclass
class OCRResult:
    extracted_text: str
    engine_used: str
    notes: list[str]


def _load_image(path: Path) -> Image.Image:
    with Image.open(path) as img:
        return img.convert("RGB")


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _spell_and_grammar_normalize(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s([?.!,;:])", r"\1", text)
    return text


def _is_meaningful_text(text: str) -> bool:
    return _text_quality_score(text) >= 2.0


def _text_quality_score(text: str) -> float:
    cleaned = _spell_and_grammar_normalize(text)
    if not cleaned:
        return 0.0
    tokens = re.findall(r"[A-Za-z0-9']+", cleaned)
    if not tokens:
        return 0.0

    alpha_count = sum(1 for ch in cleaned if ch.isalpha())
    digit_count = sum(1 for ch in cleaned if ch.isdigit())
    unique_ratio = len(set(t.lower() for t in tokens)) / max(1, len(tokens))
    longest_alpha = max((len(t) for t in tokens if any(c.isalpha() for c in t)), default=0)

    score = 0.0
    score += min(4.0, len(tokens) * 0.35)
    score += min(3.0, alpha_count * 0.05)
    score += unique_ratio
    score += 0.5 if longest_alpha >= 4 else 0.0
    if alpha_count == 0:
        score -= 3.0
    if digit_count > alpha_count:
        score -= 1.5
    if len(set(tokens)) == 1 and len(tokens) > 1:
        score -= 1.0
    return score


def _segment_lines_words(text: str) -> tuple[int, int]:
    lines = [line for line in text.splitlines() if line.strip()]
    words = [w for w in re.findall(r"[A-Za-z0-9']+", text) if w.strip()]
    return len(lines) if lines else (1 if text.strip() else 0), len(words)


def _ocr_easyocr(image: Image.Image) -> str:
    import easyocr

    # Keep EasyOCR offline-only to avoid SSL/download failures at runtime.
    # If weights are not available locally, this engine will be skipped by fallback.
    reader = easyocr.Reader(["en"], gpu=False, download_enabled=False)
    result = reader.readtext(image, detail=0, paragraph=True)
    return " ".join(result).strip()


def _ocr_trocr(image: Image.Image) -> str:
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel

    global _trocr_processor, _trocr_model
    if _trocr_processor is None or _trocr_model is None:
        with _trocr_lock:
            if _trocr_processor is None or _trocr_model is None:
                _trocr_processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
                _trocr_model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")

    processor = _trocr_processor
    model = _trocr_model
    # TrOCR performs better on line crops than on full pages.
    line_texts: list[str] = []
    for line_image in _segment_line_images(image):
        pixel_values = processor(images=line_image, return_tensors="pt").pixel_values
        generated_ids = model.generate(pixel_values, max_new_tokens=64)
        decoded = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
        if decoded:
            line_texts.append(decoded)

    joined = " ".join(line_texts).strip()
    if _is_meaningful_text(joined):
        return joined

    # Fallback to single-shot OCR on full image.
    pixel_values = processor(images=image, return_tensors="pt").pixel_values
    generated_ids = model.generate(pixel_values, max_new_tokens=128)
    return processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()


def _ocr_tesseract(image: Image.Image) -> str:
    import pytesseract

    configs = [
        "--oem 3 --psm 6",
        "--oem 3 --psm 4",
        "--oem 3 --psm 3",
    ]
    best_text = ""
    best_score = 0.0
    for cfg in configs:
        text = pytesseract.image_to_string(image, lang="eng", config=cfg).strip()
        score = _text_quality_score(text)
        if score > best_score:
            best_score = score
            best_text = text
    return best_text


def _segment_line_images(image: Image.Image) -> list[Image.Image]:
    gray = image.convert("L")
    w, h = gray.size
    px = gray.load()

    row_ink: list[int] = []
    for y in range(h):
        ink = 0
        for x in range(w):
            if px[x, y] < 160:
                ink += 1
        row_ink.append(ink)

    threshold = max(8, int(w * 0.01))
    spans: list[tuple[int, int]] = []
    start: int | None = None
    for y, ink in enumerate(row_ink):
        if ink >= threshold and start is None:
            start = y
        elif ink < threshold and start is not None:
            if y - start >= 10:
                spans.append((start, y))
            start = None
    if start is not None and h - start >= 10:
        spans.append((start, h))

    if not spans:
        return [image]

    line_images: list[Image.Image] = []
    for top, bottom in spans[:20]:
        pad = 6
        crop = image.crop((0, max(0, top - pad), w, min(h, bottom + pad)))
        line_images.append(crop)
    return line_images


def _image_variants(image: Image.Image) -> list[tuple[str, Image.Image]]:
    variants: list[tuple[str, Image.Image]] = [("raw", image)]
    pre = preprocess_image(image)
    variants.append(("preprocessed", pre.clean_image))
    variants.append(("autocontrast", Image.eval(image.convert("L"), lambda p: max(0, min(255, (p - 20) * 2)))))
    return variants


def extract_text(path: Path) -> OCRResult:
    notes: list[str] = []
    if path.suffix.lower() == ".txt":
        return OCRResult(extracted_text=_read_text_file(path), engine_used="none", notes=["Used direct typed-text file."])

    if path.suffix.lower() == ".pdf":
        from pdf2image import convert_from_path

        pages = convert_from_path(str(path), dpi=300)
        page_texts: list[str] = []
        page_engines: list[str] = []
        for idx, page in enumerate(pages, start=1):
            processed = preprocess_image(page.convert("RGB"))
            notes.extend(processed.notes)
            page_text, page_engine = _run_ocr_with_fallback(page.convert("RGB"), notes)
            line_count, word_count = _segment_lines_words(page_text)
            notes.append(f"PDF page {idx}: {line_count} lines, {word_count} words detected (engine: {page_engine}).")
            page_texts.append(page_text)
            page_engines.append(page_engine)
        cleaned = _spell_and_grammar_normalize("\n".join(page_texts))
        engine_used = "mixed" if len(set(page_engines)) > 1 else (page_engines[0] if page_engines else "none")
        return OCRResult(extracted_text=cleaned, engine_used=engine_used, notes=notes)

    image_rgb = _load_image(path)
    processed = preprocess_image(image_rgb)
    notes.extend(processed.notes)
    text, engine_used = _run_ocr_with_fallback(image_rgb, notes)
    line_count, word_count = _segment_lines_words(text)
    notes.append(f"Detected {line_count} text regions and ~{word_count} word segments.")
    normalized = _spell_and_grammar_normalize(text)
    if not normalized:
        notes.append("OCR completed but produced empty normalized text.")
    return OCRResult(extracted_text=normalized, engine_used=engine_used, notes=notes)


def _run_ocr_with_fallback(image: Image.Image, notes: list[str]) -> tuple[str, str]:
    # Prefer local/offline engines first; keep EasyOCR as optional final fallback.
    engines: list[tuple[str, object]] = []
    use_tesseract = os.getenv("USE_TESSERACT", "auto").strip().lower()
    tesseract_in_path = shutil.which("tesseract") is not None
    tesseract_enabled = use_tesseract not in {"0", "false", "off", "no"}
    if tesseract_enabled and tesseract_in_path:
        # Run local Tesseract first to avoid cloud/model download dependence.
        engines.append(("tesseract", _ocr_tesseract))
    elif not tesseract_in_path:
        notes.append("OCR engine skipped (tesseract): binary not found in PATH.")
    else:
        notes.append("OCR engine skipped (tesseract): disabled by USE_TESSERACT.")

    engines.extend([("trocr", _ocr_trocr), ("easyocr", _ocr_easyocr)])

    variants = _image_variants(image)
    for name, func in engines:
        best_engine_text = ""
        best_engine_score = 0.0
        try:
            for variant_name, variant in variants:
                text = func(variant)  # type: ignore[misc]
                score = _text_quality_score(text)
                if score > best_engine_score:
                    best_engine_score = score
                    best_engine_text = text
                if _is_meaningful_text(text):
                    preview = _spell_and_grammar_normalize(text)[:120]
                    notes.append(
                        f"OCR engine succeeded: {name} ({variant_name}). "
                        f"Quality={score:.2f}. Preview: {preview}"
                    )
                    return text, name
            notes.append(
                f"OCR engine returned low-quality text: {name}. "
                f"Best quality={best_engine_score:.2f}."
            )
        except Exception as exc:
            notes.append(f"OCR engine failed ({name}): {exc}")
        if best_engine_text and best_engine_score >= 1.2:
            notes.append(
                f"OCR engine accepted as fallback: {name}. "
                f"Quality={best_engine_score:.2f}."
            )
            return best_engine_text, name
    return "", "none"

