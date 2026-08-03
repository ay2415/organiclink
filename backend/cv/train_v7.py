"""
train_v7.py - Two-phase retrain of the ResNet18 dual-head produce grading model.

Scope vs the original train.py:
  - Scans ONLY backend/cv/data/Fruit And Vegetable Diseases Dataset.
    (Processed Images_Fruits and "quality dataset" are NOT scanned. The broken
    ARCHIVE_DIR reference from train.py is dropped entirely.)
  - 14 product classes. "lime" and "bitter_gourd" are dropped completely -
    any path containing "lime", "lemon", or "bitter" is skipped, unlabeled.
  - Binary defect head: ["fresh", "defect"]. minor_defect was dropped - the
    scanned dataset has no data for it (no folder anywhere uses "minor",
    "moderate", or "slight"), so it's folded into "defect".
  - Two-phase training: warmup (backbone frozen, lr=1e-3, 3 epochs) then
    finetune (backbone unfrozen, lr=1e-4, up to 12 epochs, early stopping
    with patience=4 on combined val score).
  - Real 3-way split: a 10% held-out test set is set aside FIRST (fixed
    seed) and never touched during training or checkpoint selection. The
    remaining 90% is split 80/20 into train/val (fixed seed=42).
  - Checkpoints and reports are versioned by date/epoch and NEVER overwrite
    the currently deployed backend/cv/models/grading_model.pt or the
    existing eval_report.json / eval_report.txt.

This script does not run automatically when imported; call
run_training_pipeline() explicitly (e.g. via `python train_v7.py`).
"""

import os
import re
import sys
import json
import time
import datetime
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
DISEASES_DATASET_DIR = os.path.join(BASE_DIR, "data", "Fruit And Vegetable Diseases Dataset")
MODELS_DIR = os.path.join(BASE_DIR, "models")
CURRENT_MODEL_PATH = os.path.join(MODELS_DIR, "grading_model.pt")  # NEVER written to by this script

# --- classes -----------------------------------------------------------
# 14 products. "lime" and "bitter_gourd" are intentionally excluded - see
# SKIP_KEYWORDS below, which drops any lime/lemon/bitter path entirely.
PRODUCT_CLASSES = [
    "apple", "banana", "capsicum", "carrot", "cucumber",
    "grape", "guava", "jujube", "mango", "orange", "pomegranate",
    "potato", "strawberry", "tomato",
]
DEFECT_CLASSES = ["fresh", "defect"]  # binary head: no separate minor_defect (no data for it)

PRODUCT_ALIASES = {
    "bellpepper": "capsicum",
    "bell_pepper": "capsicum",
    "pepper": "capsicum",
    "grapes": "grape",
    "tomatoes": "tomato",
    "carrots": "carrot",
    "potatoes": "potato",
    "oranges": "orange",
    "apples": "apple",
    "bananas": "banana",
    "strawberries": "strawberry",
}

# Any path containing one of these is skipped entirely - not labeled at all.
SKIP_KEYWORDS = ("lime", "lemon", "bitter")

FRESH_KEYWORDS = ("healthy", "fresh", "good")
# Everything non-fresh folds into "defect" - includes what used to be its own
# minor_defect bucket (minor, moderate, slight), since that data doesn't exist here.
DEFECT_KEYWORDS = ("rotten", "stale", "spoiled", "diseased", "bad", "major",
                    "minor", "moderate", "slight")

# --- hyperparameters -----------------------------------------------------
WARMUP_EPOCHS = 3
FINETUNE_MAX_EPOCHS = 12
LR_HEAD = 1e-3          # warmup phase, heads only
LR_FINETUNE = 1e-4      # finetune phase, all params
EARLY_STOP_PATIENCE = 4  # finetune phase only
WEIGHT_CAP = 5.0
BATCH_SIZE = 32
WEIGHT_DECAY = 1e-4
IMG_SIZE = 224
SEED = 42
TEST_FRACTION = 0.10          # held out first, fixed seed, never used in training/selection
VAL_FRACTION_OF_REMAINDER = 0.20  # of the remaining 90%, split 80/20 train/val
MIN_CLASS_IMAGES = 100


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


def _word_match(keyword: str, name: str) -> bool:
    """
    True if `keyword` appears in `name` bounded by non-alphanumeric characters
    (or string start/end) on both sides - i.e. as a whole "word", not as a
    substring of a longer word.

    Without this, alias "pepper" substring-matches inside unrelated filenames
    like "saltandpepper_IMG123.jpg" (a salt-and-pepper noise augmentation
    prefix, nothing to do with capsicum/bell pepper), silently mislabeling
    those images. Same class of bug applies to any keyword that happens to be
    a substring of another word (e.g. "lime" inside "slime", "grape" inside
    a hypothetical "grapefruit").
    """
    pattern = r"(?:^|[^a-z0-9])" + re.escape(keyword) + r"(?:$|[^a-z0-9])"
    return re.search(pattern, name) is not None


