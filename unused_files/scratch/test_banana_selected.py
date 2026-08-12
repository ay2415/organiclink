import os, sys
sys.path.append('backend')
from cv.bulk_grading import grade_bulk

print("\n============================================================")
print("TESTING WHOLE-IMAGE ONLY PRODUCT MATCH (NO FALSE PER-CROP MISMATCH)")
print("============================================================")

# Testing tomato image with tomato expected
res = grade_bulk("scratch/latest_media.jpg", expected_product="tomato")
print(f"Status when Tomato photo + Tomato selected: {res.get('status')}")
print(f"Batch Grade: {res.get('batch_grade')}")
print(f"Message: {res.get('message')}")

assert res.get("status") == "graded", "Test Failed: Tomato + Tomato should grade normally"
assert res.get("product_mismatch") == False, "Test Failed: product_mismatch should be False"

print("\n✓ TOMATO + TOMATO GRADED NORMALLY WITHOUT PER-CROP FALSE MISMATCH!")
