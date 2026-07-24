"""
Production Deep Learning Neural Network Training Pipeline for OrganicLink.
Scans and fine-tunes Multi-Head ResNet18 across all 3 real produce datasets (44,300+ Images):
1. `backend/cv/archive/`
2. `backend/cv/quality dataset/`
3. `backend/cv/Fruit And Vegetable Diseases Dataset/`

Supported Categories (16 classes):
- apple, banana, bitter_gourd, capsicum, carrot, cucumber, grape, guava, jujube, mango, milk, orange, pomegranate, potato, strawberry, tomato
"""

import os
import json
import time
from PIL import Image
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
import torchvision.transforms as transforms
from torchvision.models import resnet18, ResNet18_Weights

# Define Directory Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_DIR = os.path.join(BASE_DIR, "archive")
QUALITY_DATASET_DIR = os.path.join(BASE_DIR, "quality dataset")
DISEASES_DATASET_DIR = os.path.join(BASE_DIR, "Fruit And Vegetable Diseases Dataset")
MODELS_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODELS_DIR, "quality_model.pt")
REPORT_JSON_PATH = os.path.join(MODELS_DIR, "eval_report.json")

PRODUCT_CLASSES = [
    "apple", "banana", "bitter_gourd", "capsicum", "carrot", "cucumber",
    "grape", "guava", "jujube", "mango", "milk", "orange", "pomegranate",
    "potato", "strawberry", "tomato"
]
DEFECT_CLASSES = ["fresh", "minor_defect", "major_defect"]


class MultiHeadProduceModel(nn.Module):
    def __init__(self, num_products=len(PRODUCT_CLASSES), num_defects=len(DEFECT_CLASSES)):
        super().__init__()
        try:
            backbone = resnet18(weights=ResNet18_Weights.DEFAULT)
        except Exception:
            backbone = resnet18(pretrained=True)
            
        in_features = backbone.fc.in_features
        backbone.fc = nn.Identity()
        self.backbone = backbone

        # Multi-head Output Heads
        self.product_head = nn.Linear(in_features, num_products)
        self.defect_head = nn.Linear(in_features, num_defects)

    def forward(self, x):
        features = self.backbone(x)
        prod_logits = self.product_head(features)
        defect_logits = self.defect_head(features)
        return prod_logits, defect_logits


