#!/usr/bin/env python3
"""
train_all_overnight.py
=======================
ONE FILE that does everything, safely, for an overnight run:

  STEP 1  Scan ALL datasets inside backend/cv/data (old 2 folders + new Kaggle folder)
  STEP 2  DEDUPE with perceptual hashing -> build a CLEAN GROUPED SPLIT
          (near-duplicates are kept on ONE side, so NO train/val leakage)
  STEP 3  TRAIN the multi-head model (product + fresh/defect) on the clean split
  STEP 4  SAVE to a NEW filename so your working model is NEVER touched

WHAT IT SAVES (in backend/cv/models/):
  grading_model_v8_overnight.pt   <- the NEW model (safe, separate name)
  clean_split_v8.csv              <- the leak-free split
  dedupe_report_v8.txt            <- duplicate finding (for your thesis)
  eval_report_v8.txt              <- honest accuracy on the clean split
Your existing grading_model.pt is NOT modified.

HOW TO RUN (before you leave):
  pip install torch torchvision pillow imagehash numpy
  cd backend/cv
  python train_all_overnight.py

It saves the BEST model after every epoch, so even if you stop it in the
morning at epoch 5 or 6, you already have a usable checkpoint.
"""

import os, csv, time, platform, warnings, random
from collections import defaultdict, Counter
from pathlib import Path

import numpy as np
from PIL import Image
import torch, torch.nn as nn, torch.optim as optim
from torch.utils.data import DataLoader, Dataset
import torchvision.transforms as transforms
from torchvision.models import resnet18, ResNet18_Weights

warnings.filterwarnings("ignore")
Image.MAX_IMAGE_PIXELS = None

# ----------------------------------------------------------------------
# PATHS
# ----------------------------------------------------------------------
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")          # contains ALL dataset folders
MODELS_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

MODEL_OUT   = os.path.join(MODELS_DIR, "grading_model_v8_overnight.pt")  # NEW name - safe
SPLIT_CSV   = os.path.join(MODELS_DIR, "clean_split_v8.csv")
DEDUPE_TXT  = os.path.join(MODELS_DIR, "dedupe_report_v8.txt")
EVAL_TXT    = os.path.join(MODELS_DIR, "eval_report_v8.txt")

# ----------------------------------------------------------------------
# CLASSES  (14 products; quality is binary fresh vs defect)
# ----------------------------------------------------------------------
PRODUCT_CLASSES = ["apple","banana","capsicum","carrot","cucumber","grape",
    "guava","jujube","lime","mango","orange","pomegranate","potato",
    "strawberry","tomato"]
DEFECT_CLASSES  = ["fresh","defect"]

ALIASES = {"bellpepper":"capsicum","bell_pepper":"capsicum","pepper":"capsicum",
    "capsicum":"capsicum","grapes":"grape","tomatoes":"tomato","carrots":"carrot",
    "potatoes":"potato","oranges":"orange","apples":"apple","bananas":"banana",
    "strawberries":"strawberry","limes":"lime","lemon":"lime","okra":None,
    "bittergourd":None,"bitter_gourd":None,"bitterg":None,
    # --- Kaggle "fresh and stale" dataset misspellings ---
    "patato":"potato","patatos":"potato","patatoes":"potato",
    "tamto":"tomato","tamtos":"tomato","tamato":"tomato",
    "cucum":"cucumber","capsic":"capsicum","oranges":"orange"}

FRESH_KEYS = ("healthy","fresh","good","ripe")
DEFECT_KEYS = ("rotten","stale","bad","spoiled","diseased","defect","major","minor","mixed")

# ----------------------------------------------------------------------
# HYPERPARAMETERS
# ----------------------------------------------------------------------
HP = {
    "warmup_epochs": 3,
    "finetune_epochs": 17,     # total up to 20; early-stops if no improvement
    "batch_size": 32,
    "lr_head": 1e-3,
    "lr_finetune": 8e-5,
    "weight_decay": 1e-4,
    "weight_cap": 5.0,
    "val_frac": 0.2,
    "patience": 5,
    "img": 224,
    "prod_w": 1.5,             # product head weighted higher (it's the weak head)
    "def_w": 1.0,
    "phash_threshold": 3,      # near-duplicate Hamming distance
    "seed": 42,
}

