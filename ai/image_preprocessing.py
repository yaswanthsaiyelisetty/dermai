
from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError


def preprocess_image(image_path, image_size=(224, 224)):
    """
    Prepare a skin image for a future deep-learning model.

    Returns:
        NumPy array with shape (height, width, 3),
        dtype float32, and values between 0 and 1.
    """
    image_path = Path(image_path)

    # Validate the path
    if not image_path.exists():
        raise FileNotFoundError(
            f"Image file does not exist: {image_path}"
        )

    if not image_path.is_file():
        raise ValueError(
            f"Expected a file, but received a directory: {image_path}"
        )

    # Validate image size
    if (
        not isinstance(image_size, (tuple, list))
        or len(image_size) != 2
        or any(
            not isinstance(value, int)
            or isinstance(value, bool)
            or value <= 0
            for value in image_size
        )
    ):
        raise ValueError(
            "image_size must contain two positive integers."
        )

    try:
        with Image.open(image_path) as image:
            image = image.convert("RGB")
            image = image.resize(
                tuple(image_size),
                Image.Resampling.LANCZOS
            )
            image_array = np.asarray(
                image, dtype=np.float32
            )

    except UnidentifiedImageError as exc:
        raise ValueError(
            f"File is not a supported image: {image_path}"
        ) from exc

    except OSError as exc:
        raise ValueError(
            f"Could not read image: {image_path}"
        ) from exc

    # Normalize pixel values to [0, 1]
    image_array /= 255.0

    return image_array
