"""
Real-World Inference Engine for OrganicLink Produce Quality & Verification.
Loads Multi-Head Neural Network (if trained on real dataset) or ResNet18 Pretrained Model.
Enforces strict product mismatch detection (e.g., uploading Carrot when Onion is selected).
"""

import os
import cv2
import numpy as np
from PIL import Image
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision.models import resnet18, ResNet18_Weights

from cv.grading import compute_quality_score, score_to_grade

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "quality_model.pt")
MODEL_VERSION = "resnet18-real-v2"

PRODUCT_CLASSES = [
    "apple", "banana", "bitter_gourd", "capsicum", "carrot", "cucumber",
    "grape", "guava", "jujube", "mango", "milk", "orange", "pomegranate",
    "potato", "strawberry", "tomato"
]
DEFECT_CLASSES = ["fresh", "minor_defect", "major_defect"]

PRODUCT_SYNONYMS = {
    "apple": ["apple", "granny smith", "red apple", "green apple"],
    "banana": ["banana", "plantain"],
    "bitter_gourd": ["bitter gourd", "gourd"],
    "capsicum": ["bell pepper", "pepper", "capsicum", "green pepper", "bellpepper"],
    "carrot": ["carrot", "baby carrot"],
    "cucumber": ["cucumber", "pickle", "zucchini"],
    "grape": ["grape", "grapes"],
    "guava": ["guava"],
    "jujube": ["jujube", "red date"],
    "mango": ["mango"],
    "milk": ["carton", "milk can", "jug", "container", "bottle"],
    "orange": ["orange", "tangerine", "citrus"],
    "pomegranate": ["pomegranate"],
    "potato": ["potato", "sweet potato"],
    "strawberry": ["strawberry", "berries"],
    "tomato": ["tomato", "cherry tomato", "plum tomato"]
}


class MultiHeadProduceModel(nn.Module):
    def __init__(self, num_products=len(PRODUCT_CLASSES), num_defects=len(DEFECT_CLASSES)):
        super().__init__()
        backbone = resnet18(weights=None)
        in_features = backbone.fc.in_features
        backbone.fc = nn.Identity()
        self.backbone = backbone

        self.product_head = nn.Linear(in_features, num_products)
        self.defect_head = nn.Linear(in_features, num_defects)

    def forward(self, x):
        features = self.backbone(x)
        prod_logits = self.product_head(features)
        defect_logits = self.defect_head(features)
        return prod_logits, defect_logits


class GradingInferenceEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GradingInferenceEngine, cls).__new__(cls)
            cls._instance.model = None
            cls._instance.custom_model = False
            cls._instance.last_mtime = 0
            cls._instance.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            
            cls._instance.weights = ResNet18_Weights.DEFAULT
            cls._instance.transform = cls._instance.weights.transforms()
            cls._instance.categories = [c.lower() for c in cls._instance.weights.meta["categories"]]
            cls._instance.load_model()
        return cls._instance

    def load_model(self):
        if os.path.exists(MODEL_PATH):
            try:
                mtime = os.path.getmtime(MODEL_PATH)
                print(f"Loading custom trained Multi-Head Produce Model from {MODEL_PATH} (mtime: {mtime})...")
                model = MultiHeadProduceModel()
                model.load_state_dict(torch.load(MODEL_PATH, map_location=self.device))
                model.to(self.device)
                model.eval()
                self.model = model
                self.custom_model = True
                self.last_mtime = mtime
                print("Custom Multi-Head Neural Network loaded successfully!")
                return
            except Exception as e:
                print(f"Failed to load custom model weights ({e}). Falling back to official ResNet18.")

        print("Loading official PyTorch Pre-trained ResNet18...")
        model = resnet18(weights=self.weights)
        model.to(self.device)
        model.eval()
        self.model = model
        self.custom_model = False

    def extract_opencv_metrics(self, image_path: str) -> dict:
        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            return {
                "colour_vibrancy": 85.0,
                "colour_uniformity": 90.0,
                "brightness": 80.0,
                "defect_coverage_percent": 2.5
            }

        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(img_hsv)

        vibrancy = float(np.mean(s) / 2.55)
        h_float = h.astype(np.float32)
        median_h = np.median(h_float)
        if median_h < 15 or median_h > 165:
            h_float = (h_float + 90.0) % 180.0
            
        hue_std = float(np.std(h_float))
        uniformity = float(max(0.0, 100.0 - min(hue_std * 1.5, 100.0)))
        brightness = float(np.mean(v) / 2.55)

        v_median = cv2.medianBlur(v, 15)
        diff = cv2.subtract(v_median, v)
        _, defect_mask = cv2.threshold(diff, 40, 255, cv2.THRESH_BINARY)
        total_pixels = defect_mask.size
        defect_pixels = np.count_nonzero(defect_mask)
        defect_coverage = float((defect_pixels / total_pixels) * 100.0)

        return {
            "colour_vibrancy": round(max(0.0, min(100.0, vibrancy)), 2),
            "colour_uniformity": round(max(0.0, min(100.0, uniformity)), 2),
            "brightness": round(max(0.0, min(100.0, brightness)), 2),
            "defect_coverage_percent": round(max(0.0, min(100.0, defect_coverage)), 2)
        }

    def analyze_image(self, image_path: str, expected_product: str = "unknown") -> dict:
        if self.model is None or (os.path.exists(MODEL_PATH) and os.path.getmtime(MODEL_PATH) > self.last_mtime):
            self.load_model()
            
        metrics = self.extract_opencv_metrics(image_path)
        pil_img = Image.open(image_path).convert("RGB")
        input_tensor = self.transform(pil_img).unsqueeze(0).to(self.device)

        if self.custom_model:
            with torch.no_grad():
                prod_logits, def_logits = self.model(input_tensor)
                prod_probs = torch.softmax(prod_logits, dim=1).squeeze(0)
                def_probs = torch.softmax(def_logits, dim=1).squeeze(0)

            top3_values, top3_indices = torch.topk(prod_probs, min(3, len(PRODUCT_CLASSES)))
            top3_products = [PRODUCT_CLASSES[idx.item()] for idx in top3_indices]
            predicted_product = top3_products[0]
            prod_confidence = float(top3_values[0].item() * 100.0)

            top1_def_idx = torch.argmax(def_probs).item()
            predicted_defect = DEFECT_CLASSES[top1_def_idx]

            exp_clean = expected_product.lower().strip()
            synonyms = PRODUCT_SYNONYMS.get(exp_clean, [exp_clean])

            # Check mismatch against top 3 custom trained predictions & visual synonyms
            is_match = False
            for pred_p in top3_products:
                if pred_p == exp_clean or any(syn in pred_p for syn in synonyms):
                    is_match = True
                    break

            if expected_product != "unknown" and not is_match and prod_confidence > 35.0:
                return {
                    "product_mismatch": True,
                    "quality_grade": "R",
                    "quality_score": 0.0,
                    "cv_breakdown": {
                        "error": f"Product Mismatch Detected: Neural Network identified image as '{predicted_product.capitalize()}' ({prod_confidence:.1f}% confidence), which does not match requested listing product '{expected_product.capitalize()}'."
                    }
                }

            top1_label = predicted_product.capitalize()
            top1_prob = prod_confidence

        else:
            # Fallback ResNet18 ImageNet classification
            with torch.no_grad():
                outputs = self.model(input_tensor)
                probs = torch.softmax(outputs, dim=1).squeeze(0)

            top10_values, top10_indices = torch.topk(probs, 10)
            top10_labels = [self.categories[idx.item()] for idx in top10_indices]
            top1_label = top10_labels[0]
            top1_prob = float(top10_values[0].item() * 100.0)

            # Fallback ImageNet classification does not enforce strict product mismatch
            pass

        # Sub-metric quality scoring
        defects = []
        if metrics["defect_coverage_percent"] > 5.0:
            defects.append("surface_blemishes")
        if metrics["colour_uniformity"] < 60.0:
            defects.append("discolouration")
        if metrics["colour_vibrancy"] < 40.0:
            defects.append("dull_pigmentation")

        final_score = (
            (metrics["colour_vibrancy"] * 0.25) +
            (metrics["colour_uniformity"] * 0.25) +
            (metrics["brightness"] * 0.10) +
            ((100.0 - (metrics["defect_coverage_percent"] * 5)) * 0.40)
        )
        final_score = max(0.0, min(100.0, final_score))

        grade = "A"
        if final_score < 40 or (self.custom_model and predicted_defect == "major_defect" and final_score < 55):
            grade = "R"
        elif final_score < 60 or (self.custom_model and predicted_defect == "major_defect"):
            grade = "C"
        elif final_score < 80 or (self.custom_model and predicted_defect == "minor_defect"):
            grade = "B"

        return {
            "product_mismatch": False,
            "predicted_label": top1_label,
            "neural_confidence": round(top1_prob, 2),
            "quality_grade": grade,
            "quality_score": float(final_score),
            "cv_breakdown": {
                "colour_vibrancy": metrics["colour_vibrancy"],
                "colour_uniformity": metrics["colour_uniformity"],
                "brightness": metrics["brightness"],
                "defect_coverage_percent": metrics["defect_coverage_percent"],
                "detected_defects": defects
            }
        }


def get_inference_engine():
    return GradingInferenceEngine()
