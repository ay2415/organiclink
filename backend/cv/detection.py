"""
Fine-Tuned YOLOv8 Produce Detection Engine for OrganicLink.

Runs detection using the fine-tuned produce detector model (cv/models/produce_detector.pt).
Returns bounding boxes, class labels, and confidence scores.
"""

import os
import cv2
from ultralytics import YOLO

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEBUG_DIR = os.path.join(BASE_DIR, "debug")
os.makedirs(DEBUG_DIR, exist_ok=True)
DEBUG_IMAGE_PATH = os.path.join(DEBUG_DIR, "detection_debug.jpg")

PRODUCE_MODEL_PATH = os.path.join(BASE_DIR, "models", "produce_detector.pt")
COCO_MODEL_PATH = "yolov8n.pt"

_yolo_model = None

def get_detector_model():
    global _yolo_model
    if _yolo_model is None:
        if os.path.exists(PRODUCE_MODEL_PATH):
            print(f"[Detector] Loading fine-tuned produce detector from {PRODUCE_MODEL_PATH}")
            _yolo_model = YOLO(PRODUCE_MODEL_PATH)
        else:
            print(f"[Detector] Produce model not found at {PRODUCE_MODEL_PATH}, falling back to yolov8n.pt")
            _yolo_model = YOLO(COCO_MODEL_PATH)
    return _yolo_model


def detect_items(image_path: str, conf_threshold: float = 0.20) -> list:
    """
    Runs YOLOv8 produce detection on an image.
    Returns list of dicts:
      [
        {
          "bbox": [x1, y1, x2, y2],
          "confidence": float,
          "class_name": str
        },
        ...
      ]
    Saves debug visualization to backend/cv/debug/detection_debug.jpg.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at: {image_path}")

    model = get_detector_model()
    results = model(image_path, conf=conf_threshold, verbose=False)[0]

    img_bgr = cv2.imread(image_path)
    detections = []

    for box in results.boxes:
        cls_id = int(box.cls[0].item())
        conf = float(box.conf[0].item())
        x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
        class_name = results.names.get(cls_id, f"cls_{cls_id}")

        det_item = {
            "bbox": [x1, y1, x2, y2],
            "confidence": round(conf, 4),
            "class_name": class_name,
        }
        detections.append(det_item)

        # Draw bounding box and label on debug image
        label = f"{class_name} {conf:.2f}"
        cv2.rectangle(img_bgr, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            img_bgr, label, (x1, max(y1 - 8, 20)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2
        )

    # Save debug annotated image
    cv2.imwrite(DEBUG_IMAGE_PATH, img_bgr)
    print(f"[Detector] Detected {len(detections)} items. Saved debug output to: {DEBUG_IMAGE_PATH}")

    return detections
