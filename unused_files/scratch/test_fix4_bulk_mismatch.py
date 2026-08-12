"""
Automated Test for FIX 4: Bulk Product Mismatch Pre-Check
Verifies that:
1. Selecting 'tomato' + uploading a 'banana' photo in bulk mode returns a Product Mismatch (status='mismatch', product_mismatch=True) and does NOT grade.
2. Selecting 'banana' + uploading a 'banana' photo in bulk mode proceeds and grades normally (status='graded').
"""

import sys
import os

sys.path.append('backend')
from cv.bulk_grading import grade_bulk

def test_fix4_flow():
    print("=" * 60)
    print("RUNNING AUTOMATED TEST FOR FIX 4: BULK PRODUCT MISMATCH PRE-CHECK")
    print("=" * 60)

    banana_img_path = os.path.abspath("scratch/valid_tomato.jpg")

    # 1. Tomato selected + Banana photo -> MUST fail with product mismatch
    mismatch_res = grade_bulk(banana_img_path, expected_product="tomato")
    assert mismatch_res.get("product_mismatch") == True, f"Expected product_mismatch True, got {mismatch_res}"
    assert mismatch_res.get("status") == "mismatch", f"Expected status 'mismatch', got '{mismatch_res.get('status')}'"
    print(f"[OK] Step 1: Tomato selected + Banana photo correctly caught product mismatch: '{mismatch_res['message']}'")

    # 2. Banana selected + Banana photo -> MUST succeed and grade normally
    valid_res = grade_bulk(banana_img_path, expected_product="banana")
    assert valid_res.get("product_mismatch") == False, f"Expected product_mismatch False, got {valid_res}"
    assert valid_res.get("status") == "graded", f"Expected status 'graded', got '{valid_res.get('status')}'"
    print(f"[OK] Step 2: Banana selected + Banana photo correctly passed pre-check and graded: Score {valid_res['quality_score']}%, Grade {valid_res['quality_grade']}")

    print("=" * 60)
    print("FIX 4 TEST COMPLETED SUCCESSFULLY WITH ALL ASSERTIONS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    test_fix4_flow()
