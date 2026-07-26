"""
FIXED Inference Engine for OrganicLink produce quality + product verification.

Fixes applied vs the previous version:
  1. THE BIG ONE - quality_score is now driven by the neural network's defect
     head. Previously the score was 100% OpenCV heuristics and the classifier
     output was computed but never used, which is why good apples scored 30
     and rotten apples scored 65.
  2. defect_coverage_percent REMOVED from the score. On glossy produce,
     specular highlights and shadows read as "defects" while uniformly brown
     rotten fruit reads as "clean" - it inverted the result. It is still
     computed and DISPLAYED as a diagnostic, but no longer scored.
  3. Inference transform now matches the training val_transform exactly
     (Resize((224,224)) - not the ImageNet Resize(256)+CenterCrop(224)).
  4. Mismatch detection tightened: top-1 with a confidence margin instead of
     a permissive top-3 with a 35% floor.
  5. Products with no training data are rejected up front rather than
     silently mispredicted (this is why onion returned "pomegranate").
  6. compute_quality_score from grading.py is now actually used.
"""

import os
import cv2
import numpy as np
from PIL import Image
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision.models import resnet18

from cv.grading import compute_quality_score, score_to_grade

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models_backup", "quality_model.pt")
MODEL_VERSION = "resnet18-multihead-v3"

# MUST match train.py exactly.
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

PRODUCT_CLASSES = PRODUCT_CLASSES_15
DEFECT_CLASSES = ["fresh", "minor_defect", "major_defect"]

# Products the platform sells but the CV model cannot grade.
# Onion is here because no onion images exist in the training data - the model
# would otherwise confidently return "pomegranate". Milk is here because milk
# quality (bacterial count, somatic cells, fat) is not visually determinable.
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
    "mango": ["mango"],
    "orange": ["orange", "tangerine", "citrus", "mandarin"],
    "pomegranate": ["pomegranate"],
    "potato": ["potato", "sweet potato"],
    "strawberry": ["strawberry", "strawberries"],
    "tomato": ["tomato", "cherry tomato", "plum tomato", "tomatoes"],
}

