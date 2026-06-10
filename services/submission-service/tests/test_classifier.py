import io

import pytest
from app.services.classifier import classify_photo
from PIL import Image


def _png_bytes(color, size=(96, 96)):
    image = Image.new("RGB", size, color=color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_classify_dark():
    result = classify_photo(_png_bytes((10, 10, 10)))
    assert result.label in {"very_dark", "dark"}
    assert 0 <= result.score <= 100
    assert result.meta["model"] == "luminance-heuristic-v1"
    assert result.meta["width"] == 96 and result.meta["height"] == 96


def test_classify_bright():
    result = classify_photo(_png_bytes((250, 250, 250)))
    assert result.label in {"very_bright", "bright"}


def test_classify_balanced():
    result = classify_photo(_png_bytes((128, 128, 128)))
    assert result.label == "balanced"


def test_classify_rejects_garbage():
    with pytest.raises(ValueError):
        classify_photo(b"not-an-image")
