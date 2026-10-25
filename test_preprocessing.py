
from pathlib import Path

from ai.image_preprocessing import preprocess_image


# Update this path to match your actual extracted image.
image_path = Path("data/DATASET_0/DATASET_0/IMG_0011.jpg")

processed_image = preprocess_image(image_path)

print("Preprocessing successful!")
print("Image shape:", processed_image.shape)
print("Data type:", processed_image.dtype)
print("Minimum pixel value:", processed_image.min())
print("Maximum pixel value:", processed_image.max())
