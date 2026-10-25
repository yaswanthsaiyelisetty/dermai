
import numpy as np
import pytest
from PIL import Image

from ai.image_preprocessing import preprocess_image


def test_valid_jpg(tmp_path):
    image_path = tmp_path / "skin.jpg"
    Image.new("RGB", (400, 300), color="red").save(image_path)

    result = preprocess_image(image_path)

    assert result.shape == (224, 224, 3)
    assert result.dtype == np.float32
    assert result.min() >= 0.0
    assert result.max() <= 1.0


def test_png_image(tmp_path):
    image_path = tmp_path / "skin.png"
    Image.new("RGB", (100, 150), color="blue").save(image_path)

    result = preprocess_image(image_path)

    assert result.shape == (224, 224, 3)


def test_grayscale_image(tmp_path):
    image_path = tmp_path / "gray.png"
    Image.new("L", (100, 100), color=128).save(image_path)

    result = preprocess_image(image_path)

    assert result.shape == (224, 224, 3)


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        preprocess_image(tmp_path / "missing.jpg")


def test_invalid_image_file(tmp_path):
    bad_file = tmp_path / "not_image.jpg"
    bad_file.write_text("This is not an image.")

    with pytest.raises(ValueError, match="not a supported image"):
        preprocess_image(bad_file)


def test_invalid_image_size(tmp_path):
    image_path = tmp_path / "skin.jpg"
    Image.new("RGB", (100, 100)).save(image_path)

    with pytest.raises(ValueError, match="image_size"):
        preprocess_image(image_path, image_size=(0, 224))


def test_custom_image_size(tmp_path):
    image_path = tmp_path / "skin.jpg"
    Image.new("RGB", (300, 300)).save(image_path)

    result = preprocess_image(image_path, image_size=(128, 128))

    assert result.shape == (128, 128, 3)
