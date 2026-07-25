"""
FIXED Training Pipeline for OrganicLink produce quality + product verification.

Fixes applied vs the previous version:
  1. Transform leak fixed - train and val now genuinely use different transforms.
  2. Real validation loop added (previously val_loader was never used).
  3. Per-class precision / recall / F1 + confusion matrix written to eval_report.
  4. Best checkpoint selected on VALIDATION accuracy, not training accuracy.
  5. Strict label parsing - unmatched images are SKIPPED, not silently
     relabelled as "fresh tomato".
  6. Product parsed from the immediate folder name, not the whole absolute path.
  7. "milk" removed from PRODUCT_CLASSES (no images; milk is not CV-graded).
  8. Class-imbalance handling via weighted loss.
  9. Fresh checkpoints by default (no silent resume from a bad model).
"""

import os
import json
import time
import warnings
from collections import Counter

import numpy as np
from PIL import Image
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, Subset
import torchvision.transforms as transforms
from torchvision.models import resnet18, ResNet18_Weights

warnings.filterwarnings("ignore", category=UserWarning, module="PIL")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_DIR = os.path.join(BASE_DIR, "archive")
QUALITY_DATASET_DIR = os.path.join(BASE_DIR, "quality dataset")
DISEASES_DATASET_DIR = os.path.join(BASE_DIR, "Fruit And Vegetable Diseases Dataset")
MODELS_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODELS_DIR, "quality_model.pt")
REPORT_JSON_PATH = os.path.join(MODELS_DIR, "eval_report.json")
REPORT_TXT_PATH = os.path.join(MODELS_DIR, "eval_report.txt")

# NOTE: "milk" removed - no training images exist and milk is never CV-graded.
# "onion" is NOT here because the Diseases dataset contains no onion images.
# Add "onion" ONLY after you add real onion photos under an Onion__Healthy /
# Onion__Rotten folder structure. Until then the app must not offer CV grading
# for onion.
PRODUCT_CLASSES = [
    "apple", "banana", "bitter_gourd", "capsicum", "carrot", "cucumber",
    "grape", "guava", "jujube", "mango", "orange", "pomegranate",
    "potato", "strawberry", "tomato",
]
DEFECT_CLASSES = ["fresh", "minor_defect", "major_defect"]

# Folder-name aliases -> canonical product
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
        backbone = resnet18(weights=ResNet18_Weights.DEFAULT)
        in_features = backbone.fc.in_features
        backbone.fc = nn.Identity()
        self.backbone = backbone
        self.product_head = nn.Linear(in_features, num_products)
        self.defect_head = nn.Linear(in_features, num_defects)

    def forward(self, x):
        features = self.backbone(x)
        return self.product_head(features), self.defect_head(features)


def parse_labels_from_folder(folder_name: str):
    """
    Parse (product, defect) from the IMMEDIATE folder name only.

    Returns (product_index, defect_index) or (None, None) if unparseable.
    Unparseable samples are SKIPPED - never silently relabelled.
    """
    name = folder_name.lower().replace("-", "_").replace("  ", " ").strip()

    # --- product ---
    product_idx = None
    for alias, canonical in PRODUCT_ALIASES.items():
        if alias in name:
            product_idx = PRODUCT_CLASSES.index(canonical)
            break
    if product_idx is None:
        # Longest match first so "bitter_gourd" beats nothing and
        # short names don't win by accident.
        for p in sorted(PRODUCT_CLASSES, key=len, reverse=True):
            if p in name or p.replace("_", " ") in name:
                product_idx = PRODUCT_CLASSES.index(p)
                break
    if product_idx is None:
        return None, None

    # --- defect condition ---
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