# ----------------------------------------------------------------------
# LABEL PARSING  (works out product + fresh/defect from the folder name)
# ----------------------------------------------------------------------
def parse_label(folder_name):
    n = folder_name.lower().replace("-", " ").replace("_", " ")
    # quality first
    quality = None
    if any(k in n for k in DEFECT_KEYS):
        quality = 1  # defect
    elif any(k in n for k in FRESH_KEYS):
        quality = 0  # fresh
    if quality is None:
        return None, None
    # product - check aliases first (longest first to avoid partial clashes)
    product = None
    matched_alias = False
    for alias in sorted(ALIASES.keys(), key=len, reverse=True):
        if alias in n.replace(" ", ""):
            mapped = ALIASES[alias]
            if mapped is None:
                return None, None   # okra / bitter_gourd -> skip cleanly
            product = mapped
            matched_alias = True
            break
    if product is None:
        for cand in sorted(PRODUCT_CLASSES, key=len, reverse=True):
            if cand in n.replace(" ", ""):
                product = cand
                break
    if product is None or product not in PRODUCT_CLASSES:
        return None, None
    return PRODUCT_CLASSES.index(product), quality

# ----------------------------------------------------------------------
# STEP 1 + 2 : SCAN + DEDUPE -> CLEAN GROUPED SPLIT
# ----------------------------------------------------------------------
def build_clean_split():
    print("="*64)
    print("STEP 1+2 : SCAN ALL DATA  +  DEDUPE  ->  CLEAN GROUPED SPLIT")
    print("="*64)
    import imagehash

    IMG_EXT = {".jpg",".jpeg",".png",".bmp",".webp"}
    items = []   # (path, product_idx, quality_idx)
    for p in Path(DATA_DIR).rglob("*"):
        if p.suffix.lower() in IMG_EXT:
            prod, qual = parse_label(p.parent.name)
            if prod is None:
                continue
            items.append((str(p), prod, qual))
    print(f"Usable labelled images found: {len(items)}")
    if not items:
        print("NO labelled images found - check folder names in data/.")
        return False

    # perceptual hash
    print("Hashing (perceptual)... this takes a while on CPU")
    hashed = []
    for i,(path,prod,qual) in enumerate(items):
        try:
            with Image.open(path) as im:
                h = imagehash.phash(im.convert("RGB"))
            hashed.append((path,prod,qual,h))
        except Exception:
            pass
        if i % 3000 == 0:
            print(f"  hashed {i}/{len(items)}")

    # bucket + union-find near-duplicates
    buckets = defaultdict(list)
    for rec in hashed:
        s = str(rec[3])
        for c in range(4):
            buckets[(c, s[c*4:(c+1)*4])].append(rec)
    parent = {rec[0]:rec[0] for rec in hashed}
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]]; x=parent[x]
        return x
    def union(a,b):
        ra,rb=find(a),find(b)
        if ra!=rb: parent[rb]=ra
    pairs=0; seen=set()
    for b in buckets.values():
        for i in range(len(b)):
            for j in range(i+1,len(b)):
                a1,a2=b[i],b[j]
                key=(a1[0],a2[0]) if a1[0]<a2[0] else (a2[0],a1[0])
                if key in seen: continue
                seen.add(key)
                if a1[3]-a2[3] <= HP["phash_threshold"]:
                    union(a1[0],a2[0]); pairs+=1

    groups=defaultdict(list)
    for rec in hashed:
        groups[find(rec[0])].append(rec)
    multi=[g for g in groups.values() if len(g)>1]
    dup_imgs=sum(len(g) for g in multi)
    pct = dup_imgs/max(1,len(hashed))*100

    # grouped split: whole duplicate group -> one side, stratified by product
    random.seed(HP["seed"])
    by_prod=defaultdict(list)
    for members in groups.values():
        by_prod[members[0][1]].append(members)
    rows=[]
    for prod,glist in by_prod.items():
        random.shuffle(glist)
        n_val=max(1,int(round(len(glist)*HP["val_frac"])))
        for i,members in enumerate(glist):
            split="val" if i<n_val else "train"
            for (path,pr,qu,h) in members:
                rows.append((path,pr,qu,split))

    with open(SPLIT_CSV,"w",newline="") as f:
        w=csv.writer(f); w.writerow(["path","product","quality","split"])
        w.writerows(rows)

    n_train=sum(1 for r in rows if r[3]=="train")
    n_val=sum(1 for r in rows if r[3]=="val")
    report=(f"DEDUPE REPORT (v8, all datasets combined)\n"
            f"{'='*50}\n"
            f"Total images hashed:     {len(hashed)}\n"
            f"Near-duplicate groups:   {len(multi)}\n"
            f"Images with a twin:      {dup_imgs} ({pct:.1f}%)\n"
            f"Colliding pairs:         {pairs}\n"
            f"Clean grouped split:     train {n_train} / val {n_val}\n"
            f"Twins confined to one side -> NO train/val leakage.\n")
    open(DEDUPE_TXT,"w").write(report)
    print("\n"+report)
    return True