def parse_labels_from_path(full_path: str):
    """
    Parse (product, defect) from the file path and folder name.
    Returns (product_index, defect_index) or (None, None) if unparseable
    or explicitly excluded (lime / lemon / bitter).
    """
    name = full_path.lower().replace("-", "_").replace("\\", "/").replace("  ", " ").strip()

    if any(_word_match(k, name) for k in SKIP_KEYWORDS):
        return None, None

    # --- product ---
    product_idx = None
    for alias, canonical in PRODUCT_ALIASES.items():
        if _word_match(alias, name):
            product_idx = PRODUCT_CLASSES.index(canonical)
            break
    if product_idx is None:
        for p in sorted(PRODUCT_CLASSES, key=len, reverse=True):
            if _word_match(p, name) or _word_match(p.replace("_", " "), name):
                product_idx = PRODUCT_CLASSES.index(p)
                break
    if product_idx is None:
        return None, None

    # --- defect condition (binary: fresh vs defect) ---
    # Defect keywords checked first: if a path is ambiguous (both a fresh and a
    # defect keyword present), lean toward "defect" - matches the original
    # script's precedence and is the safer default for a quality-grading app.
    defect_idx = None
    if any(k in name for k in DEFECT_KEYWORDS):
        defect_idx = DEFECT_CLASSES.index("defect")
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

                for fname in image_files:
                    full_p = os.path.join(root, fname)
                    prod_idx, def_idx = parse_labels_from_path(full_p)

                    if prod_idx is None or def_idx is None:
                        self.skipped += 1
                        skipped_folders[os.path.basename(root)] += 1
                        continue

                    self.samples.append((full_p, prod_idx, def_idx))

        if skipped_folders:
            print("\n  Skipped folders (excluded or unparseable labels):")
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
        prod_counts = Counter(s[1] for s in self.samples)
        def_counts = Counter(s[2] for s in self.samples)
        return prod_counts, def_counts


class TransformSubset(Subset):
    """Subset that applies its OWN transform (train/val/test each need a different one)."""

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


def format_metrics_block(title, metrics):
    lines = [
        "-" * 60,
        title,
        "-" * 60,
        f"Accuracy: {metrics['accuracy']*100:.2f}%   Macro F1: {metrics['macro_f1']:.4f}",
        "",
        f"{'class':<16}{'precision':>11}{'recall':>9}{'f1':>8}{'support':>9}",
    ]
    for name, m in metrics["per_class"].items():
        lines.append(f"{name:<16}{m['precision']:>11.4f}{m['recall']:>9.4f}"
                     f"{m['f1']:>8.4f}{m['support']:>9}")
    lines += [
        "",
        "Confusion matrix (rows = true, cols = predicted):",
        format_confusion_matrix(metrics["confusion_matrix"], metrics["class_names"]),
        "",
    ]
    return lines


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


def preflight_check(full_dataset, prod_counts, def_counts):
    """Print class-by-class counts. Warn under MIN_CLASS_IMAGES. Abort on any 0-image class."""
    print("\n" + "=" * 75)
    print("PRE-FLIGHT DATASET CHECK")
    print("=" * 75)
    print(f"Total usable images: {len(full_dataset)}   Skipped: {full_dataset.skipped}\n")

    zero_classes = []
    low_classes = []

    print("Product classes:")
    for idx, name in enumerate(PRODUCT_CLASSES):
        count = prod_counts.get(idx, 0)
        flag = ""
        if count == 0:
            flag = "  <-- ABORT: zero images"
            zero_classes.append(name)
        elif count < MIN_CLASS_IMAGES:
            flag = f"  <-- WARNING: under {MIN_CLASS_IMAGES}"
            low_classes.append(name)
        print(f"  {name:<15} {count:>6}{flag}")

    print("\nDefect classes:")
    for idx, name in enumerate(DEFECT_CLASSES):
        count = def_counts.get(idx, 0)
        flag = ""
        if count == 0:
            flag = "  <-- ABORT: zero images"
            zero_classes.append(name)
        elif count < MIN_CLASS_IMAGES:
            flag = f"  <-- WARNING: under {MIN_CLASS_IMAGES}"
            low_classes.append(name)
        print(f"  {name:<15} {count:>6}{flag}")

    if low_classes:
        print(f"\n[warn] classes with fewer than {MIN_CLASS_IMAGES} images (continuing anyway): {low_classes}")

    if zero_classes:
        print(f"\n[ABORT] The following classes have ZERO images: {zero_classes}")
        print("Training cannot proceed - every class must have at least one image.")
        raise SystemExit(1)

    print("\nPre-flight check passed.\n")


