#!/usr/bin/env python3
"""
rescore_dedup.py — score your EXISTING trained weights on the deduplicated
grouped split produced by dedupe_check.py.

This does NOT train anything. It loads quality_model.pt and evaluates it.
Takes a few minutes, not 37 hours.

Install (you already have these):
    pip install torch torchvision pillow numpy

Usage:
    python rescore_dedup.py --split "C:/path/to/clean_split.csv" ^
                            --model "C:/path/to/models/quality_model.pt"

Outputs (written next to this script):
    eval_report_dedup.txt
    eval_report_dedup.json

Label parsing, class lists, model architecture and the validation transform
are copied verbatim from the training pipeline so the comparison is fair.
"""

import argparse
import csv
import json
import os
from collections import Counter

import numpy as np
from PIL import Image
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
import torchvision.transforms as transforms
from torchvision.models import resnet18

# ----------------------------------------------------------------------
# COPIED VERBATIM FROM TRAINING PIPELINE — do not edit independently
# ----------------------------------------------------------------------

PRODUCT_CLASSES = [
    "apple", "banana", "bitter_gourd", "capsicum", "carrot", "cucumber",
    "grape", "guava", "jujube", "mango", "orange", "pomegranate",
    "potato", "strawberry", "tomato",
]
DEFECT_CLASSES = ["fresh", "minor_defect", "major_defect"]

PRODUCT_ALIASES = {
    "bellpepper": "capsicum",
    "bell_pepper": "capsicum",
    "pepper": "capsicum",
    "bittergourd": "bitter_gourd",
    "bitter gourd": "bitter_gourd",
    "grapes": "grape",
    "tomatoes": "tomato",
    "carrots": "carrot",
    "potatoes": "potato",
    "oranges": "orange",
    "apples": "apple",
    "bananas": "banana",
    "strawberries": "strawberry",
}

FRESH_KEYWORDS = ("healthy", "fresh", "good")
MAJOR_KEYWORDS = ("rotten", "stale", "spoiled", "diseased", "bad", "major")
MINOR_KEYWORDS = ("minor", "moderate", "slight")


class MultiHeadProduceModel(nn.Module):
    def __init__(self, num_products=len(PRODUCT_CLASSES), num_defects=len(DEFECT_CLASSES)):
        super().__init__()
        backbone = resnet18(weights=None)  # weights come from the checkpoint
        in_features = backbone.fc.in_features
        backbone.fc = nn.Identity()
        self.backbone = backbone
        self.product_head = nn.Linear(in_features, num_products)
        self.defect_head = nn.Linear(in_features, num_defects)

    def forward(self, x):
        features = self.backbone(x)
        return self.product_head(features), self.defect_head(features)


def parse_labels_from_folder(folder_name: str):
    name = folder_name.lower().replace("-", "_").replace("  ", " ").strip()

    product_idx = None
    for alias, canonical in PRODUCT_ALIASES.items():
        if alias in name:
            product_idx = PRODUCT_CLASSES.index(canonical)
            break
    if product_idx is None:
        for p in sorted(PRODUCT_CLASSES, key=len, reverse=True):
            if p in name or p.replace("_", " ") in name:
                product_idx = PRODUCT_CLASSES.index(p)
                break
    if product_idx is None:
        return None, None

    defect_idx = None
    if any(k in name for k in MINOR_KEYWORDS):
        defect_idx = DEFECT_CLASSES.index("minor_defect")
    elif any(k in name for k in MAJOR_KEYWORDS):
        defect_idx = DEFECT_CLASSES.index("major_defect")
    elif any(k in name for k in FRESH_KEYWORDS):
        defect_idx = DEFECT_CLASSES.index("fresh")

    if defect_idx is None:
        return None, None

    return product_idx, defect_idx


# Must match the training pipeline's val_transform exactly.
VAL_TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# ----------------------------------------------------------------------


