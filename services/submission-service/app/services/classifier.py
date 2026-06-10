"""Photo classifier.

A deterministic, dependency-free luminance heuristic. It keeps the service
small and fast while exposing a single clean seam -- ``classify_photo`` -- that
can later be replaced by a real model (ONNX, Triton, a remote inference API)
without touching any callers.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError


@dataclass
class PhotoClassification:
    label: str
    score: int  # 0..100
    meta: dict


# Average-luminance bands, darkest -> brightest.
LUMINANCE_BANDS = ["very_dark", "dark", "balanced", "bright", "very_bright"]
_BAND_WIDTH = 51  # ~256 / 5 buckets


def classify_photo(image_bytes: bytes) -> PhotoClassification:
    """Classify a photo by average luminance and return a labelled result."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            rgb_image = image.convert("RGB")
            width, height = rgb_image.size
            rgb_image.thumbnail((128, 128))  # downscale; the result is qualitative
            pixels = list(rgb_image.getdata())
    except UnidentifiedImageError as exc:
        raise ValueError("invalid image data") from exc

    if not pixels:
        raise ValueError("empty image")

    pixel_count = len(pixels)
    red_total = green_total = blue_total = 0
    luminance_total = 0
    for red, green, blue in pixels:
        red_total += red
        green_total += green
        blue_total += blue
        luminance_total += int(0.299 * red + 0.587 * green + 0.114 * blue)

    average_luminance = luminance_total / pixel_count
    band_index = min(int(average_luminance / _BAND_WIDTH), 4)

    # Confidence: distance from the nearest band edge, normalized to 0..100.
    offset_in_band = average_luminance % _BAND_WIDTH
    edge_distance = min(offset_in_band, _BAND_WIDTH - offset_in_band)
    score = max(0, min(100, int(50 + (edge_distance / _BAND_WIDTH) * 100)))

    return PhotoClassification(
        label=LUMINANCE_BANDS[band_index],
        score=score,
        meta={
            "width": width,
            "height": height,
            "avg_rgb": [
                round(red_total / pixel_count, 2),
                round(green_total / pixel_count, 2),
                round(blue_total / pixel_count, 2),
            ],
            "avg_luminance": round(average_luminance, 2),
            "model": "luminance-heuristic-v1",
        },
    )