def three_way_split(n_samples):
    """
    Fixed-seed 3-way split:
      - TEST_FRACTION (10%) held out FIRST, never touched again.
      - Remaining 90% split 80/20 into train/val (fixed seed=42, matches prior runs).
    """
    indices = np.random.RandomState(SEED).permutation(n_samples)

    test_size = int(round(n_samples * TEST_FRACTION))
    test_indices = indices[:test_size].tolist()

    remainder = indices[test_size:]
    val_size = int(round(len(remainder) * VAL_FRACTION_OF_REMAINDER))
    val_indices = remainder[:val_size].tolist()
    train_indices = remainder[val_size:].tolist()

    return train_indices, val_indices, test_indices


def build_transforms():
    train_transform = transforms.Compose([
        transforms.RandomResizedCrop(IMG_SIZE, scale=(0.6, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(p=0.3),
        transforms.RandomRotation(30),
        transforms.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.4, hue=0.1),
        transforms.RandomApply([transforms.GaussianBlur(3)], p=0.2),
        transforms.RandomGrayscale(p=0.05),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        transforms.RandomErasing(p=0.2, scale=(0.02, 0.15)),
    ])
    # val/test share the same deterministic transform.
    eval_transform = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    return train_transform, eval_transform


def run_training_pipeline():
    os.makedirs(MODELS_DIR, exist_ok=True)
    start_time = time.time()
    run_date = datetime.date.today().isoformat()

    print("\n" + "=" * 75)
    print("ORGANICLINK TRAINING PIPELINE v7 (2-phase, 14-class, 3-way split)")
    print("=" * 75)

    full_dataset = ProduceDataset([DISEASES_DATASET_DIR])

    if len(full_dataset) == 0:
        print("ERROR: no usable images found. Check DISEASES_DATASET_DIR.")
        raise SystemExit(1)

    prod_counts, def_counts = full_dataset.label_distribution()
    preflight_check(full_dataset, prod_counts, def_counts)

    # Class weights with capping (mirrors train.py's approach), computed on the full pool.
    raw_prod_weights = [len(full_dataset) / (len(PRODUCT_CLASSES) * max(prod_counts.get(i, 1), 1))
                        for i in range(len(PRODUCT_CLASSES))]
    raw_def_weights = [len(full_dataset) / (len(DEFECT_CLASSES) * max(def_counts.get(i, 1), 1))
                       for i in range(len(DEFECT_CLASSES))]

    train_transform, eval_transform = build_transforms()

    train_indices, val_indices, test_indices = three_way_split(len(full_dataset))

    train_ds = TransformSubset(full_dataset, train_indices, train_transform)
    val_ds = TransformSubset(full_dataset, val_indices, eval_transform)
    test_ds = TransformSubset(full_dataset, test_indices, eval_transform)

    print("Split (fixed seed=42, test held out first, then 80/20 train/val of the remainder):")
    print(f"  Train: {len(train_ds)}")
    print(f"  Val:   {len(val_ds)}")
    print(f"  Test:  {len(test_ds)}  (held out - never used for training or checkpoint selection)")

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\nDevice: {device}\n")

    model = MultiHeadProduceModel().to(device)

    prod_weights = torch.tensor([min(w, WEIGHT_CAP) for w in raw_prod_weights], dtype=torch.float32).to(device)
    def_weights = torch.tensor([min(w, WEIGHT_CAP) for w in raw_def_weights], dtype=torch.float32).to(device)

    # NO label smoothing.
    criterion_prod = nn.CrossEntropyLoss(weight=prod_weights)
    criterion_def = nn.CrossEntropyLoss(weight=def_weights)

    best_val_score = 0.0
    best_epoch = None
    best_phase = None
    best_state_dict = None
    history = []
    global_epoch = 0

    def run_epoch(loader, optimizer):
        model.train()
        running_loss = 0.0
        total = 0
        for images, prod_labels, def_labels in loader:
            images = images.to(device)
            prod_labels = prod_labels.to(device)
            def_labels = def_labels.to(device)

            optimizer.zero_grad()
            prod_logits, def_logits = model(images)
            loss = (1.5 * criterion_prod(prod_logits, prod_labels) + 1.0 * criterion_def(def_logits, def_labels))
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            total += images.size(0)
        return running_loss / total

    def validate_and_maybe_checkpoint(phase, train_loss):
        nonlocal best_val_score, best_epoch, best_phase, best_state_dict, global_epoch
        prod_true, prod_pred, def_true, def_pred = evaluate(model, val_loader, device)
        prod_metrics = compute_metrics(prod_true, prod_pred, PRODUCT_CLASSES)
        def_metrics = compute_metrics(def_true, def_pred, DEFECT_CLASSES)
        val_score = (prod_metrics["accuracy"] + def_metrics["accuracy"]) / 2 * 100

        print(f"[{phase:>8}] Epoch {global_epoch:02d} loss {train_loss:.4f} | "
              f"VAL product {prod_metrics['accuracy']*100:.1f}% | "
              f"VAL quality {def_metrics['accuracy']*100:.1f}% | "
              f"combined {val_score:.1f}%")

        history.append({
            "epoch": global_epoch,
            "phase": phase,
            "train_loss": round(train_loss, 4),
            "val_product_acc": prod_metrics["accuracy"],
            "val_quality_acc": def_metrics["accuracy"],
        })

        improved = val_score > best_val_score
        if improved:
            best_val_score = val_score
            best_epoch = global_epoch
            best_phase = phase
            best_state_dict = {k: v.detach().clone() for k, v in model.state_dict().items()}
            print(f"   -> new best (val {val_score:.1f}%), held in memory")
        return improved

    # --- Phase 1: warmup (backbone frozen, heads only) ---
    print("\n" + "-" * 75)
    print(f"PHASE 1: WARMUP ({WARMUP_EPOCHS} epochs, backbone frozen, lr={LR_HEAD})")
    print("-" * 75)
    for param in model.backbone.parameters():
        param.requires_grad = False

    warmup_optimizer = optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=LR_HEAD, weight_decay=WEIGHT_DECAY,
    )

    for _ in range(WARMUP_EPOCHS):
        global_epoch += 1
        train_loss = run_epoch(train_loader, warmup_optimizer)
        validate_and_maybe_checkpoint("warmup", train_loss)

    # --- Phase 2: finetune (backbone unfrozen, full model) ---
    print("\n" + "-" * 75)
    print(f"PHASE 2: FINETUNE (up to {FINETUNE_MAX_EPOCHS} epochs, backbone unfrozen, lr={LR_FINETUNE}, "
          f"early stop patience={EARLY_STOP_PATIENCE})")
    print("-" * 75)
    for param in model.backbone.parameters():
        param.requires_grad = True

    finetune_optimizer = optim.AdamW(model.parameters(), lr=LR_FINETUNE, weight_decay=WEIGHT_DECAY)

    epochs_without_improvement = 0
    for _ in range(FINETUNE_MAX_EPOCHS):
        global_epoch += 1
        train_loss = run_epoch(train_loader, finetune_optimizer)
        improved = validate_and_maybe_checkpoint("finetune", train_loss)

        if improved:
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= EARLY_STOP_PATIENCE:
                print(f"   -> early stopping: no val improvement for {EARLY_STOP_PATIENCE} consecutive epochs")
                break

    if best_state_dict is None:
        print("ERROR: no checkpoint ever improved on val - nothing to save.")
        raise SystemExit(1)

    # --- Final evaluation on VAL (with best weights) and held-out TEST ---
    model.load_state_dict(best_state_dict)

    val_prod_true, val_prod_pred, val_def_true, val_def_pred = evaluate(model, val_loader, device)
    val_prod_metrics = compute_metrics(val_prod_true, val_prod_pred, PRODUCT_CLASSES)
    val_def_metrics = compute_metrics(val_def_true, val_def_pred, DEFECT_CLASSES)

    test_prod_true, test_prod_pred, test_def_true, test_def_pred = evaluate(model, test_loader, device)
    test_prod_metrics = compute_metrics(test_prod_true, test_prod_pred, PRODUCT_CLASSES)
    test_def_metrics = compute_metrics(test_def_true, test_def_pred, DEFECT_CLASSES)

    elapsed = (time.time() - start_time) / 60.0

    # --- Versioned checkpoint + report filenames (never touch the deployed model) ---
    checkpoint_filename = f"grading_model_{run_date}_ep{best_epoch:02d}.pt"
    checkpoint_path = os.path.join(MODELS_DIR, checkpoint_filename)
    report_json_path = os.path.join(MODELS_DIR, f"eval_report_{run_date}.json")
    report_txt_path = os.path.join(MODELS_DIR, f"eval_report_{run_date}.txt")

    if os.path.abspath(checkpoint_path) == os.path.abspath(CURRENT_MODEL_PATH):
        # Should never happen (versioned filename always differs from grading_model.pt),
        # but guard explicitly since overwriting the deployed model is forbidden.
        raise RuntimeError("Refusing to write: versioned checkpoint path collides with the deployed model path.")

    tmp_path = checkpoint_path + ".tmp"
    torch.save(best_state_dict, tmp_path)
    os.replace(tmp_path, checkpoint_path)

    report = {
        "run_date": run_date,
        "script": "train_v7.py",
        "architecture": "MultiHeadProduceModel (ResNet18, 2-phase: warmup+finetune) - 14 products, binary defect head (fresh vs defect)",
        "dataset_scanned": [DISEASES_DATASET_DIR],
        "hyperparameters": {
            "warmup_epochs": WARMUP_EPOCHS,
            "finetune_max_epochs": FINETUNE_MAX_EPOCHS,
            "lr_head": LR_HEAD,
            "lr_finetune": LR_FINETUNE,
            "early_stop_patience": EARLY_STOP_PATIENCE,
            "batch_size": BATCH_SIZE,
            "weight_decay": WEIGHT_DECAY,
            "weight_cap": WEIGHT_CAP,
            "label_smoothing": False,
            "img_size": IMG_SIZE,
            "seed": SEED,
            "test_fraction": TEST_FRACTION,
            "val_fraction_of_remainder": VAL_FRACTION_OF_REMAINDER,
        },
        "total_images": len(full_dataset),
        "skipped_images": full_dataset.skipped,
        "train_samples": len(train_ds),
        "val_samples": len(val_ds),
        "test_samples": len(test_ds),
        "best_epoch": best_epoch,
        "best_phase": best_phase,
        "best_val_score_combined": round(best_val_score, 2),
        "training_time_minutes": round(elapsed, 2),
        "history": history,
        "val_metrics": {
            "product_metrics": val_prod_metrics,
            "quality_metrics": val_def_metrics,
        },
        "test_metrics": {
            "product_metrics": test_prod_metrics,
            "quality_metrics": test_def_metrics,
        },
        "checkpoint_path": checkpoint_path,
        "note": (
            "val_metrics were used for checkpoint selection (some optimistic bias expected). "
            "test_metrics are on a 10% held-out split NEVER used during training or checkpoint "
            "selection - treat test_metrics as the trustworthy generalization estimate. "
            "The currently deployed backend/cv/models/grading_model.pt was NOT modified by this run."
        ),
    }

    with open(report_json_path, "w") as f:
        json.dump(report, f, indent=2)

    lines = [
        "ORGANICLINK EVALUATION REPORT (train_v7.py)",
        "=" * 60,
        f"Run date: {run_date}",
        f"Dataset scanned: {DISEASES_DATASET_DIR}",
        f"Images (usable): {len(full_dataset)}   skipped: {full_dataset.skipped}",
        f"Train: {len(train_ds)}   Val: {len(val_ds)}   Test (held out): {len(test_ds)}",
        f"Best epoch: {best_epoch} (phase={best_phase})   Time: {elapsed:.1f} min",
        f"Checkpoint saved to: {checkpoint_path}",
        f"NOTE: {CURRENT_MODEL_PATH} was NOT modified by this run.",
        "",
        "=" * 60,
        "VALIDATION METRICS (used for checkpoint selection - optimistic bias expected)",
        "=" * 60,
    ]
    lines += format_metrics_block("PRODUCT CLASSIFICATION (VAL)", val_prod_metrics)
    lines += format_metrics_block("QUALITY GRADING (VAL)", val_def_metrics)
    lines += [
        "=" * 60,
        "HELD-OUT TEST METRICS (never used in training or checkpoint selection)",
        "=" * 60,
    ]
    lines += format_metrics_block("PRODUCT CLASSIFICATION (TEST)", test_prod_metrics)
    lines += format_metrics_block("QUALITY GRADING (TEST)", test_def_metrics)

    with open(report_txt_path, "w") as f:
        f.write("\n".join(lines))

    print("\n" + "\n".join(lines[:12]))
    print(f"\nFull report: {report_txt_path}")
    print(f"Checkpoint:  {checkpoint_path}")
    print(f"(deployed grading_model.pt untouched)\n")

    return report


if __name__ == "__main__":
    run_training_pipeline()
