"""
Training script for OrganicLink produce quality computer vision classifier.
Uses transfer learning on EfficientNet-B0 (or ResNet18 backbone) PyTorch model.
Generates synthetic bootstrap dataset if real dataset is absent.
Saves model weights to backend/cv/models/quality_model.pt and evaluation report.
"""

import os
import json
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
import torchvision.transforms as transforms
from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights, resnet18, ResNet18_Weights

# Define Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODELS_DIR, "quality_model.pt")
REPORT_JSON_PATH = os.path.join(MODELS_DIR, "eval_report.json")
REPORT_TXT_PATH = os.path.join(MODELS_DIR, "eval_report.txt")

CLASSES = ["fresh", "minor_defect", "major_defect"]


def generate_synthetic_dataset(num_per_class_train=300, num_per_class_val=60):
    """
    Generates synthetic produce images with varying defect spots for bootstrap training.
    """
    print("Generating synthetic bootstrap produce dataset...")
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Produce colors (apples/onions/tomatoes/potatoes)
    base_colors = [
        (220, 50, 40),   # Red apple/tomato
        (70, 160, 50),   # Green apple
        (220, 170, 70),  # Onion yellow
        (190, 140, 90),  # Potato brown
    ]

    splits = {
        "train": num_per_class_train,
        "val": num_per_class_val
    }

    for split, count in splits.items():
        for cls in CLASSES:
            cls_dir = os.path.join(DATA_DIR, split, cls)
            os.makedirs(cls_dir, exist_ok=True)

            for i in range(count):
                # Create base produce image
                img_size = 224
                img = Image.new("RGB", (img_size, img_size), (240, 240, 240))
                draw = ImageDraw.Draw(img)

                # Draw produce oval blob
                color = random.choice(base_colors)
                # Randomize color slightly
                r = max(0, min(255, color[0] + random.randint(-20, 20)))
                g = max(0, min(255, color[1] + random.randint(-20, 20)))
                b = max(0, min(255, color[2] + random.randint(-20, 20)))
                
                margin = random.randint(15, 30)
                ellipse_box = [margin, margin, img_size - margin, img_size - margin]
                draw.ellipse(ellipse_box, fill=(r, g, b))

                # Add defect spots depending on class
                if cls == "fresh":
                    num_spots = 0
                elif cls == "minor_defect":
                    num_spots = random.randint(1, 4)
                else:  # major_defect
                    num_spots = random.randint(6, 15)

                for _ in range(num_spots):
                    spot_x = random.randint(margin + 20, img_size - margin - 20)
                    spot_y = random.randint(margin + 20, img_size - margin - 20)
                    if cls == "minor_defect":
                        spot_r = random.randint(3, 8)
                    else:
                        spot_r = random.randint(10, 25)
                    
                    spot_color = (
                        max(0, r - random.randint(80, 150)),
                        max(0, g - random.randint(80, 150)),
                        max(0, b - random.randint(80, 150))
                    )
                    draw.ellipse(
                        [spot_x - spot_r, spot_y - spot_r, spot_x + spot_r, spot_y + spot_r],
                        fill=spot_color
                    )

                # Apply slight blur filter
                img = img.filter(ImageFilter.GaussianBlur(radius=0.8))

                img_path = os.path.join(cls_dir, f"{cls}_{i:04d}.png")
                img.save(img_path)

    print(f"Synthetic dataset generated successfully at {DATA_DIR}")