# ----------------------------------------------------------------------
# MODEL
# ----------------------------------------------------------------------
class MultiHead(nn.Module):
    def __init__(s, n_prod=15, n_def=2):
        super().__init__()
        b=resnet18(weights=ResNet18_Weights.DEFAULT)
        f=b.fc.in_features; b.fc=nn.Identity()
        s.backbone=b
        s.product_head=nn.Sequential(nn.Dropout(0.2), nn.Linear(f,n_prod))
        s.defect_head =nn.Sequential(nn.Dropout(0.3), nn.Linear(f,n_def))
    def forward(s,x):
        f=s.backbone(x); return s.product_head(f), s.defect_head(f)
    def set_backbone_trainable(s,flag):
        for p in s.backbone.parameters(): p.requires_grad=flag

# ----------------------------------------------------------------------
# DATASET (reads the clean split csv)
# ----------------------------------------------------------------------
class SplitDS(Dataset):
    def __init__(s, which, tf):
        s.tf=tf; s.samples=[]
        with open(SPLIT_CSV) as f:
            for r in csv.DictReader(f):
                if r["split"]!=which: continue
                s.samples.append((r["path"], int(r["product"]), int(r["quality"])))
    def __len__(s): return len(s.samples)
    def __getitem__(s,i):
        path,pr,qu=s.samples[i]
        img=Image.open(path).convert("RGB")
        return s.tf(img), pr, qu
    def dist(s):
        return Counter(x[1] for x in s.samples), Counter(x[2] for x in s.samples)

def metrics(yt,yp,n):
    cm=np.zeros((n,n),int)
    for t,p in zip(yt,yp): cm[t][p]+=1
    acc=float(np.trace(cm)/cm.sum()) if cm.sum() else 0.0
    f1s=[]
    for i in range(n):
        tp=cm[i][i]; fp=cm[:,i].sum()-tp; fn=cm[i,:].sum()-tp
        pr=tp/(tp+fp) if tp+fp else 0; rc=tp/(tp+fn) if tp+fn else 0
        f1s.append(2*pr*rc/(pr+rc) if pr+rc else 0)
    return acc, float(np.mean(f1s))

@torch.no_grad()
def evaluate(m,ld,dev):
    m.eval(); pt,pp,dt,dp=[],[],[],[]
    for x,pr,qu in ld:
        x=x.to(dev); po,do=m(x)
        pp+=torch.argmax(po,1).cpu().tolist(); dp+=torch.argmax(do,1).cpu().tolist()
        pt+=pr.tolist(); dt+=qu.tolist()
    return pt,pp,dt,dp

