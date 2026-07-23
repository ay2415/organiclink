"""
Real-World Dataset Training Script for OrganicLink Computer Vision.
Designed to train directly on Kaggle datasets (e.g., 'Fruit and Vegetable Disease (Healthy vs Rotten)').

Supported Folders:
- Tomato_Healthy / Tomato__Healthy -> (tomato, fresh)
- Tomato_Rotten / Tomato__Rotten -> (tomato, major_defect)
- Apple_Healthy, Potato_Healthy, Carrot_Healthy, etc.
"""

import os
import json
import numpy as np
from PIL import Image
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
import torchvision.transforms as transforms
from torchvision.models import resnet18, ResNet18_Weights

# Define Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODELS_DIR, "quality_model.pt")
REPORT_JSON_PATH = os.path.join(MODELS_DIR, "eval_report.json")

PRODUCT_CLASSES = [
    "onion", "milk", "apple", "potato", "carrot", "cheese", "tomato",
    "banana", "bellpepper", "cucumber", "grape", "guava", "mango", "orange", "strawberry"
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

        # Multi-head outputs
        self.product_head = nn.Linear(in_features, num_products)
        self.defect_head = nn.Linear(in_features, num_defects)

    def forward(self, x):
        features = self.backbone(x)
        prod_logits = self.product_head(features)
        defect_logits = self.defect_head(features)
        return prod_logits, defect_logits


class KaggleProduceDataset(Dataset):
    """
    Scans real images from backend/cv/data/
    Automatically parses Kaggle folder names like:
    - Tomato_Healthy / Tomato__Healthy -> (tomato, fresh)
    - Tomato_Rotten / Tomato__Rotten -> (tomato, major_defect)
    - Apple___fresh, onion___major_defect, etc.
    """
    def __init__(self, root_dir, transform=None):
        self.root_dir = root_dir
        self.transform = transform
        self.samples = []

        if not os.path.exists(root_dir):
            return

        for root, dirs, files in os.walk(root_dir):
            for fname in files:
                if fname.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    full_path = os.path.join(root, fname)
                    folder_name = os.path.basename(root).lower()

                    prod_label = None
                    def_label = None

                    # Parse folder name like "tomato_healthy" or "apple__rotten"
                    clean_folder = folder_name.replace("__", "_")
                    
                    # 1. Product mapping
                    for i, p in enumerate(PRODUCT_CLASSES):
                        if p in clean_folder or p in fname.lower():
                            prod_label = i
                            break

                    # 2. Defect mapping (Healthy -> fresh, Rotten -> major_defect)
                    if "healthy" in clean_folder or "fresh" in clean_folder:
                        def_label = DEFECT_CLASSES.index("fresh")
                    elif "rotten" in clean_folder or "major" in clean_folder:
                        def_label = DEFECT_CLASSES.index("major_defect")
                    elif "minor" in clean_folder or "defect" in clean_folder:
                        def_label = DEFECT_CLASSES.index("minor_defect")
                    else:
                        def_label = DEFECT_CLASSES.index("fresh")

                    # If product is matched, record sample
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


def train_model():
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)

    dataset_all = KaggleProduceDataset(DATA_DIR)
    if len(dataset_all) == 0:
        print("\n" + "="*75)
        print("ERROR: NO REAL KAGGLE IMAGES FOUND IN `backend/cv/data/`")
        print("Please extract your Kaggle ZIP into `backend/cv/data/`!")
        print("Expected folders inside `backend/cv/data/`:")
        print("  - Tomato_Healthy")
        print("  - Tomato_Rotten")
        print("  - Onion_Healthy (or Onion___fresh)")
        print("  - Potato_Healthy / Potato_Rotten")
        print("="*75 + "\n")
        return None

    print(f"\nSuccessfully loaded {len(dataset_all)} REAL Kaggle images from {DATA_DIR}!\n")

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

    train_loader = DataLoader(train_ds, batch_size=min(32, train_size), shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=min(32, val_size), shuffle=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = MultiHeadProduceModel().to(device)

    criterion_prod = nn.CrossEntropyLoss()
    criterion_def = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)

    epochs = 6
    print(f"Training Multi-Head ResNet18 model on Kaggle Dataset for {epochs} epochs...")
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

        epoch_loss = running_loss / total
        prod_acc = prod_correct / total
        def_acc = def_correct / total
        print(f"Epoch {epoch+1}/{epochs} - Loss: {epoch_loss:.4f} | Product Acc: {prod_acc*100:.1f}% | Quality Acc: {def_acc*100:.1f}%")

    torch.save(model.state_dict(), MODEL_PATH)
    print(f"\nReal-World Neural Network Model saved to {MODEL_PATH}")

    report = {
        "architecture": "MultiHeadProduceModel (ResNet18)",
        "dataset_type": "Kaggle Fruit and Vegetable Diseases Dataset",
        "total_samples": len(dataset_all),
        "train_samples": train_size,
        "val_samples": val_size
    }

    with open(REPORT_JSON_PATH, "w") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    train_model()