class RealCombinedDatasetScanner(Dataset):
    """
    Scans and merges images recursively from all 3 real produce datasets.
    Handles naming formats like:
    - Apple__Healthy / Apple__Rotten
    - Carrot__Healthy / Carrot__Rotten
    - fresh_capsicum / stale_capsicum
    """
    def __init__(self, search_dirs, transform=None):
        self.transform = transform
        self.samples = []

        for target_dir in search_dirs:
            if not os.path.exists(target_dir):
                continue

            for root, dirs, files in os.walk(target_dir):
                for fname in files:
                    if fname.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                        full_path = os.path.join(root, fname)
                        folder_path_lower = root.lower()
                        fname_lower = fname.lower()

                        prod_label = None
                        def_label = None

                        # Special Aliases
                        if "bellpepper" in folder_path_lower or "bellpepper" in fname_lower:
                            prod_label = PRODUCT_CLASSES.index("capsicum")

                        # 1. Product Category Mapping
                        if prod_label is None:
                            for i, p in enumerate(PRODUCT_CLASSES):
                                if p in folder_path_lower or p in fname_lower:
                                    prod_label = i
                                    break

                        # Heuristic fallback if product is missing in path
                        if prod_label is None:
                            if "banana" in fname_lower:
                                prod_label = PRODUCT_CLASSES.index("banana")
                            elif "apple" in fname_lower:
                                prod_label = PRODUCT_CLASSES.index("apple")
                            elif "orange" in fname_lower:
                                prod_label = PRODUCT_CLASSES.index("orange")
                            else:
                                prod_label = PRODUCT_CLASSES.index("tomato")

                        # 2. Defect Quality Condition Mapping
                        if "healthy" in folder_path_lower or "fresh" in folder_path_lower:
                            def_label = DEFECT_CLASSES.index("fresh")
                        elif "rotten" in folder_path_lower or "stale" in folder_path_lower or "major" in folder_path_lower or "diseased" in folder_path_lower:
                            def_label = DEFECT_CLASSES.index("major_defect")
                        elif "minor" in folder_path_lower or "defect" in folder_path_lower:
                            def_label = DEFECT_CLASSES.index("minor_defect")
                        else:
                            def_label = DEFECT_CLASSES.index("fresh")

                        if prod_label is not None:
                            self.samples.append((full_path, prod_label, def_label))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, prod_label, def_label = self.samples[idx]
        image = Image.open(path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, prod_label, def_label


def run_training_pipeline(epochs=25, batch_size=32, learning_rate=3e-4):
    os.makedirs(MODELS_DIR, exist_ok=True)
    start_time = time.time()

    dataset_all = RealCombinedDatasetScanner([ARCHIVE_DIR, QUALITY_DATASET_DIR, DISEASES_DATASET_DIR])
    if len(dataset_all) == 0:
        print("\n" + "="*75)
        print("ERROR: NO REAL IMAGES FOUND IN DATASET DIRECTORIES")
        print("="*75 + "\n")
        return None

    print("\n" + "="*75)
    print(f"ORGANICLINK NEURAL NETWORK TRAINING PIPELINE")
    print(f"Total Combined Real Images : {len(dataset_all)}")
    print(f"Target Categories (Classes): {len(PRODUCT_CLASSES)}")
    print(f"Target Training Epochs     : {epochs}")
    print(f"Batch Size                 : {batch_size}")
    print(f"Initial Learning Rate      : {learning_rate}")
    print("="*75 + "\n")

    train_transform = transforms.Compose([
        transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    val_size = max(1, int(len(dataset_all) * 0.2))
    train_size = len(dataset_all) - val_size
    train_ds, val_ds = torch.utils.data.random_split(dataset_all, [train_size, val_size])

    train_ds.dataset.transform = train_transform
    val_ds.dataset.transform = val_transform

    train_loader = DataLoader(train_ds, batch_size=min(batch_size, train_size), shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=min(batch_size, val_size), shuffle=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = MultiHeadProduceModel().to(device)

    # Resume fine-tuning if checkpoint exists with matching shape
    if os.path.exists(MODEL_PATH):
        try:
            state_dict = torch.load(MODEL_PATH, map_location=device)
            model.load_state_dict(state_dict)
            print(f"Loaded existing model checkpoint from {MODEL_PATH} for fine-tuning!")
        except Exception as e:
            print(f"Initializing fresh 16-class model checkpoint ({e})")

    criterion_prod = nn.CrossEntropyLoss()
    criterion_def = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_combined_acc = 0.0

    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        prod_correct = 0
        def_correct = 0
        total = 0

        for images, prod_labels, def_labels in train_loader:
            images = images.to(device)
            prod_labels = prod_labels.to(device)
            def_labels = def_labels.to(device)

            optimizer.zero_grad()
            prod_logits, def_logits = model(images)

            loss_prod = criterion_prod(prod_logits, prod_labels)
            loss_def = criterion_def(def_logits, def_labels)
            total_loss = loss_prod + loss_def

            total_loss.backward()
            optimizer.step()

            running_loss += total_loss.item() * images.size(0)
            _, prod_preds = torch.max(prod_logits, 1)
            _, def_preds = torch.max(def_logits, 1)

            prod_correct += torch.sum(prod_preds == prod_labels.data).item()
            def_correct += torch.sum(def_preds == def_labels.data).item()
            total += images.size(0)

        scheduler.step()

        epoch_loss = running_loss / total
        prod_acc = (prod_correct / total) * 100.0
        def_acc = (def_correct / total) * 100.0
        combined_acc = (prod_acc + def_acc) / 2.0

        print(f"Epoch [{epoch+1:02d}/{epochs:02d}] - Loss: {epoch_loss:.4f} | Product Acc: {prod_acc:.1f}% | Quality Acc: {def_acc:.1f}% | Combined Acc: {combined_acc:.1f}%")

        if combined_acc > best_combined_acc:
            best_combined_acc = combined_acc
            torch.save(model.state_dict(), MODEL_PATH)
            print(f"  --> Saved new best model checkpoint to {MODEL_PATH} (Combined Acc: {combined_acc:.1f}%)")

    elapsed_mins = (time.time() - start_time) / 60.0

    report = {
        "architecture": "MultiHeadProduceModel (ResNet18)",
        "dataset_type": "Real Produce Images (Archive, Quality Dataset & Diseases Dataset)",
        "total_images": len(dataset_all),
        "train_samples": train_size,
        "val_samples": val_size,
        "epochs": epochs,
        "best_combined_acc": round(best_combined_acc, 2),
        "training_time_minutes": round(elapsed_mins, 2),
        "model_path": MODEL_PATH
    }

    with open(REPORT_JSON_PATH, "w") as f:
        json.dump(report, f, indent=2)

    print("\n" + "="*75)
    print(f"TRAINING COMPLETED SUCCESSFULLY!")
    print(f"Best Model Saved To : {MODEL_PATH}")
    print(f"Best Accuracy       : {best_combined_acc:.2f}%")
    print(f"Elapsed Time        : {elapsed_mins:.2f} minutes")
    print("="*75 + "\n")

    return report


if __name__ == "__main__":
    run_training_pipeline(epochs=25, batch_size=32, learning_rate=3e-4)