# ----------------------------------------------------------------------
# STEP 3 + 4 : TRAIN + SAVE (new filename)
# ----------------------------------------------------------------------
def train():
    print("="*64)
    print("STEP 3+4 : TRAIN ON CLEAN SPLIT  ->  SAVE NEW MODEL")
    print("="*64)
    torch.manual_seed(HP["seed"]); np.random.seed(HP["seed"])
    sz=HP["img"]
    train_tf=transforms.Compose([
        transforms.RandomResizedCrop(sz,scale=(0.6,1.0)),
        transforms.RandomHorizontalFlip(), transforms.RandomVerticalFlip(0.3),
        transforms.RandomRotation(30),
        transforms.ColorJitter(0.4,0.4,0.4,0.1),
        transforms.RandomApply([transforms.GaussianBlur(3)],p=0.2),
        transforms.RandomGrayscale(p=0.05),
        transforms.ToTensor(),
        transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225]),
        transforms.RandomErasing(p=0.2,scale=(0.02,0.15)),
    ])
    val_tf=transforms.Compose([
        transforms.Resize((sz,sz)), transforms.ToTensor(),
        transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225]),
    ])

    tr=SplitDS("train",train_tf); va=SplitDS("val",val_tf)
    pc,dc=tr.dist()
    print(f"Train {len(tr)}  Val {len(va)}")
    print("Products:", {PRODUCT_CLASSES[k]:v for k,v in sorted(pc.items())})
    print("Quality :", {DEFECT_CLASSES[k]:v for k,v in sorted(dc.items())})
    nw = 0 if platform.system()=="Windows" else 2
    trl=DataLoader(tr,HP["batch_size"],shuffle=True,num_workers=nw)
    val=DataLoader(va,HP["batch_size"],shuffle=False,num_workers=nw)
    dev=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Device:",dev)

    m=MultiHead(len(PRODUCT_CLASSES),len(DEFECT_CLASSES)).to(dev)

    # quick 30s diagnostic - product should climb fast
    print("\nDIAGNOSTIC (product % should climb past 60):")
    m.set_backbone_trainable(True)
    do=optim.AdamW(m.parameters(),1e-3); cp=nn.CrossEntropyLoss(); cd=nn.CrossEntropyLoss()
    xb,pb,db=next(iter(trl)); xb,pb,db=xb.to(dev),pb.to(dev),db.to(dev)
    for st in range(12):
        do.zero_grad(); po,dov=m(xb); (cp(po,pb)+cd(dov,db)).backward(); do.step()
        if st%4==0 or st==11:
            acc=(torch.argmax(po,1)==pb).float().mean().item()*100
            print(f"  step {st}: product {acc:.0f}%")
    # reset model after diagnostic
    m=MultiHead(len(PRODUCT_CLASSES),len(DEFECT_CLASSES)).to(dev)

    def capped(counter,n,total):
        return torch.tensor([min(total/(n*max(counter.get(i,1),1)),HP["weight_cap"])
                             for i in range(n)],dtype=torch.float32).to(dev)
    cprod=nn.CrossEntropyLoss(weight=capped(pc,len(PRODUCT_CLASSES),len(tr)))
    cdef =nn.CrossEntropyLoss(weight=capped(dc,len(DEFECT_CLASSES),len(tr)))

    total=HP["warmup_epochs"]+HP["finetune_epochs"]; best=0.0; noimp=0
    def make_opt(phase):
        if phase=="warmup":
            m.set_backbone_trainable(False)
            return optim.AdamW([p for p in m.parameters() if p.requires_grad],
                               HP["lr_head"],weight_decay=HP["weight_decay"])
        m.set_backbone_trainable(True)
        return optim.AdamW(m.parameters(),HP["lr_finetune"],weight_decay=HP["weight_decay"])
    phase="warmup"; opt=make_opt(phase)
    sched=optim.lr_scheduler.CosineAnnealingLR(opt,T_max=HP["finetune_epochs"])

    for e in range(total):
        if e==HP["warmup_epochs"]:
            phase="finetune"; opt=make_opt(phase)
            sched=optim.lr_scheduler.CosineAnnealingLR(opt,T_max=HP["finetune_epochs"])
            print("-- finetune phase --")
        m.train()
        for x,pr,qu in trl:
            x,pr,qu=x.to(dev),pr.to(dev),qu.to(dev)
            opt.zero_grad(); po,do=m(x)
            loss=HP["prod_w"]*cprod(po,pr)+HP["def_w"]*cdef(do,qu)
            loss.backward(); opt.step()
        if phase=="finetune": sched.step()

        pt,pp,dt,dp=evaluate(m,val,dev)
        pacc,pf1=metrics(pt,pp,len(PRODUCT_CLASSES))
        dacc,df1=metrics(dt,dp,len(DEFECT_CLASSES))
        combined=(pacc+dacc)/2*100
        print(f"[{e+1}/{total}] {phase} | product {pacc*100:.1f}% (F1 {pf1:.3f}) "
              f"| quality {dacc*100:.1f}% (F1 {df1:.3f})")
        if combined>best:
            best=combined; noimp=0
            torch.save(m.state_dict(), MODEL_OUT)
            print(f"   -> saved best to {os.path.basename(MODEL_OUT)}")
        else:
            noimp+=1
            if phase=="finetune" and noimp>=HP["patience"]:
                print("   early stop (no improvement)"); break

    # final honest report on best model
    m.load_state_dict(torch.load(MODEL_OUT,map_location=dev))
    pt,pp,dt,dp=evaluate(m,val,dev)
    pacc,pf1=metrics(pt,pp,len(PRODUCT_CLASSES))
    dacc,df1=metrics(dt,dp,len(DEFECT_CLASSES))
    rep=(f"EVAL (v8, clean deduplicated split - honest)\n{'='*50}\n"
         f"Product accuracy: {pacc*100:.2f}%  (macro F1 {pf1:.4f})\n"
         f"Quality accuracy: {dacc*100:.2f}%  (macro F1 {df1:.4f})\n"
         f"Model saved: {MODEL_OUT}\n"
         f"(Your working grading_model.pt was NOT modified.)\n")
    open(EVAL_TXT,"w").write(rep)
    print("\n"+rep)

# ----------------------------------------------------------------------
def main():
    t0=time.time()
    ok=build_clean_split()
    if not ok:
        print("Aborting - no data."); return
    train()
    print(f"\nALL DONE in {(time.time()-t0)/60:.1f} min")
    print(f"NEW model: {MODEL_OUT}")
    print("Your existing grading_model.pt is untouched (safe fallback).")

if __name__ == "__main__":
    main()