class SplitCsvDataset(Dataset):
    """Reads file paths from clean_split.csv and re-derives labels
    from each file's immediate parent folder."""

    def __init__(self, csv_path, split_name="val", transform=VAL_TRANSFORM):
        self.transform = transform
        self.samples = []
        self.skipped = 0
        self.missing = 0
        skipped_folders = Counter()

        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["split"] != split_name:
                    continue
                path = row["filepath"]
                if not os.path.exists(path):
                    self.missing += 1
                    continue
                folder = os.path.basename(os.path.dirname(path))
                prod_idx, def_idx = parse_labels_from_folder(folder)
                if prod_idx is None or def_idx is None:
                    self.skipped += 1
                    skipped_folders[folder] += 1
                    continue
                self.samples.append((path, prod_idx, def_idx))

        if skipped_folders:
            print("\n  Folders skipped (labels unparseable — same rule as training):")
            for folder, count in skipped_folders.most_common(20):
                print(f"    {folder}: {count} images")
            print()

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, prod_label, def_label = self.samples[idx]
        image = Image.open(path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, prod_label, def_label

    def label_distribution(self):
        return (Counter(s[1] for s in self.samples),
                Counter(s[2] for s in self.samples))


def compute_metrics(y_true, y_pred, class_names):
    """Same metric code as the training pipeline, plus a macro F1 that
    excludes classes with zero support."""
    n = len(class_names)
    cm = np.zeros((n, n), dtype=int)
    for t, p in zip(y_true, y_pred):
        cm[t][p] += 1

    per_class = {}
    for i, name in enumerate(class_names):
        tp = cm[i][i]
        fp = cm[:, i].sum() - tp
        fn = cm[i, :].sum() - tp
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        per_class[name] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": int(cm[i, :].sum()),
        }

    accuracy = float(np.trace(cm) / cm.sum()) if cm.sum() else 0.0
    all_f1 = [v["f1"] for v in per_class.values()]
    present_f1 = [v["f1"] for v in per_class.values() if v["support"] > 0]
    absent = [k for k, v in per_class.items() if v["support"] == 0]

    return {
        "accuracy": round(accuracy, 4),
        "macro_f1_all_classes": round(float(np.mean(all_f1)), 4),
        "macro_f1_present_classes": round(float(np.mean(present_f1)), 4) if present_f1 else 0.0,
        "classes_with_zero_support": absent,
        "per_class": per_class,
        "confusion_matrix": cm.tolist(),
        "class_names": class_names,
    }


def format_confusion_matrix(cm, class_names):
    width = max(len(c) for c in class_names) + 2
    lines = [" " * width + "".join(f"{c[:6]:>8}" for c in class_names)]
    for i, name in enumerate(class_names):
        lines.append(f"{name:<{width}}" + "".join(f"{v:>8}" for v in cm[i]))
    return "\n".join(lines)


@torch.no_grad()
def evaluate(model, loader, device):
    model.eval()
    prod_true, prod_pred, def_true, def_pred = [], [], [], []
    total = len(loader)
    for i, (images, prod_labels, def_labels) in enumerate(loader, 1):
        images = images.to(device)
        prod_logits, def_logits = model(images)
        prod_pred.extend(torch.argmax(prod_logits, 1).cpu().tolist())
        def_pred.extend(torch.argmax(def_logits, 1).cpu().tolist())
        prod_true.extend(prod_labels.tolist())
        def_true.extend(def_labels.tolist())
        if i % 20 == 0 or i == total:
            print(f"  batch {i}/{total}", end="\r")
    print()
    return prod_true, prod_pred, def_true, def_pred


