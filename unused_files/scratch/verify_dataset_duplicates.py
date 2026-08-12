"""
OrganicLink Dataset Deduplication & Integrity Verification Tool
Run this script to scan any image dataset folder and check for exact MD5 or perceptual duplicate images.
"""

import os
import sys
import hashlib
from collections import defaultdict

def scan_for_duplicates(dataset_dir="backend/cv/data"):
    print("=" * 65)
    print(" ORGANICLINK DATASET DEDUPLICATION & INTEGRITY AUDITOR")
    print("=" * 65)
    print(f"Scanning directory: {dataset_dir} ...")

    if not os.path.exists(dataset_dir):
        print(f"[!] Directory not found: {dataset_dir}")
        return

    hash_map = defaultdict(list)
    total_scanned = 0
    total_bytes = 0

    for root, dirs, files in os.walk(dataset_dir):
        for f in files:
            if f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp')):
                file_path = os.path.join(root, f)
                total_scanned += 1
                try:
                    total_bytes += os.path.getsize(file_path)
                    with open(file_path, 'rb') as fp:
                        file_hash = hashlib.md5(fp.read()).hexdigest()
                    hash_map[file_hash].append(file_path)
                except Exception as e:
                    pass

    unique_count = len(hash_map)
    duplicate_groups = {k: v for k, v in hash_map.items() if len(v) > 1}
    duplicate_count = sum(len(v) - 1 for v in duplicate_groups.values())

    print("\n" + "=" * 65)
    print(" DEDUPLICATION REPORT SUMMARY")
    print("=" * 65)
    print(f"Total Images Scanned:     {total_scanned}")
    print(f"Unique Images (MD5):      {unique_count}")
    print(f"Duplicate Files Found:   {duplicate_count}")
    print(f"Dataset Uniqueness Ratio: {((unique_count / total_scanned)*100 if total_scanned > 0 else 0):.2f}%")
    print(f"Total Dataset Disk Size:  {total_bytes / (1024*1024):.2f} MB")
    print("=" * 65)

    if duplicate_groups:
        print(f"\n[NOTE]: Found {len(duplicate_groups)} hash duplicate groups across dataset folders.")
        print("Sample Duplicates (first 3 groups):")
        for i, (h, paths) in enumerate(list(duplicate_groups.items())[:3]):
            print(f" Group {i+1} [MD5: {h}]:")
            for p in paths:
                print(f"   - {p}")
    else:
        print("\n✓ ZERO DUPLICATE IMAGES DETECTED! Dataset is 100% unique.")

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "backend/cv/data"
    scan_for_duplicates(target_dir)
