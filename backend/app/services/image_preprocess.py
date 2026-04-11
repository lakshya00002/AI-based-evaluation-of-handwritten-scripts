"""
OpenCV preprocessing for handwritten OCR: noise removal, skew correction, binarization.

Line/word segmentation is approximated via morphological operations and contours
for optional downstream use; primary OCR uses Tesseract on the full preprocessed page.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

import cv2
import numpy as np


@dataclass
class PreprocessResult:
    """Binary image ready for OCR plus human-readable notes."""

    binary_bgr: np.ndarray
    notes: list[str] = field(default_factory=list)


def _estimate_skew_angle(gray: np.ndarray) -> float:
    """Estimate document skew using min-area rectangle on largest text contour region."""
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(thresh > 0))
    if coords.size < 100:
        return 0.0
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    elif angle > 45:
        angle = angle - 90
    return float(angle)


def _rotate_image(image: np.ndarray, angle: float) -> Tuple[np.ndarray, bool]:
    if abs(angle) < 0.3:
        return image, False
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    m = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image,
        m,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return rotated, True


def preprocess_for_ocr(bgr: np.ndarray) -> PreprocessResult:
    """
    Full pipeline: grayscale, denoise, optional deskew, adaptive binarization.

    Args:
        bgr: BGR image as uint8 numpy array (OpenCV default).
    """
    notes: list[str] = []
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)
    notes.append("Applied non-local means denoising.")

    angle = _estimate_skew_angle(denoised)
    rotated, did_rotate = _rotate_image(denoised, angle)
    if did_rotate:
        notes.append(f"Deskewed by approximately {angle:.2f} degrees.")

    # Adaptive threshold handles uneven lighting better than global Otsu on scans.
    binary = cv2.adaptiveThreshold(
        rotated,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        35,
        10,
    )
    notes.append("Applied adaptive Gaussian binarization.")

    # Tesseract expects light background, dark text for many configs; invert if needed.
    if float(np.mean(binary)) < 127:
        binary = cv2.bitwise_not(binary)
        notes.append("Inverted polarity for dark-background scan.")

    bgr_out = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    return PreprocessResult(binary_bgr=bgr_out, notes=notes)


def segment_lines_mask(binary_inv: np.ndarray) -> list[tuple[int, int, int, int]]:
    """
    Rough horizontal line bounding boxes via morphological closing.

    Expects inverted binary (text white). Returns list of (x, y, w, h).
    """
    h, w = binary_inv.shape[:2]
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(w // 20, 15), 1))
    dilated = cv2.dilate(binary_inv, horizontal_kernel, iterations=1)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes: list[tuple[int, int, int, int]] = []
    for c in contours:
        x, y, cw, ch = cv2.boundingRect(c)
        if ch > h * 0.01 and cw > w * 0.05:
            boxes.append((x, y, cw, ch))
    return sorted(boxes, key=lambda b: b[1])
