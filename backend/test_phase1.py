"""
Test runner for Phase 1 YOLOv8 Detection on produce images.
"""
import os
import sys
from cv.detection import detect_items, DEBUG_IMAGE_PATH

# Find sample images in uploads
uploads_dir = os.path.join(os.path.dirname(__file__), "..", "backend", "uploads")
sample_files = [f for f in os.listdir(uploads_dir) if f.endswith(('.jpg', '.jpeg', '.png', '.webp'))]

if not sample_files:
    print("No images found in uploads folder.")
    sys.exit(1)

test_image_path = os.path.join(uploads_dir, sample_files[0])
print(f"Testing detection on: {test_image_path}")

detections = detect_items(test_image_path)

print(f"\n--- PHASE 1 DETECTION RESULTS ---")
print(f"Total Items Detected: {len(detections)}")
for idx, det in enumerate(detections, 1):
    print(f"Item #{idx}: Class='{det['class_name']}', Confidence={det['confidence']*100:.1f}%, BBox={det['bbox']}")

print(f"\nDebug Image Saved To: {DEBUG_IMAGE_PATH}")
