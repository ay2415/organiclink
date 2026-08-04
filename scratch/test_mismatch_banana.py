import os, sys
sys.path.append('backend')
from cv.bulk_grading import grade_bulk

print("\n============================================================")
print("TESTING BANANA UPLOAD WITH TOMATO EXPECTED (MISMATCH TEST)")
print("============================================================")

# Testing with a banana image or calling mismatch logic
res = grade_bulk("scratch/latest_media.jpg", expected_product="banana")
print(f"Status when selecting Banana for Tomato photo: {res.get('status')}")
print(f"Message: {res.get('message')}")
assert res.get("status") == "mismatch", "Mismatch Test Failed: Should return mismatch status"
assert res.get("product_mismatch") == True, "Mismatch Test Failed: product_mismatch should be True"

print("\n✓ BANANA / TOMATO MISMATCH TEST PASSED PERFECTLY!")
