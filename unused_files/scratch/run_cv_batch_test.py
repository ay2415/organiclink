"""
OrganicLink Batch Evaluation & Accuracy Verification Script
Run this script to benchmark ResNet-18 Multi-Head & Bulk Grading on any image directory.
"""

import os
import sys
import json
import time
from collections import Counter

sys.path.append('backend')
from cv.inference import get_inference_engine
from cv.bulk_grading import grade_bulk

def benchmark_dataset(data_dir=None):
    engine = get_inference_engine()
    print("=" * 65)
    print(" ORGANICLINK MODEL ACCURACY BENCHMARK & EVALUATION TOOL")
    print("=" * 65)
    print(f"Active Checkpoint: backend/cv/models/grading_model.pt")
    
    # Read existing evaluation report if available
    eval_txt_path = os.path.join("backend", "cv", "models", "eval_report.txt")
    if os.path.exists(eval_txt_path):
        print(f"\n[FOUND EMPIRICAL TRAINED EVALUATION REPORT]: {eval_txt_path}")
        with open(eval_txt_path, "r") as f:
            lines = f.readlines()
        print("".join(lines[:35])) # Print top summary
    
    print("\n" + "=" * 65)
    print(" LIVE TEST RUNNER ON CUSTOM IMAGES")
    print("=" * 65)

    test_samples = [
        ("scratch/latest_media.jpg", "tomato", "Bulk Basket of Tomatoes"),
    ]

    for img_path, expected, desc in test_samples:
        if not os.path.exists(img_path):
            continue
        print(f"\nTesting Sample: {desc} ({img_path})")
        print(f"Expected Product: {expected}")
        
        # 1. Single-item Inference
        t0 = time.time()
        single_res = engine.analyze_image(img_path, expected_product=expected)
        t_single = (time.time() - t0) * 1000
        print(f" -> Single-Item Result: Pred Product='{single_res.get('predicted_label')}', Conf={single_res.get('neural_confidence')}%, Quality Score={single_res.get('quality_score')}, Grade={single_res.get('quality_grade')} ({t_single:.1f}ms)")
        
        # 2. Bulk-item Inference
        t0 = time.time()
        bulk_res = grade_bulk(img_path, expected_product=expected)
        t_bulk = (time.time() - t0) * 1000
        print(f" -> Bulk-Item Result: Status='{bulk_res.get('status')}', Items Detected={bulk_res.get('total_items_detected', 1)}, Fresh Count={bulk_res.get('fresh_count', 0)}, Defect Coverage={bulk_res.get('defect_percent', 0.0)}%, Batch Grade={bulk_res.get('batch_grade', bulk_res.get('quality_grade'))} ({t_bulk:.1f}ms)")

if __name__ == "__main__":
    benchmark_dataset()
