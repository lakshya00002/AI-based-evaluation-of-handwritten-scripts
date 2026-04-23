from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image


SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
SUPPORTED_FORMATS = SUPPORTED_IMAGE_EXTS | {".pdf", ".txt"}


@dataclass
class SubmissionMetadata:
    student_id: str
    exam_id: str
    question_id: str
    answer_script_path: str
    typed_text: str | None = None


@dataclass
class AcquisitionResult:
    metadata: SubmissionMetadata
    input_mode: str  # typed | handwritten
    validated_path: Path | None
    dpi_ok: bool
    notes: list[str]


def _validate_image_dpi(path: Path, min_dpi: int) -> tuple[bool, str]:
    with Image.open(path) as img:
        dpi = img.info.get("dpi")
        if not dpi:
            return False, "No DPI metadata found."
        x_dpi = int(dpi[0])
        return x_dpi >= min_dpi, f"Detected DPI: {x_dpi}"


def acquire_input(metadata: SubmissionMetadata, min_dpi: int) -> AcquisitionResult:
    notes: list[str] = []
    path = Path(metadata.answer_script_path).expanduser().resolve()
    ext = path.suffix.lower() if path.exists() else ""

    # Uploaded answer scripts (image/PDF) must drive OCR even if the student also typed in the text box.
    # Otherwise only the first lines in the form field were scored and the file was ignored.
    handwritten_upload = path.exists() and ext in SUPPORTED_IMAGE_EXTS | {".pdf"}

    if handwritten_upload:
        if ext not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {ext}. Allowed: {sorted(SUPPORTED_FORMATS)}")
        dpi_ok = True
        if ext in SUPPORTED_IMAGE_EXTS:
            dpi_ok, dpi_note = _validate_image_dpi(path, min_dpi=min_dpi)
            notes.append(dpi_note)
        else:
            notes.append("PDF accepted; rasterization will use high DPI for OCR.")
        if metadata.typed_text and metadata.typed_text.strip():
            notes.append(
                "Typed text present; OCR will run on the uploaded file and typed text will be appended after the transcript."
            )
        return AcquisitionResult(
            metadata=metadata,
            input_mode="handwritten",
            validated_path=path,
            dpi_ok=dpi_ok,
            notes=notes,
        )

    if metadata.typed_text and metadata.typed_text.strip():
        notes.append("Typed input received.")
        return AcquisitionResult(
            metadata=metadata,
            input_mode="typed",
            validated_path=None,
            dpi_ok=True,
            notes=notes,
        )

    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    if ext not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format: {ext}. Allowed: {sorted(SUPPORTED_FORMATS)}")

    dpi_ok = True
    if ext in SUPPORTED_IMAGE_EXTS:
        dpi_ok, dpi_note = _validate_image_dpi(path, min_dpi=min_dpi)
        notes.append(dpi_note)
    elif ext == ".pdf":
        notes.append("PDF accepted; rasterization will use high DPI for OCR.")
    elif ext == ".txt":
        notes.append("Text file accepted as typed input fallback.")

    return AcquisitionResult(
        metadata=metadata,
        input_mode="handwritten" if ext in SUPPORTED_IMAGE_EXTS | {".pdf"} else "typed",
        validated_path=path,
        dpi_ok=dpi_ok,
        notes=notes,
    )

