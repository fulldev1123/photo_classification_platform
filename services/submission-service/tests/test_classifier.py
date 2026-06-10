import io

import pytest
from app.services.classifier import classify_photo
from PIL import Image


def _png_bytes(color, size=(96, 96)):
    image = Image.new("RGB", size, color=color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_classify_warm_red():
    result = classify_photo(_png_bytes((200, 10, 10)))
    assert result.label == "warm"
    assert 0 <= result.score <= 100
    assert result.meta["model"] == "color-palette-v1"
    assert result.meta["dominant_channel"] == "red"
    assert result.meta["width"] == 96 and result.meta["height"] == 96


def test_classify_cool_blue():
    result = classify_photo(_png_bytes((10, 10, 200)))
    assert result.label == "cool"
    assert result.meta["dominant_channel"] == "blue"


def test_classify_natural_green():
    result = classify_photo(_png_bytes((10, 150, 10)))
    assert result.label == "natural"
    assert result.meta["dominant_channel"] == "green"


def test_classify_grayscale():
    result = classify_photo(_png_bytes((128, 128, 128)))
    assert result.label == "grayscale"
    assert result.score >= 90  # near-neutral gray -> high confidence


def test_classify_rejects_garbage():
    with pytest.raises(ValueError):
        classify_photo(b"not-an-image")
