
from pathlib import Path

import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
METADATA_FILE = DATA / "Skin_Metadata.csv"
IMAGE_DIR = DATA / "DATASET_0" / "DATASET_0"
SPLIT_DIR = DATA / "splits"


def main():
    metadata = pd.read_csv(METADATA_FILE)

    # Index available image files by filename.
    image_lookup = {}
    for path in IMAGE_DIR.rglob("*"):
        if path.is_file() and path.suffix.lower() in {
            ".jpg", ".jpeg", ".png"
        }:
            image_lookup.setdefault(path.name.lower(), path.resolve())

    # Match metadata records to images.
    metadata["image_path"] = metadata["Image_name"].apply(
        lambda name: (
            str(image_lookup[Path(str(name)).name.lower()])
            if pd.notna(name)
            and Path(str(name)).name.lower() in image_lookup
            else None
        )
    )

    matched = metadata.dropna(
        subset=["image_path", "Disease_label", "Subject_ID"]
    ).copy()

    matched = matched[
        matched["Disease_label"].astype(str).str.strip().ne("")
        & matched["Subject_ID"].astype(str).str.strip().ne("")
    ]

    matched = matched.drop_duplicates(subset=["image_path"])
    matched = matched.reset_index(drop=True)

    if len(matched) < 10:
        raise ValueError("Not enough matched images to create splits.")

    # First reserve 20% of subjects for testing.
    first_split = GroupShuffleSplit(
        n_splits=1, test_size=0.20, random_state=42
    )
    train_val_idx, test_idx = next(
        first_split.split(
            matched,
            groups=matched["Subject_ID"]
        )
    )

    train_val = matched.iloc[train_val_idx].copy()
    test = matched.iloc[test_idx].copy()

    # Reserve 18.75% of the remaining subjects for validation.
    second_split = GroupShuffleSplit(
        n_splits=1, test_size=0.1875, random_state=42
    )
    train_idx, val_idx = next(
        second_split.split(
            train_val,
            groups=train_val["Subject_ID"]
        )
    )

    train = train_val.iloc[train_idx].copy()
    validation = train_val.iloc[val_idx].copy()

    # Verify that no subject appears in multiple splits.
    train_subjects = set(train["Subject_ID"])
    val_subjects = set(validation["Subject_ID"])
    test_subjects = set(test["Subject_ID"])

    assert train_subjects.isdisjoint(val_subjects)
    assert train_subjects.isdisjoint(test_subjects)
    assert val_subjects.isdisjoint(test_subjects)

    SPLIT_DIR.mkdir(parents=True, exist_ok=True)

    train.to_csv(SPLIT_DIR / "train.csv", index=False)
    validation.to_csv(SPLIT_DIR / "validation.csv", index=False)
    test.to_csv(SPLIT_DIR / "test.csv", index=False)

    print("Dataset split completed successfully!")
    print(f"Matched images: {len(matched)}")

    for name, frame in [
        ("Train", train),
        ("Validation", validation),
        ("Test", test),
    ]:
        print(
            f"{name}: {len(frame)} images, "
            f"{frame['Subject_ID'].nunique()} subjects, "
            f"{frame['Disease_label'].nunique()} classes"
        )

    print("\nFiles saved in:", SPLIT_DIR)
    print("Subject leakage check: PASSED")


if __name__ == "__main__":
    main()
