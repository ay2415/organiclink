#!/usr/bin/env python3
"""
dedupe_check.py — find near-duplicate images leaking across train/val,
then write a clean grouped split.

Install:
    pip install pillow imagehash tqdm

Usage:
    # Case A: you have train/ and val/ folders already
    python dedupe_check.py --train /path/to/train --val /path/to/val

    # Case B: you have one folder of class subfolders (no split yet)
    python dedupe_check.py --data /path/to/dataset

Outputs (written next to this script):
    duplicate_report.txt   - human-readable summary
    duplicate_pairs.csv    - every colliding pair found
    clean_split.csv        - filepath,class,split  (duplicates kept on ONE side)
"""

import argparse
import csv
import os
import random
from collections import defaultdict
from pathlib import Path

from PIL import Image
import imagehash
from tqdm import tqdm

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# Hamming distance threshold. 0 = pixel-identical after hashing.
# 1-3 = near-duplicate (crop, resize, brightness, mild augmentation).
# Keep this <= 3: the 4-chunk bucketing below only guarantees it finds
# every pair up to distance 3 (pigeonhole principle on 4 x 16-bit chunks).
THRESHOLD = 3


def collect(root, split_label):
    """Walk a folder. Assumes class name is the immediate parent folder."""
    items = []
    for path in Path(root).rglob("*"):
        if path.suffix.lower() in IMG_EXT:
            items.append((str(path), path.parent.name, split_label))
    return items


def hash_all(items):
    """Compute perceptual hash for every image."""
    hashed = []
    failed = 0
    for filepath, cls, split in tqdm(items, desc="hashing"):
        try:
            with Image.open(filepath) as im:
                h = imagehash.phash(im.convert("RGB"))
            hashed.append((filepath, cls, split, h))
        except Exception:
            failed += 1
    return hashed, failed


def find_groups(hashed):
    """
    Bucket by hash prefix, then compare within buckets.
    Avoids an O(n^2) comparison across 48k images.
    """
    # Multi-index hashing: split the 64-bit hash into four 16-bit chunks
    # and bucket on each one. Two hashes within 3 bits of each other must
    # match exactly on at least one chunk, so nothing is missed.
    buckets = defaultdict(list)
    for rec in hashed:
        s = str(rec[3])
        for c in range(4):
            buckets[(c, s[c * 4:(c + 1) * 4])].append(rec)

    parent = {rec[0]: rec[0] for rec in hashed}
    seen_pairs = set()

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    pairs = []
    for bucket in tqdm(buckets.values(), desc="comparing"):
        for i in range(len(bucket)):
            for j in range(i + 1, len(bucket)):
                a, b = bucket[i], bucket[j]
                key = (a[0], b[0]) if a[0] < b[0] else (b[0], a[0])
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                dist = a[3] - b[3]
                if dist <= THRESHOLD:
                    pairs.append((a[0], b[0], a[2], b[2], a[1], b[1], dist))
                    union(a[0], b[0])

    groups = defaultdict(list)
    for rec in hashed:
        groups[find(rec[0])].append(rec)

    return groups, pairs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train")
    ap.add_argument("--val")
    ap.add_argument("--data")
    ap.add_argument("--val-frac", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    if args.data:
        items = collect(args.data, "unsplit")
    elif args.train and args.val:
        items = collect(args.train, "train") + collect(args.val, "val")
    else:
        ap.error("give either --data, or both --train and --val")

    print(f"found {len(items)} images")
    hashed, failed = hash_all(items)
    if failed:
        print(f"skipped {failed} unreadable files")

    groups, pairs = find_groups(hashed)

    # --- leakage: groups that span both train and val ---
    leaked = []
    for members in groups.values():
        splits = {m[2] for m in members}
        if "train" in splits and "val" in splits:
            leaked.append(members)

    leaked_images = sum(len(g) for g in leaked)
    multi = [g for g in groups.values() if len(g) > 1]
    dup_images = sum(len(g) for g in multi)

    # --- clean grouped split: whole group goes to one side ---
    random.seed(args.seed)
    by_class = defaultdict(list)
    for members in groups.values():
        cls = members[0][1]
        by_class[cls].append(members)

    rows = []
    for cls, glist in by_class.items():
        random.shuffle(glist)
        n_val = max(1, int(round(len(glist) * args.val_frac)))
        for i, members in enumerate(glist):
            split = "val" if i < n_val else "train"
            for m in members:
                rows.append((m[0], cls, split))

    out = Path(__file__).parent

    with open(out / "clean_split.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["filepath", "class", "split"])
        w.writerows(rows)

    with open(out / "duplicate_pairs.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file_a", "file_b", "split_a", "split_b",
                    "class_a", "class_b", "hamming"])
        w.writerows(pairs)

    n_train = sum(1 for r in rows if r[2] == "train")
    n_val = sum(1 for r in rows if r[2] == "val")

    report = f"""DUPLICATE / LEAKAGE REPORT
{'=' * 50}
Total images hashed:          {len(hashed)}
Unreadable / skipped:         {failed}
Perceptual hash:              phash, threshold <= {THRESHOLD}

Duplicate groups (size > 1):  {len(multi)}
Images inside those groups:   {dup_images}  ({dup_images / max(1, len(hashed)):.1%} of dataset)
Colliding pairs:              {len(pairs)}

TRAIN/VAL LEAKAGE
Groups spanning both splits:  {len(leaked)}
Images involved in leakage:   {leaked_images}

NEW GROUPED SPLIT
Train: {n_train}    Val: {n_val}
Written to clean_split.csv — duplicates are confined to one side.

NEXT STEP
Re-run evaluation with your EXISTING weights against clean_split.csv.
Do not retrain. Report both numbers in the thesis:
  "99.3% on random per-image split, X% on deduplicated grouped split."
"""

    with open(out / "duplicate_report.txt", "w") as f:
        f.write(report)

    print(report)


if __name__ == "__main__":
    main()