class ProduceDataset(Dataset):
    """Scans dataset roots and keeps ONLY samples whose labels parse cleanly."""

    def __init__(self, search_dirs, transform=None):
        self.transform = transform
        self.samples = []
        self.skipped = 0
        skipped_folders = Counter()

        for target_dir in search_dirs:
            if not os.path.exists(target_dir):
                print(f"  [warn] dataset dir not found, skipping: {target_dir}")
                continue

            for root, _dirs, files in os.walk(target_dir):
                image_files = [f for f in files
                               if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
                if not image_files:
                    continue

                folder_name = os.path.basename(root)
                prod_idx, def_idx = parse_labels_from_folder(folder_name)

                if prod_idx is None or def_idx is None:
                    self.skipped += len(image_files)
                    skipped_folders[folder_name] += len(image_files)
                    continue

                for fname in image_files:
                    self.samples.append((os.path.join(root, fname), prod_idx, def_idx))

        if skipped_folders:
            print("\n  Skipped folders (labels could not be parsed):")
            for folder, count in skipped_folders.most_common(20):
                print(f"    {folder}: {count} images")
            print("  -> If any of these are real data, add them to "
                  "PRODUCT_ALIASES or the keyword lists.\n")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, prod_label, def_label = self.samples[idx]
        image = Image.open(path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, prod_label, def_label

    def label_distribution(self):
        prod_counts = Counter(s[1] for s in self.samples)
        def_counts = Counter(s[2] for s in self.samples)
        return prod_counts, def_counts


class TransformSubset(Subset):
    """
    Subset that applies its OWN transform.

    This is the fix for the transform leak: previously both subsets shared
    one underlying dataset object, so setting val_transform silently
    overwrote train_transform and augmentation never ran.
    """

    def __init__(self, dataset, indices, transform):
        super().__init__(dataset, indices)
        self.transform = transform

    def __getitem__(self, idx):
        path, prod_label, def_label = self.dataset.samples[self.indices[idx]]
        image = Image.open(path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, prod_label, def_label

    def __getitems__(self, indices):
        return [self.__getitem__(idx) for idx in indices]


def compute_metrics(y_true, y_pred, class_names):
    """Per-class precision / recall / F1 + confusion matrix. No sklearn needed."""
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
    macro_f1 = float(np.mean([v["f1"] for v in per_class.values()]))
    return {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
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
    for images, prod_labels, def_labels in loader:
        images = images.to(device)
        prod_logits, def_logits = model(images)
        prod_pred.extend(torch.argmax(prod_logits, 1).cpu().tolist())
        def_pred.extend(torch.argmax(def_logits, 1).cpu().tolist())
        prod_true.extend(prod_labels.tolist())
        def_true.extend(def_labels.tolist())
    return prod_true, prod_pred, def_true, def_pred


def run_training_pipeline(epochs=25, batch_size=32, learning_rate=3e-4, resume=False):
    os.makedirs(MODELS_DIR, exist_ok=True)
    start_time = time.time()

    print("\n" + "=" * 75)
    print("ORGANICLINK TRAINING PIPELINE (FIXED)")
    print("=" * 75)

    full_dataset = ProduceDataset(
        [ARCHIVE_DIR, QUALITY_DATASET_DIR, DISEASES_DATASET_DIR]
    )

    if len(full_dataset) == 0:
        print("ERROR: no usable images found. Check dataset paths and folder naming.")
        return None

    prod_counts, def_counts = full_dataset.label_distribution()
    print(f"Usable images : {len(full_dataset)}")
    print(f"Skipped images: {full_dataset.skipped}")
    print("\nProduct distribution:")
    for idx, count in sorted(prod_counts.items()):
        print(f"  {PRODUCT_CLASSES[idx]:<15} {count}")
    print("\nQuality distribution:")
    for idx, count in sorted(def_counts.items()):
        print(f"  {DEFECT_CLASSES[idx]:<15} {count}")

    missing = [PRODUCT_CLASSES[i] for i in range(len(PRODUCT_CLASSES))
               if prod_counts.get(i, 0) == 0]
    if missing:
        print(f"\n  [warn] classes with ZERO images: {missing}")
        print("  These can never be predicted correctly. Remove them from "
              "PRODUCT_CLASSES or add data.\n")

    train_transform = transforms.Compose([
        transforms.RandomResizedCrop(224, scale=(0.7, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(p=0.2),
        transforms.RandomRotation(20),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.05),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    # IMPORTANT: inference.py must use EXACTLY this transform.
    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    indices = np.random.RandomState(42).permutation(len(full_dataset))
    val_size = max(1, int(len(full_dataset) * 0.2))
    val_indices = indices[:val_size].tolist()
    train_indices = indices[val_size:].tolist()

    train_ds = TransformSubset(full_dataset, train_indices, train_transform)
    val_ds = TransformSubset(full_dataset, val_indices, val_transform)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    print(f"\nTrain: {len(train_ds)}   Val: {len(val_ds)}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}\n")
    model = MultiHeadProduceModel().to(device)

    if resume and os.path.exists(MODEL_PATH):
        try:
            model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
            print("Resumed from existing checkpoint.")
        except Exception as e:
            print(f"Could not resume ({e}); starting fresh.")

    # Class weights so rare classes are not ignored
    prod_weights = torch.tensor(
        [len(full_dataset) / (len(PRODUCT_CLASSES) * max(prod_counts.get(i, 1), 1))
         for i in range(len(PRODUCT_CLASSES))], dtype=torch.float32
    ).to(device)
    def_weights = torch.tensor(
        [len(full_dataset) / (len(DEFECT_CLASSES) * max(def_counts.get(i, 1), 1))
         for i in range(len(DEFECT_CLASSES))], dtype=torch.float32
    ).to(device)

    criterion_prod = nn.CrossEntropyLoss(weight=prod_weights)
    criterion_def = nn.CrossEntropyLoss(weight=def_weights)
    optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_val_score = 0.0
    history = []

    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        total = 0

        for images, prod_labels, def_labels in train_loader:
            images = images.to(device)
            prod_labels = prod_labels.to(device)
            def_labels = def_labels.to(device)

            optimizer.zero_grad()
            prod_logits, def_logits = model(images)
            loss = criterion_prod(prod_logits, prod_labels) + criterion_def(def_logits, def_labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            total += images.size(0)

        scheduler.step()
        train_loss = running_loss / total

        # --- REAL validation ---
        prod_true, prod_pred, def_true, def_pred = evaluate(model, val_loader, device)
        prod_metrics = compute_metrics(prod_true, prod_pred, PRODUCT_CLASSES)
        def_metrics = compute_metrics(def_true, def_pred, DEFECT_CLASSES)

        val_score = (prod_metrics["accuracy"] + def_metrics["accuracy"]) / 2 * 100

        print(f"Epoch [{epoch+1:02d}/{epochs:02d}] loss {train_loss:.4f} | "
              f"VAL product {prod_metrics['accuracy']*100:.1f}% | "
              f"VAL quality {def_metrics['accuracy']*100:.1f}% | "
              f"combined {val_score:.1f}%")

        history.append({
            "epoch": epoch + 1,
            "train_loss": round(train_loss, 4),
            "val_product_acc": prod_metrics["accuracy"],
            "val_quality_acc": def_metrics["accuracy"],
        })

        if val_score > best_val_score:
            best_val_score = val_score
            torch.save(model.state_dict(), MODEL_PATH)
            print(f"   -> saved best checkpoint (val {val_score:.1f}%)")

    # Final evaluation with the best weights
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    prod_true, prod_pred, def_true, def_pred = evaluate(model, val_loader, device)
    prod_metrics = compute_metrics(prod_true, prod_pred, PRODUCT_CLASSES)
    def_metrics = compute_metrics(def_true, def_pred, DEFECT_CLASSES)

    elapsed = (time.time() - start_time) / 60.0

    report = {
        "architecture": "MultiHeadProduceModel (ResNet18, ImageNet pretrained)",
        "total_images": len(full_dataset),
        "skipped_images": full_dataset.skipped,
        "train_samples": len(train_ds),
        "val_samples": len(val_ds),
        "epochs": epochs,
        "training_time_minutes": round(elapsed, 2),
        "product_metrics": prod_metrics,
        "quality_metrics": def_metrics,
        "history": history,
        "note": "All reported metrics are VALIDATION metrics on a held-out 20% split.",
    }

    with open(REPORT_JSON_PATH, "w") as f:
        json.dump(report, f, indent=2)

    lines = [
        "ORGANICLINK EVALUATION REPORT",
        "=" * 60,
        f"Images (usable): {len(full_dataset)}   skipped: {full_dataset.skipped}",
        f"Train: {len(train_ds)}   Validation: {len(val_ds)}",
        f"Epochs: {epochs}   Time: {elapsed:.1f} min",
        "",
        "ALL METRICS BELOW ARE ON THE HELD-OUT VALIDATION SPLIT.",
        "",
        "-" * 60,
        "PRODUCT CLASSIFICATION",
        "-" * 60,
        f"Accuracy: {prod_metrics['accuracy']*100:.2f}%   Macro F1: {prod_metrics['macro_f1']:.4f}",
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
        "-" * 60,
        "QUALITY GRADING",
        "-" * 60,
        f"Accuracy: {def_metrics['accuracy']*100:.2f}%   Macro F1: {def_metrics['macro_f1']:.4f}",
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
    ]

    with open(REPORT_TXT_PATH, "w") as f:
        f.write("\n".join(lines))

    print("\n" + "\n".join(lines[:8]))
    print(f"\nFull report: {REPORT_TXT_PATH}")
    print(f"Model saved: {MODEL_PATH}\n")

    return report


if __name__ == "__main__":
    run_training_pipeline(epochs=25, batch_size=32, learning_rate=3e-4, resume=False)