# Tunables
MIN_CONFIDENCE_TO_ACCEPT = 45.0   # below this, ask for a better photo
MISMATCH_MARGIN = 15.0            # predicted must beat expected by this to reject


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

            # EXACTLY the val_transform used in train.py.
            inst.transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                     std=[0.229, 0.224, 0.225]),
            ])
            inst.load_model()
        return cls._instance

    def load_model(self):
        candidate_paths = [
            os.path.join(BASE_DIR, "models_backup", "quality_model.pt"),
            os.path.join(BASE_DIR, "models", "quality_model.pt"),
            os.path.join(BASE_DIR, "models", "grading_model.pt"),
        ]
        chosen_path = None
        for p in candidate_paths:
            if os.path.exists(p):
                chosen_path = p
                break

        if not chosen_path:
            print(f"[CV] No trained model found. Grading is DISABLED.")
            self.model = None
            self.model_available = False
            return

        try:
            state_dict = torch.load(chosen_path, map_location=self.device)
            has_sub_index = 'product_head.1.weight' in state_dict
            num_prods = state_dict['product_head.1.weight'].shape[0] if has_sub_index else state_dict['product_head.weight'].shape[0]
            num_defs = state_dict['defect_head.1.weight'].shape[0] if has_sub_index else state_dict['defect_head.weight'].shape[0]

            self.product_classes = PRODUCT_CLASSES_15 if num_prods == 15 else PRODUCT_CLASSES_16
            model = MultiHeadProduceModel(num_products=num_prods, num_defects=num_defs)

            if has_sub_index:
                model.product_head = torch.nn.Sequential(torch.nn.Dropout(0.2), torch.nn.Linear(512, num_prods))
                model.defect_head = torch.nn.Sequential(torch.nn.Dropout(0.3), torch.nn.Linear(512, num_defs))
            else:
                model.product_head = torch.nn.Linear(512, num_prods)
                model.defect_head = torch.nn.Linear(512, num_defs)

            model.load_state_dict(state_dict)
            model.to(self.device)
            model.eval()
            self.model = model
            self.model_available = True
            self.last_mtime = os.path.getmtime(chosen_path)
            print(f"[CV] Successfully loaded model from {os.path.basename(chosen_path)} ({num_prods} classes) on {self.device}.")
        except Exception as e:
            print(f"[CV] FAILED to load model from {os.path.basename(chosen_path)}: {e}. Grading is DISABLED.")
            self.model = None
            self.model_available = False

    def extract_opencv_metrics(self, image_path: str) -> dict:
        """
        Diagnostic sub-metrics for the UI breakdown panel.
        defect_coverage_percent is DISPLAY ONLY - it is deliberately not scored.
        """
        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            return {"colour_vibrancy": 0.0, "colour_uniformity": 0.0,
                    "brightness": 0.0, "defect_coverage_percent": 0.0}

        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(img_hsv)

        vibrancy = float(np.mean(s) / 2.55)
        brightness = float(np.mean(v) / 2.55)

        # Handle red hue wraparound (red sits at both 0 and 180)
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

    def analyze_image(self, image_path: str, expected_product: str = "unknown") -> dict:
        # Hot-reload if the model file changed
        if os.path.exists(MODEL_PATH) and os.path.getmtime(MODEL_PATH) > self.last_mtime:
            self.load_model()

        expected = expected_product.lower().strip().replace(" ", "_")

        # 1. Product not gradable at all -> honest refusal, never a fake grade
        if expected in CV_UNSUPPORTED_PRODUCTS:
            return {
                "status": "not_gradable",
                "product_mismatch": False,
                "quality_grade": None,
                "quality_score": None,
                "message": CV_UNSUPPORTED_PRODUCTS[expected],
            }

        if expected != "unknown" and expected not in PRODUCT_CLASSES:
            return {
                "status": "not_gradable",
                "product_mismatch": False,
                "quality_grade": None,
                "quality_score": None,
                "message": (f"'{expected_product}' is not supported by the grading "
                            f"model. Supported: {', '.join(PRODUCT_CLASSES)}."),
            }

        if not self.model_available:
            return {
                "status": "unavailable",
                "product_mismatch": False,
                "quality_grade": None,
                "quality_score": None,
                "message": "Grading model not loaded. Train the model first.",
            }

        metrics = self.extract_opencv_metrics(image_path)
        pil_img = Image.open(image_path).convert("RGB")
        input_tensor = self.transform(pil_img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            prod_logits, def_logits = self.model(input_tensor)
            prod_probs = torch.softmax(prod_logits, dim=1).squeeze(0)
            def_probs = torch.softmax(def_logits, dim=1).squeeze(0)

        top_idx = int(torch.argmax(prod_probs).item())
        predicted_product = PRODUCT_CLASSES[top_idx]
        predicted_conf = float(prod_probs[top_idx].item() * 100.0)

        # 2. Low confidence -> ask for a better photo rather than guessing
        if predicted_conf < MIN_CONFIDENCE_TO_ACCEPT:
            return {
                "status": "unclear_image",
                "product_mismatch": False,
                "quality_grade": None,
                "quality_score": None,
                "message": (f"Could not confidently identify the produce "
                            f"({predicted_conf:.0f}% confidence). Retake the photo "
                            f"in good light with the produce filling the frame "
                            f"against a plain background."),
            }

        # 3. Strict mismatch check: top-1, with a margin over the expected class
        if expected != "unknown":
            expected_idx = PRODUCT_CLASSES.index(expected)
            expected_conf = float(prod_probs[expected_idx].item() * 100.0)

            synonyms = PRODUCT_SYNONYMS.get(expected, [expected])
            is_synonym = any(
                predicted_product == s.lower().replace(" ", "_") for s in synonyms
            )

            if (predicted_product != expected
                    and not is_synonym
                    and (predicted_conf - expected_conf) > MISMATCH_MARGIN):
                return {
                    "status": "product_mismatch",
                    "product_mismatch": True,
                    "quality_grade": "R",
                    "quality_score": 0.0,
                    "predicted_label": predicted_product,
                    "neural_confidence": round(predicted_conf, 2),
                    "message": (f"This looks like {predicted_product.replace('_',' ')} "
                                f"({predicted_conf:.0f}% confidence), but you selected "
                                f"{expected_product}. Please upload a photo of your "
                                f"{expected_product}."),
                }

        # 4. Quality score - NOW DRIVEN BY THE NEURAL NETWORK
        prob_fresh = float(def_probs[0].item())
        prob_minor = float(def_probs[1].item())
        prob_major = float(def_probs[2].item())
        predicted_defect = DEFECT_CLASSES[int(torch.argmax(def_probs).item())]

        quality_score = compute_quality_score(
            prob_fresh=prob_fresh,
            prob_minor=prob_minor,
            prob_major=prob_major,
            colour_vibrancy=metrics["colour_vibrancy"],
            colour_uniformity=metrics["colour_uniformity"],
        )
        grade = score_to_grade(quality_score)

        # Descriptive defect labels for the UI (informational only)
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
            "status": "graded",
            "product_mismatch": False,
            "predicted_label": predicted_product,
            "neural_confidence": round(predicted_conf, 2),
            "predicted_condition": predicted_defect,
            "quality_grade": grade,
            "quality_score": quality_score,
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
                # Diagnostic only - NOT used in the score. On glossy produce this
                # measures reflections as much as blemishes.
                "defect_coverage_percent_diagnostic": metrics["defect_coverage_percent"],
                "detected_defects": defects,
            },
        }


def get_inference_engine():
    return GradingInferenceEngine()