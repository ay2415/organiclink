"""
YOLOv8 Produce Detection Engine for OrganicLink Phase 1.

Loads pretrained yolov8n.pt model to detect individual fruit/vegetable items
in bulk/tray images and generates a debug annotated image.
"""

import os
import cv2
from ultralytics import YOLO

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEBUG_IMAGE_PATH = os.path.join(BASE_DIR, "debug_detection.jpg")

# COCO dataset produce-relevant class names and IDs
# 46: banana, 47: apple, 49: orange, 50: broccoli, 51: carrot
PRODUCE_COCO_CLASSES = {
    46: "banana",
    47: "apple",
    49: "orange",
    50: "broccoli",
    51: "carrot",
}

_yolo_model = None

def get_yolo_model():
    global _yolo_model
    if _yolo_model is None:
        model_path = os.path.join(BASE_DIR, "yolov8n.pt")
        # Load pretrained yolov8n.pt (will download automatically if not cached)
        _yolo_model = YOLO("yolov8n.pt")
    return _yolo_model


def detect_items(image_path: str, conf_threshold: float = 0.25) -> list:
    """
    Runs YOLOv8 detection on the image.
    Filters to fruit/produce-relevant classes or high-confidence objects if produce.
    Returns list of dicts:
      [
        {
          "bbox": [x1, y1, x2, y2],
          "confidence": float,
          "class_name": str
        },
        ...
      ]
    Saves debug image with boxes to backend/cv/debug_detection.jpg.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at {image_path}")

    model = get_yolo_model()
    results = model(image_path, conf=conf_threshold, verbose=False)[0]

    img_bgr = cv2.imread(image_path)
    detections = []

    for box in results.boxes:
        cls_id = int(box.cls[0].item())
        conf = float(box.conf[0].item())
        x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]

        # Check if detected class is in produce COCO classes, or filter
        class_name = results.names.get(cls_id, f"cls_{cls_id}")
        
        # We accept COCO produce classes, or general fruits if detected as produce
        is_produce = cls_id in PRODUCE_COCO_CLASSES or class_name.lower() in [
            "apple", "banana", "orange", "broccoli", "carrot", "fruit", "food"
        ]

        if is_produce or conf > 0.35:  # also catch fruits detected under close confidence
            det_item = {
                "bbox": [x1, y1, x2, y2],
                "confidence": round(conf, 4),
                "class_name": class_name,
            }
            detections.append(det_item)

            # Draw bounding box on debug image
            label = f"{class_name} {conf:.2f}"
            cv2.rectangle(img_bgr, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                img_bgr, label, (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2
            )

    # Save debug image
    cv2.imwrite(DEBUG_IMAGE_PATH, img_bgr)
    print(f"[YOLO Detection] Detected {len(detections)} items. Saved debug image to {DEBUG_IMAGE_PATH}")

    return detections
