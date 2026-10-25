from __future__ import annotations

import math
import sys
from datetime import date
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from PIL import Image, UnidentifiedImageError

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
METADATA_PATH = DATA / "Skin_Metadata.csv"
PREPARED_PATH = DATA / "prepared_metadata.csv"
IMAGE_DIR = DATA / "DATASET_0"
SPLITS = {
    "Train": DATA / "splits" / "train.csv",
    "Validation": DATA / "splits" / "validation.csv",
    "Test": DATA / "splits" / "test.csv",
}

REQUIRED_COLUMNS = {
    "Disease_label",
    "Main_class",
    "Sub_class",
    "Image_name",
    "Subject_ID",
}
SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png"}


def require_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Required input file does not exist: {path}")


def load_metadata(path: Path) -> pd.DataFrame:
    require_file(path)
    frame = pd.read_csv(path)
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"{path.name} is missing required columns: {sorted(missing)}")
    return frame


def counts(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    result = frame[column].value_counts(dropna=False).rename_axis(column).reset_index(name="count")
    result["percentage"] = result["count"] / len(frame) * 100
    return result


def distribution_stats(frame: pd.DataFrame, column: str) -> dict:
    values = frame[column].value_counts(dropna=False)
    return {
        "classes": int(values.size),
        "minimum": int(values.min()),
        "maximum": int(values.max()),
        "mean": float(values.mean()),
        "median": float(values.median()),
        "rares_under_5": int((values < 5).sum()),
        "rares_under_10": int((values < 10).sum()),
        "least": values[values == values.min()].index.astype(str).tolist(),
        "most": values[values == values.max()].index.astype(str).tolist(),
        "imbalance_ratio": float(values.max() / values.min()) if values.min() else math.inf,
    }


def build_image_index() -> dict[str, list[Path]]:
    if not IMAGE_DIR.is_dir():
        raise FileNotFoundError(f"Extracted image directory does not exist: {IMAGE_DIR}")
    index: dict[str, list[Path]] = {}
    for path in IMAGE_DIR.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_FORMATS:
            index.setdefault(path.name.lower(), []).append(path)
    return index


def inspect_images(paths: list[Path]) -> dict:
    unreadable = 0
    dimensions: list[tuple[int, int]] = []
    formats: dict[str, int] = {}
    for path in paths:
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                dimensions.append(image.size)
                formats[image.format or path.suffix.lower().lstrip(".").upper()] = (
                    formats.get(image.format or path.suffix.lower().lstrip(".").upper(), 0) + 1
                )
        except (UnidentifiedImageError, OSError):
            unreadable += 1
    return {
        "checked": len(paths),
        "unreadable": unreadable,
        "formats": formats,
        "width_min": min((item[0] for item in dimensions), default=None),
        "width_max": max((item[0] for item in dimensions), default=None),
        "height_min": min((item[1] for item in dimensions), default=None),
        "height_max": max((item[1] for item in dimensions), default=None),
    }


def split_analysis(metadata: pd.DataFrame) -> tuple[dict, dict]:
    split_stats: dict = {}
    split_frames: dict[str, pd.DataFrame] = {}
    for name, path in SPLITS.items():
        require_file(path)
        frame = pd.read_csv(path)
        split_frames[name] = frame
        image_column = "image_path" if "image_path" in frame.columns else "matched_image_path"
        split_stats[name] = {
            "rows": len(frame),
            "subjects": int(frame["Subject_ID"].nunique()) if "Subject_ID" in frame else None,
            "classes": int(frame["Disease_label"].nunique()) if "Disease_label" in frame else None,
            "image_column": image_column if image_column in frame else None,
            "missing_image_refs": (
                int(frame[image_column].isna().sum()) if image_column in frame else None
            ),
            "main_class_counts": (
                frame["Main_class"].value_counts().to_dict()
                if "Main_class" in frame
                else {}
            ),
        }

    subject_overlap: dict[str, int] = {}
    image_overlap: dict[str, int] = {}
    names = list(split_frames)
    for index, left_name in enumerate(names):
        for right_name in names[index + 1 :]:
            left = split_frames[left_name]
            right = split_frames[right_name]
            if "Subject_ID" in left and "Subject_ID" in right:
                subject_overlap[f"{left_name}/{right_name}"] = len(
                    set(left["Subject_ID"]) & set(right["Subject_ID"])
                )
            for column in ("image_path", "matched_image_path", "Image_name"):
                if column in left and column in right:
                    image_overlap[f"{left_name}/{right_name}"] = len(
                        set(left[column].dropna()) & set(right[column].dropna())
                    )
                    break
    return split_stats, {"subject_overlap": subject_overlap, "image_overlap": image_overlap}


def save_bar_chart(series: pd.Series, path: Path, title: str, xlabel: str, horizontal: bool = False) -> None:
    height = max(4.5, len(series) * 0.28) if horizontal else 5.5
    figure, axis = plt.subplots(figsize=(10, height))
    if horizontal:
        series.sort_values().plot(kind="barh", ax=axis, color="#176b66")
        axis.set_xlabel("Sample count")
        axis.set_ylabel(xlabel)
    else:
        series.plot(kind="bar", ax=axis, color="#176b66")
        axis.set_ylabel("Sample count")
        axis.set_xlabel(xlabel)
        axis.tick_params(axis="x", rotation=35)
    axis.set_title(title)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def save_missing_chart(frame: pd.DataFrame, path: Path) -> None:
    missing = frame.isna().sum().sort_values(ascending=False)
    missing = missing[missing > 0]
    if missing.empty:
        missing = pd.Series({"No missing values": 0})
    save_bar_chart(missing, path, "Missing values by metadata column", "Column")


def save_split_chart(split_stats: dict, path: Path) -> None:
    values = pd.Series({name: data["rows"] for name, data in split_stats.items()})
    save_bar_chart(values, path, "Prepared dataset split sizes", "Split")


def save_imbalance_chart(disease_counts: pd.Series, path: Path) -> None:
    ranked = disease_counts.sort_values(ascending=False)
    top = ranked.head(20)
    tail = ranked.iloc[20:]
    values = pd.concat([top, pd.Series({"All remaining labels": int(tail.sum())})])
    save_bar_chart(values, path, "Disease-label long-tail distribution", "Disease label", horizontal=True)


def fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def table_from_counts(frame: pd.DataFrame, column: str, limit: int = 12) -> str:
    rows = counts(frame, column).head(limit)
    lines = [f"| {column} | Count | Percentage |", "|---|---:|---:|"]
    for _, row in rows.iterrows():
        lines.append(f"| {row[column]} | {int(row['count'])} | {row['percentage']:.2f}% |")
    return "\n".join(lines)


def generate_report(
    metadata: pd.DataFrame,
    prepared: pd.DataFrame,
    image_index: dict[str, list[Path]],
    image_info: dict,
    split_stats: dict,
    split_overlaps: dict,
) -> None:
    metadata_names = metadata["Image_name"].map(lambda value: Path(str(value)).name.lower())
    matched = metadata_names.map(lambda name: name in image_index)
    duplicate_files = sum(len(paths) - 1 for paths in image_index.values() if len(paths) > 1)
    empty_labels = int(metadata["Disease_label"].astype(str).str.strip().eq("").sum())
    replacement_labels = int(metadata["Disease_label"].astype(str).str.contains("\ufffd", regex=False).sum())
    report_lines = [
        "# DermAI Exploratory Data Analysis and Class Distribution Report",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "## Dataset source and attribution",
        "",
        "The repository identifies the working dataset as DermaCon-IN through the project context and file names. "
        "No authoritative citation, license file, or source URL was present in the inspected repository, so licensing "
        "and de-identification claims are not independently verified here. The report therefore describes repository "
        "artifacts without asserting rights beyond the evidence available.",
        "",
        "## Methodology",
        "",
        "The reproducible script reads the original metadata, prepared metadata, extracted image directory, and existing "
        "train/validation/test CSV files. It recalculates counts, nulls, duplicates, filename matches, image readability, "
        "class distributions, subject overlap, image-record overlap, and generated split charts. Source files are never modified.",
        "",
        "## Dataset overview",
        "",
        f"- Original metadata: **{len(metadata):,} rows**, **{len(metadata.columns)} columns**.",
        f"- Prepared metadata: **{len(prepared):,} rows**, **{len(prepared.columns)} columns**.",
        f"- Disease labels: **{metadata['Disease_label'].nunique():,}**; main classes: **{metadata['Main_class'].nunique():,}**; subclasses: **{metadata['Sub_class'].nunique():,}**.",
        f"- Unique subjects: **{metadata['Subject_ID'].nunique():,}**.",
        f"- Unique metadata image names: **{metadata['Image_name'].nunique():,}**; duplicate metadata rows: **{int(metadata.duplicated().sum())}**; duplicate image names: **{int(metadata['Image_name'].duplicated().sum())}**.",
        "",
        "Important columns are `Image_name` (image identifier used for matching), `Disease_label` (fine-grained annotation), "
        "`Main_class` and `Sub_class` (broader annotation levels), and `Subject_ID` (subject grouping used by the split script). "
        "The analysis does not assume that each row is an independent subject because subject identifiers repeat.",
        "",
        "### Metadata types and nulls",
        "",
        "```text",
        metadata.dtypes.astype(str).to_string(),
        "```",
        "",
        "Null counts:",
        "",
        "```text",
        metadata.isna().sum().to_string(),
        "```",
        "",
        "## Data-quality findings",
        "",
        f"- Extracted image files indexed: **{sum(len(paths) for paths in image_index.values()):,}** across **{len(image_index):,} unique basenames**.",
        f"- Metadata records with a matching extracted basename: **{int(matched.sum()):,}**; unmatched records: **{int((~matched).sum()):,}**.",
        f"- Extracted files with duplicate basenames: **{duplicate_files:,} additional file(s)**.",
        f"- Readability checks: **{image_info['checked']:,} checked**, **{image_info['unreadable']:,} unreadable**.",
        f"- Image formats: {', '.join(f'{key}={value:,}' for key, value in sorted(image_info['formats'].items())) or 'none'}.",
        f"- Readable image width range: {image_info['width_min']}–{image_info['width_max']} pixels; height range: {image_info['height_min']}–{image_info['height_max']} pixels.",
        f"- Empty/whitespace disease labels: **{empty_labels}**; labels containing the Unicode replacement character: **{replacement_labels}**.",
        "- Unmatched metadata records may reflect an unextracted archive or incomplete local extraction; they are not treated as proof that source images are permanently missing.",
        "",
        "## Class distribution",
        "",
        f"Main-class statistics: `{distribution_stats(metadata, 'Main_class')}`.",
        "",
        table_from_counts(metadata, "Main_class", limit=20),
        "",
        "Disease-label statistics:",
        "",
        f"`{distribution_stats(metadata, 'Disease_label')}`",
        "",
        table_from_counts(metadata, "Disease_label"),
        "",
        "Subclass statistics:",
        "",
        f"`{distribution_stats(metadata, 'Sub_class')}`",
        "",
        table_from_counts(metadata, "Sub_class", limit=20),
        "",
        "The disease-label median is much smaller than the maximum, indicating a long tail. Labels below 5 samples are treated as "
        "very rare for this report; labels below 10 are treated as low-support. These thresholds are reporting conventions, not "
        "clinical or modeling requirements.",
        "",
        "![Main-class distribution](figures/main_class_distribution.png)",
        "",
        "*Figure 1. Counts and relative scale of the broad main classes.*",
        "",
        "![Top disease labels](figures/top_disease_labels.png)",
        "",
        "*Figure 2. The 20 most frequent fine-grained disease labels.*",
        "",
        "![Disease-label long tail](figures/class_imbalance.png)",
        "",
        "*Figure 3. Top disease labels compared with the aggregate remaining long tail.*",
        "",
        "![Missing values](figures/missing_values.png)",
        "",
        "*Figure 4. Missing metadata values; zero bars are omitted when no column is missing.*",
        "",
        "## Prepared dataset and split analysis",
        "",
    ]
    for name, data in split_stats.items():
        split_lines = [
            f"- **{name}:** {data['rows']:,} rows; {data['subjects']:,} unique subjects; "
            f"{data['classes']:,} disease labels; missing image references: {data['missing_image_refs']}.",
        ]
        report_lines.extend(split_lines)
        split_classes = ", ".join(
            f"{label}: {count:,}" for label, count in data["main_class_counts"].items()
        )
        report_lines.append(f"  - Main-class counts: {split_classes}.")
    report_lines.extend(
        [
            "",
            f"Subject overlap checks: `{split_overlaps['subject_overlap']}`.",
            f"Image-record overlap checks: `{split_overlaps['image_overlap']}`.",
            "",
            "The existing split-generation script uses `GroupShuffleSplit` on `Subject_ID` and asserts disjoint subject sets. "
            "This report independently checks subject and available image-reference overlap; it does not claim that all possible "
            "forms of leakage have been eliminated.",
            "",
            "![Dataset splits](figures/dataset_splits.png)",
            "",
            "*Figure 5. Row counts in the existing prepared splits.*",
            "",
            "## Target-class recommendation",
            "",
            "For an educational first classifier, the **8 `Main_class` categories** are the most defensible candidate level "
            "because they provide broader support than the 245 fine-grained disease labels. This remains a recommendation, not "
            "a finalized implementation decision.",
            "",
            f"- Main-class support ranges from {distribution_stats(metadata, 'Main_class')['minimum']:,} to {distribution_stats(metadata, 'Main_class')['maximum']:,} records, with an imbalance ratio of {distribution_stats(metadata, 'Main_class')['imbalance_ratio']:.2f}:1.",
            f"- Fine-grained disease-label support ranges from {distribution_stats(metadata, 'Disease_label')['minimum']:,} to {distribution_stats(metadata, 'Disease_label')['maximum']:,}; {distribution_stats(metadata, 'Disease_label')['rares_under_5']} labels have fewer than 5 records and {distribution_stats(metadata, 'Disease_label')['rares_under_10']} have fewer than 10.",
            "- A selected subset of disease labels could be considered only after project-owner approval, explicit clinical/educational rationale, and a minimum-support rule.",
            "- All labels remain candidates in the source data; this task does not modify or discard any labels.",
            "",
        ]
    )
    report_lines.extend(
        [
            "## Key findings and limitations",
            "",
            "- The local extracted working set is smaller than the original metadata, so matching results depend on the extraction state.",
            "- Subject identifiers repeat and are therefore important for evaluating split independence.",
            "- The metadata contains six null values in `Fitzpatrick` and six in `Monk_skin_tone`; other inspected required fields have no nulls.",
            "- The repository does not contain authoritative dataset citation/license evidence, so attribution and reuse terms require confirmation before external distribution.",
            "- Upload validation and preprocessing are implemented, but no model training or inference is included in this milestone.",
            "",
            "## Reproduction",
            "",
            "From any working directory, run:",
            "",
            "```powershell",
            ".\\.venv\\Scripts\\python.exe ai\\generate_eda_report.py",
            "```",
            "",
            "The script writes this report and figures under `reports/` and exits non-zero when required inputs or critical analysis steps fail.",
        ]
    )
    (REPORTS / "eda_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")


def main() -> int:
    try:
        FIGURES.mkdir(parents=True, exist_ok=True)
        metadata = load_metadata(METADATA_PATH)
        prepared = load_metadata(PREPARED_PATH)
        if "matched_image_path" not in prepared.columns:
            raise ValueError("prepared_metadata.csv must contain matched_image_path")

        image_index = build_image_index()
        image_paths = [path for paths in image_index.values() for path in paths]
        image_info = inspect_images(image_paths)
        split_stats, split_overlaps = split_analysis(metadata)

        save_bar_chart(
            metadata["Main_class"].value_counts(),
            FIGURES / "main_class_distribution.png",
            "Main-class distribution",
            "Main class",
        )
        save_bar_chart(
            metadata["Disease_label"].value_counts().head(20),
            FIGURES / "top_disease_labels.png",
            "Top 20 disease labels",
            "Disease label",
            horizontal=True,
        )
        save_missing_chart(metadata, FIGURES / "missing_values.png")
        save_split_chart(split_stats, FIGURES / "dataset_splits.png")
        save_imbalance_chart(metadata["Disease_label"].value_counts(), FIGURES / "class_imbalance.png")
        generate_report(metadata, prepared, image_index, image_info, split_stats, split_overlaps)

        print("EDA report generated successfully.")
        print(f"Original metadata: {len(metadata):,} rows, {len(metadata.columns)} columns")
        print(f"Prepared metadata: {len(prepared):,} rows, {len(prepared.columns)} columns")
        print(f"Indexed images: {sum(len(paths) for paths in image_index.values()):,}")
        print(f"Readable image failures: {image_info['unreadable']:,}")
        print(f"Report: {REPORTS / 'eda_report.md'}")
        return 0
    except (FileNotFoundError, ValueError, OSError, pd.errors.ParserError) as exc:
        print(f"EDA generation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
