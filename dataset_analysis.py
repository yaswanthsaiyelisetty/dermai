
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


# Find the metadata file inside the data folder
project_folder = Path(__file__).parent
csv_path = project_folder / "data" / "Skin_Metadata.csv"

# Load the dataset
df = pd.read_csv(csv_path)

print("\n--- DermAI Dataset Analysis ---")
print("Total images:", len(df))
print("Total columns:", len(df.columns))

print("\nColumn names:")
print(df.columns.tolist())

# Count disease categories
print("\nImages by main disease category:")
print(df["Main_class"].value_counts(dropna=False))

print("\nTop 10 disease labels:")
print(df["Disease_label"].value_counts().head(10))

# Check missing values
print("\nMissing values in each column:")
print(df.isnull().sum())

# Plot the main disease categories
df["Main_class"].value_counts().plot(
    kind="bar",
    figsize=(10, 5),
    title="Images by Main Disease Category"
)

plt.xlabel("Disease category")
plt.ylabel("Number of images")
plt.xticks(rotation=35, ha="right")
plt.tight_layout()
plt.show()
