"""Photo classifier.

A deterministic, dependency-free *colour-palette* heuristic: it inspects the
image's average colour and labels its dominant tone. Kept small and fast,
behind a single seam -- ``classify_photo`` -- so it can later be swapped for a
real model (ONNX, Triton, a remote inference API) without touching callers.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError


@dataclass
class PhotoClassification:
    label: str
    score: int  # 0..100 confidence
    meta: dict


# Dominant-tone labels produced by the palette heuristic.
PALETTE_LABELS = ["grayscale", "warm", "cool", "natural"]

# Below this saturation the image is treated as neutral/gray rather than a hue.
_GRAYSCALE_SATURATION = 0.15


def classify_photo(image_bytes: bytes) -> PhotoClassification:
    """Classify a photo by its dominant colour tone.

    Rules, applied to the image's average RGB:

    * low saturation                  -> ``grayscale``
    * red is the strongest channel    -> ``warm``
    * blue is the strongest channel   -> ``cool``
    * green is the strongest channel  -> ``natural``

    The score is a 0..100 confidence: for colour images it tracks how saturated
    the average colour is; for gray images, how neutral it is.
    """
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
    for red, green, blue in pixels:
        red_total += red
        green_total += green
        blue_total += blue

    avg_red = red_total / pixel_count
    avg_green = green_total / pixel_count
    avg_blue = blue_total / pixel_count

    brightest = max(avg_red, avg_green, avg_blue)
    darkest = min(avg_red, avg_green, avg_blue)
    saturation = 0.0 if brightest == 0 else (brightest - darkest) / brightest

    if saturation < _GRAYSCALE_SATURATION:
        label = "grayscale"
        dominant_channel = "none"
        # Most confident when the channels are nearly equal (very low saturation).
        score = int((1 - saturation / _GRAYSCALE_SATURATION) * 100)
    else:
        if avg_red >= avg_green and avg_red >= avg_blue:
            label, dominant_channel = "warm", "red"
        elif avg_blue >= avg_red and avg_blue >= avg_green:
            label, dominant_channel = "cool", "blue"
        else:
            label, dominant_channel = "natural", "green"
        # Confidence grows with how saturated the dominant colour is.
        score = int(min(1.0, saturation) * 100)

    score = max(0, min(100, score))

    return PhotoClassification(
        label=label,
        score=score,
        meta={
            "width": width,
            "height": height,
            "avg_rgb": [round(avg_red, 2), round(avg_green, 2), round(avg_blue, 2)],
            "saturation": round(saturation, 3),
            "dominant_channel": dominant_channel,
            "model": "color-palette-v1",
        },
    )
