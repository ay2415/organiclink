import os
import shutil

BASE_DIR = os.path.abspath(".")
UNUSED_DIR = os.path.join(BASE_DIR, "unused_files")

moves = [
    ("training_log_2026-08-01.txt", "root/training_log_2026-08-01.txt"),
    ("backend/contact_sheet_all_classes.png", "backend/contact_sheet_all_classes.png"),
    ("backend/test_phase1.py", "backend/test_phase1.py"),
    ("backend/cv/dedupe_check.py", "backend_cv/dedupe_check.py"),
    ("backend/cv/duplicate_pairs.csv", "backend_cv/duplicate_pairs.csv"),
    ("backend/cv/clean_split.csv", "backend_cv/clean_split.csv"),
    ("backend/cv/duplicate_report.txt", "backend_cv/duplicate_report.txt"),
]

for src_rel, dst_rel in moves:
    src_path = os.path.join(BASE_DIR, src_rel)
    dst_path = os.path.join(UNUSED_DIR, dst_rel)
    if os.path.exists(src_path):
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        shutil.move(src_path, dst_path)
        print(f"Moved {src_rel} -> unused_files/{dst_rel}")

# Move contents of scratch/ into unused_files/scratch/ except move_unused_files.py
scratch_dir = os.path.join(BASE_DIR, "scratch")
unused_scratch_dir = os.path.join(UNUSED_DIR, "scratch")
os.makedirs(unused_scratch_dir, exist_ok=True)

if os.path.exists(scratch_dir):
    for item in os.listdir(scratch_dir):
        if item == "move_unused_files.py":
            continue
        s = os.path.join(scratch_dir, item)
        d = os.path.join(unused_scratch_dir, item)
        if os.path.exists(s):
            if os.path.exists(d):
                if os.path.isdir(d):
                    shutil.rmtree(d)
                else:
                    os.remove(d)
            shutil.move(s, d)
            print(f"Moved scratch/{item} -> unused_files/scratch/{item}")

print("File migration to unused_files completed successfully!")
