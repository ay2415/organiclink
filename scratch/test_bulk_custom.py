"""
Custom Bulk Grading Test Runner with Adjustable Confidence Threshold & Crop Shrink Factor
"""
import sys
import argparse

sys.path.append('backend')
from cv.bulk_grading import grade_bulk

def test_custom():
    parser = argparse.ArgumentParser(description="Test Bulk Grading on Custom Image")
    parser.add_argument("image_path", help="Path to produce photo")
    parser.add_argument("expected_product", help="Expected product species (e.g. apple, tomato, banana)")
    parser.add_argument("--conf", type=float, default=0.75, help="Detection confidence threshold (default 0.75)")
    parser.add_argument("--shrink", type=float, default=0.70, help="Center-crop inner shrink factor (default 0.70)")
    
    args = parser.parse_args()
    
    print("\n" + "=" * 65)
    print(f" TESTING BULK GRADING ON CUSTOM IMAGE")
    print("=" * 65)
    print(f"Image Path:       {args.image_path}")
    print(f"Expected Product: {args.expected_product}")
    print(f"Confidence Thresh:{args.conf}")
    print(f"Crop Shrink Factor:{args.shrink}")
    print("=" * 65)
    
    res = grade_bulk(args.image_path, expected_product=args.expected_product, crop_shrink_factor=args.shrink, det_conf_threshold=args.conf)
    
    print("\n" + "=" * 65)
    print(" BULK GRADING RESULT SUMMARY")
    print("=" * 65)
    print(f"Status:                   {res.get('status')}")
    print(f"Product Mismatch Flag:    {res.get('product_mismatch')}")
    print(f"Total Detections:         {res.get('total_items_detected')}")
    print(f"Confidently Graded Count: {res.get('confidently_graded_count')}")
    print(f"Skipped Low-Conf Count:   {res.get('skipped_low_conf_count')}")
    print(f"Fresh Count:              {res.get('fresh_count')}")
    print(f"Defect Count:             {res.get('major_defect_count', 0) + res.get('minor_defect_count', 0)}")
    print(f"Defect Coverage %:        {res.get('defect_coverage_percent')}%")
    print(f"Weighted Quality Score:   {res.get('weighted_quality_score')}/100")
    print(f"Batch Quality Grade:      {res.get('batch_grade')}")
    print(f"Message:                  {res.get('message')}")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    test_custom()
