import sys, os
sys.path.append(os.path.abspath('backend'))
from cv.bulk_grading import grade_bulk

print("=== TESTING BUG 1 FIX: BULK GRADING EXPLICIT NONE-HANDLING ===")
img = os.path.abspath("backend/uploads/insp_6e2f954d7b0046e7bb658766c7f16663.jpg")
if os.path.exists(img):
    res = grade_bulk(img, expected_product="tomato")
    print("\nResult status:", res.get("status"))
    print("Weighted score:", res.get("weighted_quality_score"))
    print("Batch grade:", res.get("batch_grade"))
    print("Items detected:", res.get("total_items_detected"), "Matching:", res.get("matching_items_total"), "Excluded:", res.get("excluded_items_count"))
else:
    print("Test image not found:", img)
