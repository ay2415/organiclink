import os
import hashlib
import datetime
import torch
import sys

sys.path.append(os.path.abspath('backend'))
from cv.inference import PRODUCT_CLASSES_15, PRODUCT_CLASSES_16, DEFECT_CLASSES

models_dir = os.path.abspath(os.path.join('backend', 'cv', 'models'))
print("=== PHASE 1: MODEL RESTORE VERIFICATION REPORT ===\n")

pt_files = [f for f in os.listdir(models_dir) if f.endswith('.pt')]

hashes = {}

for fname in pt_files:
    fpath = os.path.join(models_dir, fname)
    size = os.path.getsize(fpath)
    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(fpath)).strftime('%Y-%m-%d %H:%M:%S')
    
    with open(fpath, 'rb') as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()
    hashes[fname] = sha256

    print(f"File: {fname}")
    print(f"  - Size: {size:,} bytes")
    print(f"  - Modification Date: {mtime}")
    print(f"  - SHA-256 Hash: {sha256}\n")

if 'grading_model.pt' in hashes and 'quality_model.pt' in hashes:
    if hashes['grading_model.pt'] != hashes['quality_model.pt']:
        print("[CONFIRMATION] grading_model.pt and quality_model.pt are DIFFERENT files (hashes do not match).\n")
    else:
        print("[WARNING] grading_model.pt and quality_model.pt have IDENTICAL hashes.\n")

for fname in ['grading_model.pt', 'quality_model.pt']:
    fpath = os.path.join(models_dir, fname)
    if not os.path.exists(fpath):
        print(f"Cannot inspect {fname}: File does not exist.\n")
        continue

    print(f"--- Model Inspection: {fname} ---")
    state = torch.load(fpath, map_location='cpu')

    p_weight = None
    if 'product_head.weight' in state:
        p_weight = state['product_head.weight']
    elif 'product_head.1.weight' in state:
        p_weight = state['product_head.1.weight']

    d_weight = None
    if 'defect_head.weight' in state:
        d_weight = state['defect_head.weight']
    elif 'defect_head.1.weight' in state:
        d_weight = state['defect_head.1.weight']

    p_out = p_weight.shape[0] if p_weight is not None else 'Unknown'
    d_out = d_weight.shape[0] if d_weight is not None else 'Unknown'

    if p_out == 16:
        class_list = PRODUCT_CLASSES_16
    else:
        class_list = PRODUCT_CLASSES_15

    print(f"  - Product Head Class Count (out_features): {p_out}")
    print(f"  - Quality/Defect Head Class Count (out_features): {d_out}")
    print(f"  - Class Name List ({len(class_list)} classes):")
    print(f"    {class_list}\n")
