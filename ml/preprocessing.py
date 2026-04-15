from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps


@dataclass
class PreprocessOutput:
    clean_image: Image.Image
    notes: list[str]


def _simple_skew_estimate(gray: Image.Image) -> float:
    # Lightweight skew proxy: if text mass is strongly diagonal, nudge correction.
    w, h = gray.size
    left_strip = gray.crop((0, 0, max(1, w // 5), h))
    right_strip = gray.crop((w - max(1, w // 5), 0, w, h))
    left_dark = sum(1 for px in left_strip.getdata() if px < 128)
    right_dark = sum(1 for px in right_strip.getdata() if px < 128)
    delta = right_dark - left_dark
    if abs(delta) < 100:
        return 0.0
    return -1.0 if delta > 0 else 1.0


def _deskew(gray: Image.Image, angle: float) -> Image.Image:
    if abs(angle) < 0.3:
        return gray
    return gray.rotate(angle, expand=False, fillcolor=255)


def preprocess_image(image_rgb: Image.Image) -> PreprocessOutput:
    notes: list[str] = []
    gray = ImageOps.grayscale(image_rgb)
    notes.append("Converted to grayscale.")

    denoised = gray.filter(ImageFilter.GaussianBlur(radius=1.0)).filter(ImageFilter.MedianFilter(size=3))
    notes.append("Applied Gaussian + Median denoising.")

    angle = _simple_skew_estimate(denoised)
    deskewed = _deskew(denoised, angle)
    if abs(angle) >= 0.3:
        notes.append(f"Skew corrected by {angle:.2f} degrees.")
    else:
        notes.append("No significant skew found.")

    # Otsu-like threshold approximation using mean intensity and local enhancement.
    mean_val = int(sum(deskewed.getdata()) / max(1, len(deskewed.getdata())))
    otsu_like = deskewed.point(lambda p: 255 if p > mean_val else 0)
    adaptive_like = ImageOps.autocontrast(deskewed).point(lambda p: 255 if p > 140 else 0)
    binary = ImageChops.logical_and(otsu_like.convert("1"), adaptive_like.convert("1")).convert("L")
    notes.append("Applied Otsu + adaptive binarization.")

    enhanced = ImageEnhance.Contrast(binary).enhance(1.8)
    notes.append("Enhanced contrast.")

    return PreprocessOutput(clean_image=enhanced, notes=notes)

