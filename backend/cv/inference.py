"""
# CV Inference Engine for OrganicLink Produce Quality & Product Classification
# Restored proven high-accuracy quality model weights..

=====================================================================
  MODEL TOGGLE - change ONE line to switch models:

      USE_NEW_MODEL = True   -> grading_model.pt (16 classes, incl. lime)
      USE_NEW_MODEL = False  -> quality_model.pt (15 classes, original)

  To go back to the original working model, set it to False and restart.
  Nothing else needs to change.
=====================================================================
"""

import os
import cv2
import numpy as np
from PIL import Image
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision.models import resnet18

from cv.grading import compute_quality_score, score_to_grade, calibrate_probabilities

# ============================ MODEL TOGGLE ============================
# Set MODEL_CHOICE to switch models with a single word change:
#   "grading_model"  -> Uses models/grading_model.pt (16 produce classes, including lime)
#   "quality_model"  -> Uses models_backup/quality_model.pt (15 produce classes, original)
MODEL_CHOICE = "grading_model"
# ======================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PRODUCT_CLASSES_15 = [
    "apple", "banana", "bitter_gourd", "capsicum", "carrot", "cucumber",
    "grape", "guava", "jujube", "mango", "orange", "pomegranate",
    "potato", "strawberry", "tomato",
]
PRODUCT_CLASSES_16 = [
    "apple", "banana", "bitter_gourd", "capsicum", "carrot", "cucumber",
    "grape", "guava", "jujube", "lime", "mango", "orange", "pomegranate",
    "potato", "strawberry", "tomato",
]

if MODEL_CHOICE == "quality_model":
    MODEL_PATH = os.path.join(BASE_DIR, "models_backup", "quality_model.pt")
    if not os.path.exists(MODEL_PATH):
        MODEL_PATH = os.path.join(BASE_DIR, "models", "quality_model.pt")
    PRODUCT_CLASSES = PRODUCT_CLASSES_15
    MODEL_VERSION = "resnet18-multihead-v3-15class"
else:
    MODEL_PATH = os.path.join(BASE_DIR, "models", "grading_model.pt")
    PRODUCT_CLASSES = PRODUCT_CLASSES_16
    MODEL_VERSION = "resnet18-multihead-v6-16class"

DEFECT_CLASSES = ["fresh", "minor_defect", "major_defect"]

CV_UNSUPPORTED_PRODUCTS = {
    "onion": "No onion training data available - visual grading unavailable.",
    "milk": "Milk quality cannot be assessed visually.",
    "leek": "No training data available for this product.",
    "cabbage": "No training data available for this product.",
    "lettuce": "No training data available for this product.",
    "broccoli": "No training data available for this product.",
}

PRODUCT_SYNONYMS = {
    "apple": ["apple", "granny smith", "red apple", "green apple"],
    "banana": ["banana", "plantain"],
    "bitter_gourd": ["bitter gourd", "bittergourd", "karela"],
    "capsicum": ["bell pepper", "bellpepper", "pepper", "capsicum"],
    "carrot": ["carrot", "baby carrot"],
    "cucumber": ["cucumber", "courgette", "zucchini"],
    "grape": ["grape", "grapes"],
    "guava": ["guava"],
    "jujube": ["jujube", "red date"],
    "lime": ["lime", "limes", "lemon", "lemons"],
    "mango": ["mango"],
    "orange": ["orange", "tangerine", "citrus", "mandarin"],
    "pomegranate": ["pomegranate"],
    "potato": ["potato", "sweet potato"],
    "strawberry": ["strawberry", "strawberries"],
    "tomato": ["tomato", "cherry tomato", "plum tomato", "tomatoes"],
}

MIN_CONFIDENCE_TO_ACCEPT = 45.0
MISMATCH_MARGIN = 15.0


class MultiHeadProduceModel(nn.Module):
    """Matches BOTH models: dropout in heads (new) is harmless when loading old
    weights because Sequential(Dropout, Linear) still keys the Linear at .1."""
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
        return self.product_head(features), self.defect_head(features)


class MultiHeadProduceModelDropout(nn.Module):
    """Head layout used by the NEW model (train.py v6 with Dropout)."""
    def __init__(self, num_products, num_defects):
        super().__init__()
        backbone = resnet18(weights=None)
        in_features = backbone.fc.in_features
        backbone.fc = nn.Identity()
        self.backbone = backbone
        self.product_head = nn.Sequential(nn.Dropout(0.2), nn.Linear(in_features, num_products))
        self.defect_head = nn.Sequential(nn.Dropout(0.3), nn.Linear(in_features, num_defects))

    def forward(self, x):
        features = self.backbone(x)
        return self.product_head(features), self.defect_head(features)


class GradingInferenceEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            inst = cls._instance
            inst.model = None
            inst.model_available = False
            inst.last_mtime = 0
            inst.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            inst.transform = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                     std=[0.229, 0.224, 0.225]),
            ])
            inst.load_model()
        return cls._instance

    def load_model(self):
        if not os.path.exists(MODEL_PATH):
            print(f"[CV] No model at {MODEL_PATH}. Grading DISABLED.")
            if not getattr(self, 'model', None):
                self.model = None
                self.model_available = False
            return

        try:
            state = torch.load(MODEL_PATH, map_location=self.device)
        except Exception as e:
            print(f"[CV] Warning: Failed to read checkpoint {MODEL_PATH} ({e}). Retaining active model.")
            return

        if "product_head.weight" in state:
            n_prod = state["product_head.weight"].shape[0]
        elif "product_head.1.weight" in state:
            n_prod = state["product_head.1.weight"].shape[0]
        else:
            raise RuntimeError("Cannot find product head weight in checkpoint")

        if n_prod == 15:
            self.product_classes = PRODUCT_CLASSES_15
        elif n_prod == 16:
            self.product_classes = PRODUCT_CLASSES_16
        else:
            raise RuntimeError(f"Unexpected product head size: {n_prod}")

        n_def = len(DEFECT_CLASSES)

        # Try both head layouts - whichever matches the saved weights loads.
        for ModelClass in (MultiHeadProduceModelDropout, MultiHeadProduceModel):
            try:
                model = ModelClass(n_prod, n_def)
                model.load_state_dict(state)
                model.to(self.device)
                model.eval()
                self.model = model
                self.model_available = True
                self.last_mtime = os.path.getmtime(MODEL_PATH)
                print(f"[CV] Loaded {MODEL_VERSION} from {os.path.basename(MODEL_PATH)} "
                      f"({n_prod} products) using {ModelClass.__name__}.")
                return
            except Exception as e:
                continue

        if not getattr(self, 'model', None):
            print(f"[CV] FAILED to load {MODEL_PATH} with either head layout. "
                  f"Check that PRODUCT_CLASSES count matches the trained model. "
                  f"Grading DISABLED.")
            self.model = None
            self.model_available = False

    def extract_opencv_metrics(self, image_path):
        # Auto-reload model weights if step2_train.py saved a newer checkpoint on disk
        if os.path.exists(MODEL_PATH):
            current_mtime = os.path.getmtime(MODEL_PATH)
            if current_mtime > self.last_mtime:
                print(f"[CV] Auto-reloading newer model checkpoint from {os.path.basename(MODEL_PATH)}...")
                self.load_model()

        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            return {"colour_vibrancy": 0.0, "colour_uniformity": 0.0,
                    "brightness": 0.0, "defect_coverage_percent": 0.0}
        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(img_hsv)
        vibrancy = float(np.mean(s) / 2.55)
        brightness = float(np.mean(v) / 2.55)
        h_float = h.astype(np.float32)
        median_h = np.median(h_float)
        if median_h < 15 or median_h > 165:
            h_float = (h_float + 90.0) % 180.0
        hue_std = float(np.std(h_float))
        uniformity = float(max(0.0, 100.0 - min(hue_std * 1.5, 100.0)))
        v_median = cv2.medianBlur(v, 15)
        diff = cv2.subtract(v_median, v)
        _, defect_mask = cv2.threshold(diff, 40, 255, cv2.THRESH_BINARY)
        defect_coverage = float((np.count_nonzero(defect_mask) / defect_mask.size) * 100.0)
        clamp = lambda x: round(max(0.0, min(100.0, x)), 2)
        return {
            "colour_vibrancy": clamp(vibrancy),
            "colour_uniformity": clamp(uniformity),
            "brightness": clamp(brightness),
            "defect_coverage_percent": clamp(defect_coverage),
        }

    def analyze_image(self, image_path, expected_product="unknown"):
        if os.path.exists(MODEL_PATH) and os.path.getmtime(MODEL_PATH) > self.last_mtime:
            self.load_model()

        expected = expected_product.lower().strip().replace(" ", "_")

        if expected in CV_UNSUPPORTED_PRODUCTS:
            return {"status": "not_gradable", "product_mismatch": False,
                    "quality_grade": None, "quality_score": None,
                    "message": CV_UNSUPPORTED_PRODUCTS[expected]}

        product_classes = getattr(self, 'product_classes', PRODUCT_CLASSES)

        if expected != "unknown" and expected not in product_classes:
            return {"status": "not_gradable", "product_mismatch": False,
                    "quality_grade": None, "quality_score": None,
                    "message": (f"'{expected_product}' is not supported. "
                                f"Supported: {', '.join(product_classes)}.")}

        if not self.model_available:
            return {"status": "unavailable", "product_mismatch": False,
                    "quality_grade": None, "quality_score": None,
                    "message": "Grading model not loaded."}

        metrics = self.extract_opencv_metrics(image_path)
        pil_img = Image.open(image_path).convert("RGB")
        input_tensor = self.transform(pil_img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            prod_logits, def_logits = self.model(input_tensor)
            prod_probs = torch.softmax(prod_logits, dim=1).squeeze(0)
            def_probs = torch.softmax(def_logits, dim=1).squeeze(0)

        top_idx = int(torch.argmax(prod_probs).item())
        predicted_product = product_classes[top_idx]
        predicted_conf = float(prod_probs[top_idx].item() * 100.0)

        if predicted_conf < MIN_CONFIDENCE_TO_ACCEPT:
            return {"status": "unclear_image", "product_mismatch": False,
                    "quality_grade": None, "quality_score": None,
                    "message": (f"Could not confidently identify the produce "
                                f"({predicted_conf:.0f}% confidence). Retake in good "
                                f"light, produce filling the frame, plain background.")}

        if expected != "unknown":
            expected_idx = product_classes.index(expected)
            expected_conf = float(prod_probs[expected_idx].item() * 100.0)
            synonyms = PRODUCT_SYNONYMS.get(expected, [expected])
            is_synonym = any(predicted_product == s.lower().replace(" ", "_") for s in synonyms)

            # Strict Product Mismatch Check: If predicted product is different and confidence > 35%
            if (predicted_product != expected and not is_synonym and predicted_conf >= 35.0):
                return {"status": "product_mismatch", "product_mismatch": True,
                        "quality_grade": "R", "quality_score": 0.0,
                        "predicted_label": predicted_product,
                        "neural_confidence": round(predicted_conf, 2),
                        "message": (f"Product Mismatch Detected: This photo looks like {predicted_product.replace('_',' ').title()} "
                                    f"({predicted_conf:.0f}% confidence), but you selected "
                                    f"{expected_product.title()}. Please upload a photo of {expected_product.title()}.")}

        prob_fresh, prob_minor, prob_major = calibrate_probabilities(
            float(def_probs[0].item()),
            float(def_probs[1].item()),
            float(def_probs[2].item()),
            metrics["colour_uniformity"],
            metrics["defect_coverage_percent"],
        )

        probs_arr = [prob_fresh, prob_minor, prob_major]
        predicted_defect = DEFECT_CLASSES[int(np.argmax(probs_arr))]

        quality_score = compute_quality_score(
            prob_fresh=prob_fresh, prob_minor=prob_minor, prob_major=prob_major,
            colour_vibrancy=metrics["colour_vibrancy"],
            colour_uniformity=metrics["colour_uniformity"],
            defect_coverage_percent=metrics["defect_coverage_percent"],
        )
        grade = score_to_grade(quality_score)

        defects = []
        if predicted_defect == "major_defect":
            defects.append("significant_spoilage")
        elif predicted_defect == "minor_defect":
            defects.append("surface_blemishes")
        if metrics["colour_uniformity"] < 50.0:
            defects.append("discolouration")
        if metrics["colour_vibrancy"] < 30.0:
            defects.append("dull_pigmentation")

        return {
            "status": "graded", "product_mismatch": False,
            "predicted_label": predicted_product,
            "neural_confidence": round(predicted_conf, 2),
            "predicted_condition": predicted_defect,
            "quality_grade": grade, "quality_score": quality_score,
            "model_version": MODEL_VERSION,
            "cv_breakdown": {
                "class_probabilities": {
                    "fresh": round(prob_fresh, 4),
                    "minor_defect": round(prob_minor, 4),
                    "major_defect": round(prob_major, 4),
                },
                "colour_vibrancy": metrics["colour_vibrancy"],
                "colour_uniformity": metrics["colour_uniformity"],
                "brightness": metrics["brightness"],
                "defect_coverage_percent_diagnostic": metrics["defect_coverage_percent"],
                "detected_defects": defects,
            },
        }


def get_inference_engine():
    return GradingInferenceEngine()