class SyntheticProduceDataset(Dataset):
    def __init__(self, root_dir, transform=None):
        self.root_dir = root_dir
        self.transform = transform
        self.samples = []
        for class_idx, class_name in enumerate(CLASSES):
            class_dir = os.path.join(root_dir, class_name)
            if not os.path.exists(class_dir):
                continue
            for fname in os.listdir(class_dir):
                if fname.endswith((".png", ".jpg", ".jpeg")):
                    self.samples.append((os.path.join(class_dir, fname), class_idx))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        image = Image.open(path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, label


def train_model():
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    # Generate synthetic dataset if not exists
    train_dir = os.path.join(DATA_DIR, "train")
    if not os.path.exists(train_dir) or len(os.listdir(train_dir)) == 0:
        generate_synthetic_dataset()

    # Transforms
    train_transform = transforms.Compose([
        transforms.RandomResizedCrop(224),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(20),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    train_dataset = SyntheticProduceDataset(os.path.join(DATA_DIR, "train"), transform=train_transform)
    val_dataset = SyntheticProduceDataset(os.path.join(DATA_DIR, "val"), transform=val_transform)

    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)

    print(f"Dataset loaded: {len(train_dataset)} train images, {len(val_dataset)} val images.")

    # Initialize model: EfficientNet-B0 with fallback to ResNet18
    try:
        model = efficientnet_b0(weights=EfficientNet_B0_Weights.DEFAULT)
        in_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(in_features, len(CLASSES))
        print("Initialized EfficientNet-B0 backbone.")
    except Exception as e:
        print(f"EfficientNet-B0 initialization fallback: {e}")
        model = resnet18(weights=ResNet18_Weights.DEFAULT)
        in_features = model.fc.in_features
        model.fc = nn.Linear(in_features, len(CLASSES))
        print("Initialized ResNet18 backbone.")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=1e-3)

    epochs = 5
    print(f"Training for {epochs} epochs on {device}...")
    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            _, preds = torch.max(outputs, 1)
            correct += torch.sum(preds == labels.data).item()
            total += labels.size(0)

        epoch_loss = running_loss / total
        epoch_acc = correct / total
        print(f"Epoch {epoch+1}/{epochs} - Loss: {epoch_loss:.4f} - Acc: {epoch_acc:.4f}")

    # Evaluation on Validation set
    model.eval()
    all_preds = []
    all_targets = []

    with torch.no_grad():
        for images, labels in val_loader:
            images = images.to(device)
            outputs = model(images)
            _, preds = torch.max(outputs, 1)
            all_preds.extend(preds.cpu().numpy())
            all_targets.extend(labels.numpy())

    all_preds = np.array(all_preds)
    all_targets = np.array(all_targets)

    accuracy = float(np.mean(all_preds == all_targets))
    
    # Calculate confusion matrix & per-class metrics
    cm = np.zeros((len(CLASSES), len(CLASSES)), dtype=int)
    for t, p in zip(all_targets, all_preds):
        cm[t, p] += 1

    class_metrics = {}
    for i, cls_name in enumerate(CLASSES):
        tp = cm[i, i]
        fp = np.sum(cm[:, i]) - tp
        fn = np.sum(cm[i, :]) - tp
        
        precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        class_metrics[cls_name] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "support": int(np.sum(cm[i, :]))
        }

    report = {
        "architecture": "EfficientNet-B0",
        "dataset": "Synthetic Bootstrap Produce Quality Dataset",
        "num_train_samples": len(train_dataset),
        "num_val_samples": len(val_dataset),
        "overall_accuracy": round(accuracy, 4),
        "class_metrics": class_metrics,
        "confusion_matrix": cm.tolist()
    }

    # Save model checkpoint
    torch.save(model.state_dict(), MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")

    # Save JSON report
    with open(REPORT_JSON_PATH, "w") as f:
        json.dump(report, f, indent=2)

    # Save TXT report
    with open(REPORT_TXT_PATH, "w") as f:
        f.write("=== ORGANICLINK CV MODEL EVALUATION REPORT ===\n")
        f.write(f"Architecture: {report['architecture']}\n")
        f.write(f"Dataset: {report['dataset']}\n")
        f.write(f"Overall Accuracy: {report['overall_accuracy'] * 100:.2f}%\n\n")
        f.write("Per-Class Performance Metrics:\n")
        for cls_name, metrics in class_metrics.items():
            f.write(f" - {cls_name.upper()}:\n")
            f.write(f"     Precision: {metrics['precision']:.4f}\n")
            f.write(f"     Recall:    {metrics['recall']:.4f}\n")
            f.write(f"     F1 Score:  {metrics['f1_score']:.4f}\n")
            f.write(f"     Support:   {metrics['support']}\n")
        f.write("\nConfusion Matrix (Rows: Actual, Cols: Predicted):\n")
        f.write(f"Classes: {CLASSES}\n")
        for row in cm:
            f.write(f"  {row.tolist()}\n")

    print(f"Evaluation report saved to {REPORT_TXT_PATH}")
    return report


if __name__ == "__main__":
    train_model()