def main():
    here = os.path.dirname(os.path.abspath(__file__))

    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default=os.path.join(here, "clean_split.csv"),
                    help="path to clean_split.csv from dedupe_check.py")
    ap.add_argument("--model", default=os.path.join(here, "models", "quality_model.pt"),
                    help="path to quality_model.pt")
    ap.add_argument("--batch-size", type=int, default=32)
    args = ap.parse_args()

    if not os.path.exists(args.split):
        raise SystemExit(f"clean_split.csv not found at: {args.split}")
    if not os.path.exists(args.model):
        raise SystemExit(f"model checkpoint not found at: {args.model}")

    print("\n" + "=" * 70)
    print("RE-SCORING EXISTING WEIGHTS ON DEDUPLICATED GROUPED SPLIT")
    print("=" * 70)

    ds = SplitCsvDataset(args.split, split_name="val")
    if len(ds) == 0:
        raise SystemExit("No usable validation images found. Check the paths "
                         "inside clean_split.csv still exist on disk.")

    print(f"Validation images scored : {len(ds)}")
    print(f"Skipped (unparseable)    : {ds.skipped}")
    print(f"Missing on disk          : {ds.missing}")

    prod_counts, def_counts = ds.label_distribution()
    print("\nQuality distribution in this split:")
    for idx in range(len(DEFECT_CLASSES)):
        print(f"  {DEFECT_CLASSES[idx]:<15} {def_counts.get(idx, 0)}")

    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=False, num_workers=0)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\nDevice: {device}")

    model = MultiHeadProduceModel().to(device)
    model.load_state_dict(torch.load(args.model, map_location=device))
    print(f"Loaded weights: {args.model}\n")

    prod_true, prod_pred, def_true, def_pred = evaluate(model, loader, device)
    prod_metrics = compute_metrics(prod_true, prod_pred, PRODUCT_CLASSES)
    def_metrics = compute_metrics(def_true, def_pred, DEFECT_CLASSES)

    # False-fresh rate: major_defect predicted as fresh. The dangerous error.
    maj = DEFECT_CLASSES.index("major_defect")
    fresh = DEFECT_CLASSES.index("fresh")
    false_fresh = sum(1 for t, p in zip(def_true, def_pred) if t == maj and p == fresh)
    n_major = sum(1 for t in def_true if t == maj)
    false_fresh_rate = false_fresh / n_major if n_major else 0.0

    report = {
        "split": "deduplicated grouped split (clean_split.csv)",
        "val_images_scored": len(ds),
        "skipped_unparseable": ds.skipped,
        "missing_on_disk": ds.missing,
        "product_metrics": prod_metrics,
        "quality_metrics": def_metrics,
        "false_fresh_count": false_fresh,
        "major_defect_total": n_major,
        "false_fresh_rate": round(false_fresh_rate, 4),
        "note": "No retraining. Existing checkpoint evaluated on a grouped split "
                "where near-duplicate images are confined to one side.",
    }

    lines = [
        "ORGANICLINK EVALUATION — DEDUPLICATED GROUPED SPLIT",
        "=" * 70,
        f"Validation images scored: {len(ds)}",
        f"Skipped (unparseable):    {ds.skipped}",
        f"Missing on disk:          {ds.missing}",
        "",
        "No retraining was performed. The existing checkpoint was evaluated",
        "on a split where near-duplicate images cannot appear on both sides.",
        "",
        "-" * 70,
        "PRODUCT CLASSIFICATION",
        "-" * 70,
        f"Accuracy: {prod_metrics['accuracy']*100:.2f}%",
        f"Macro F1 (all classes):     {prod_metrics['macro_f1_all_classes']:.4f}",
        f"Macro F1 (present classes): {prod_metrics['macro_f1_present_classes']:.4f}",
    ]
    if prod_metrics["classes_with_zero_support"]:
        lines.append(f"Classes with zero validation samples: "
                     f"{', '.join(prod_metrics['classes_with_zero_support'])}")
        lines.append("  -> report the 'present classes' figure; the other is "
                     "dragged down by classes that have no test data.")
    lines += [
        "",
        f"{'class':<16}{'precision':>11}{'recall':>9}{'f1':>8}{'support':>9}",
    ]
    for name, m in prod_metrics["per_class"].items():
        lines.append(f"{name:<16}{m['precision']:>11.4f}{m['recall']:>9.4f}"
                     f"{m['f1']:>8.4f}{m['support']:>9}")
    lines += [
        "",
        "Confusion matrix (rows = true, cols = predicted):",
        format_confusion_matrix(prod_metrics["confusion_matrix"], PRODUCT_CLASSES),
        "",
        "-" * 70,
        "QUALITY GRADING",
        "-" * 70,
        f"Accuracy: {def_metrics['accuracy']*100:.2f}%",
        f"Macro F1 (all classes):     {def_metrics['macro_f1_all_classes']:.4f}",
        f"Macro F1 (present classes): {def_metrics['macro_f1_present_classes']:.4f}",
        "",
        f"{'class':<16}{'precision':>11}{'recall':>9}{'f1':>8}{'support':>9}",
    ]
    for name, m in def_metrics["per_class"].items():
        lines.append(f"{name:<16}{m['precision']:>11.4f}{m['recall']:>9.4f}"
                     f"{m['f1']:>8.4f}{m['support']:>9}")
    lines += [
        "",
        "Confusion matrix (rows = true, cols = predicted):",
        format_confusion_matrix(def_metrics["confusion_matrix"], DEFECT_CLASSES),
        "",
        "-" * 70,
        "SAFETY-CRITICAL ERROR",
        "-" * 70,
        f"major_defect predicted as fresh: {false_fresh} of {n_major} "
        f"({false_fresh_rate*100:.2f}%)",
        "This is the error that matters on the platform: spoiled produce",
        "published with a quality certificate. Quote this figure in the thesis",
        "alongside the confidence-threshold mitigation.",
    ]

    with open(os.path.join(here, "eval_report_dedup.json"), "w") as f:
        json.dump(report, f, indent=2)
    with open(os.path.join(here, "eval_report_dedup.txt"), "w") as f:
        f.write("\n".join(lines))

    print("\n".join(lines))
    print(f"\nWritten: {os.path.join(here, 'eval_report_dedup.txt')}")


if __name__ == "__main__":
    main()
