import os, sys
sys.path.append('backend')
from cv.bulk_grading import grade_bulk

def test_fixes():
    print("============================================================")
    print("TESTING BULK GRADING PROMPT FIXES")
    print("============================================================")

    # 1. Test Bulk Grading on Tomato Pile (Problem 1 Verification)
    print("\n--- Test 1: Tomatoes Batch Grading & Defect Aggregation ---")
    res1 = grade_bulk("scratch/latest_tomato_user.jpg", expected_product="tomato")
    print(f"Status: {res1.get('status')}")
    print(f"Message: {res1.get('message')}")
    print(f"Fresh Count: {res1.get('fresh_count')} / {res1.get('matching_items_total')}")
    print(f"Fresh Percent: {res1.get('fresh_percent')}%")
    print(f"Defect Percent / Coverage: {res1.get('defect_percent')}%")
    print(f"Batch Quality Score: {res1.get('weighted_quality_score')}")
    print(f"Batch Quality Grade: {res1.get('batch_grade')}")
    assert res1.get("status") == "graded", "Test 1 Failed: Status should be graded"
    assert res1.get("defect_percent") is not None, "Test 1 Failed: Defect percent missing"

    # 2. Test Product Mismatch (Bananas uploaded, Tomato selected - Problem 2 Verification)
    print("\n--- Test 2: Product Mismatch (Bananas uploaded, Tomato selected) ---")
    # Using an available media file or generating test image
    test_img = "scratch/latest_media.jpg"
    if os.path.exists(test_img):
        res2 = grade_bulk(test_img, expected_product="tomato")
        print(f"Status: {res2.get('status')}")
        print(f"Product Mismatch Flag: {res2.get('product_mismatch')}")
        print(f"Message: {res2.get('message')}")

    print("\n============================================================")
    print("BULK GRADING PROMPT FIXES TEST COMPLETE")
    print("============================================================")

if __name__ == "__main__":
    test_fixes()
