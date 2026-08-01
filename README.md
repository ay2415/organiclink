# OrganicLink: A Computer-Vision Marketplace for Irish Organic Producers with Automated Produce Quality Grading

[![FastAPI](https://img.shields.io/badge/Backend-Python_3.11_|_FastAPI_|_SQLAlchemy_2.0-green.svg)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/CV_Engine-PyTorch_|_ResNet--18_Dual--Head-orange.svg)](https://pytorch.org)
[![YOLOv8](https://img.shields.io/badge/Object_Detection-YOLOv8_5--Step_Bulk_Engine-yellow.svg)](https://ultralytics.com)
[![React 18](https://img.shields.io/badge/Frontend-React_18_|_Vite_|_Tailwind_CSS-blue.svg)](https://vitejs.dev)
[![ReportLab](https://img.shields.io/badge/PDF_Engine-ReportLab_Quality_Certs_&_Invoices-red.svg)](https://www.reportlab.com)
[![License](https://img.shields.io/badge/Thesis_Project-MSc_Computer_Science-purple.svg)](#)

**OrganicLink** is a full-stack platform designed specifically for the Irish organic agricultural ecosystem. It connects certified Irish organic produce and dairy farmers with commercial buyers (retailers, farm-to-fork restaurants, institutions, aggregators, and consumers) to market surplus yield exceeding fixed processor contracts.

The platform features an automated **5-Step YOLOv8 Two-Stage Computer Vision Quality Engine** combining deep learning classification with computer vision sub-metrics (`colour_vibrancy`, `colour_uniformity`, `brightness`, `defect_coverage_percent`). Quality is evaluated at listing dispatch (`farm` level) and upon arrival (`delivery` level). If quality degrades by more than **10.0%** in transit, an automated dispute is raised, payment is held in escrow, and platform administrators are alerted for binding resolution.

---

## Table of Contents
1. [The Organic Surplus Problem](#the-organic-surplus-problem)
2. [5-Step Bulk Produce Computer Vision Architecture](#5-step-bulk-produce-computer-vision-architecture)
3. [System Architecture & Technology Stack](#system-architecture--technology-stack)
4. [Model Evaluation & Dataset Metrics](#model-evaluation--dataset-metrics)
5. [Key Platform Capabilities](#key-platform-capabilities)
6. [Seeded Demonstration Login Credentials](#seeded-demonstration-login-credentials)
7. [End-to-End Demonstration Walkthrough](#end-to-end-demonstration-walkthrough)
8. [Installation & Setup Instructions](#installation--setup-instructions)
9. [Key Technical & Architectural Decisions](#key-technical--architectural-decisions)

---

## The Organic Surplus Problem

Certified Irish organic farmers operate under strict processor and aggregator contracts. For example:
- A farmer produces **100 kg** of organic tomatoes or apples per month.
- A retail contract commits **80 kg/month** (graded, packed, and delivered to distribution hubs).
- This leaves **20 kg surplus per month** with no direct market channel — traditionally wasted or sold as non-organic.

OrganicLink models this business logic: `Surplus = Produced Yield - Contracted Volume`. The platform automatically alerts farmers to list this surplus yield to local buyers within regional transport range, preserving organic premium value and reducing food waste across Ireland.

---

## 5-Step Bulk Produce Computer Vision Architecture

For bulk produce photos (e.g., crates of apples, tomatoes, potatoes), OrganicLink implements a **Two-Stage YOLOv8 + ResNet-18 Pipeline**:

```
+---------------------------------------------------------------------------------------------------+
|                                5-STEP BULK PRODUCE GRADING PIPELINE                               |
+---------------------------------------------------------------------------------------------------+
|  STEP 1: DETECT                                                                                   |
|  YOLOv8 item localization + Inner 75% Region Shrink (crop_shrink_factor=0.75)                     |
|  Trims 12.5% outer edges off bounding boxes to eliminate neighbouring fruit pixel bleed.           |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|  STEP 2: RECOGNIZE + MATCH                                                                        |
|  Evaluates crop against ResNet-18 Product Classifier. Compares predicted produce against selected |
|  item (e.g. Tomato vs Orange). If mismatch >= 35% confidence, triggers Product Mismatch Rejection. |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|  STEP 3: GRADE                                                                                    |
|  Evaluates matching crops using ResNet-18 Defect Head (fresh, minor_defect, major_defect) +       |
|  OpenCV sub-metrics (colour_vibrancy, colour_uniformity, defect_coverage_percent).                |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|  STEP 4: AGGREGATE                                                                                |
|  Computes batch weighted score: (Fresh*1.0 + Minor*0.6 + Major*0.0) / Matching_Total * 100        |
|  Batch Grade Rules: >= 90% Grade A | >= 75% Grade B | >= 50% Grade C | < 50% Grade R (Rejected).    |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|  STEP 5: RIPENESS & ANNOTATED RENDER                                                              |
|  Summarizes ripeness notes (e.g., Fully-ripe, Semi-ripe for tomatoes) and renders dual-box image  |
|  (Outer detector box: Green=Fresh, Yellow=Minor, Red=Major; Inner white box: 75% crop boundary).   |
+---------------------------------------------------------------------------------------------------+
```

---

## System Architecture & Technology Stack

```
                                    ORGANICLINK SYSTEM ARCHITECTURE

  +---------------------------------------------------------------------------------------------------+
  |                                        REACT 18 + VITE FRONTEND                                   |
  |  Farmer Dashboard | Surplus Assistant | Marketplace Feed | CV Breakdown Panel | Dispute Resolution |
  |  CameraOrUploadInput Component (WebRTC Live Viewfinder Modal + Native File Picker Fallback)       |
  +---------------------------------------------------------------------------------------------------+
                                                      |  HTTP / REST API (Axios + JWT)
                                                      v
  +---------------------------------------------------------------------------------------------------+
  |                                         FASTAPI BACKEND                                           |
  |  /api/auth     | /api/farms        | /api/contracts  | /api/products  | /api/quality | /api/orders  |
  |  /api/payments | /api/ratings      | /api/hubs       | /api/demand    | /api/messages| /api/admin   |
  +---------------------------------------------------------------------------------------------------+
         |                                |                                   |
         v                                v                                   v
  +---------------+              +--------------------+              +--------------------+
  | DATABASE LAYER|              | COMPUTER VISION CV |              | PDF DOCUMENTS SVC  |
  | PostgreSQL 15 |              | PyTorch ResNet-18  |              | ReportLab Engine   |
  | SQLAlchemy 2.0|              | YOLOv8 Detector    |              | Quality Certs      |
  | Optimistic Lock|             | Dynamic Auto-Reload|              | Invoices + Summary |
  +---------------+              +--------------------+              +--------------------+
```

### Core Technologies:
- **Backend Framework**: Python 3.11, FastAPI, SQLAlchemy 2.0, Pydantic v2.
- **Computer Vision & ML**: PyTorch, Torchvision, Ultralytics YOLOv8, OpenCV, ImageHash (Phash De-duplication).
- **Frontend Framework**: React 18, Vite, Tailwind CSS, Lucide Icons, Axios.
- **Document Generation**: ReportLab PDF Engine (Certificates & Invoices).
- **Database**: PostgreSQL 15 / SQLite (Development).

---

## Model Evaluation & Dataset Metrics

The core classifier model (`backend/cv/models/grading_model.pt`) was trained using a **ResNet-18 Dual-Head Architecture** on **48,817 produce images** with a near-duplicate grouped split (`step1_dedupe_split.py`) to prevent train/validation data leakage.

### Validation Results (9,763 Held-Out Images):

| Evaluation Metric | Result | Held-Out Sample |
| :--- | :--- | :--- |
| **Product Classification Accuracy** | **99.33%** | 9,763 Images |
| **Product Macro F1-Score** | **0.9250** | 16 Produce Classes |
| **Quality Grading Accuracy** | **99.40%** | Fresh, Minor Defect, Major Defect |
| **Quality Macro F1-Score** | **0.9898** | Clean Grouped Split |

### Verified Produce Classes (16):
`apple`, `banana`, `bitter_gourd`, `capsicum`, `carrot`, `cucumber`, `grape`, `guava`, `jujube`, `lime`, `mango`, `orange`, `pomegranate`, `potato`, `strawberry`, `tomato`.

---

## Key Platform Capabilities

1. **Dual Camera Options Everywhere (`CameraOrUploadInput.jsx`)**:
   - Every photo upload form (Stock Listing, Farm Inspection, Delivery Inspection, Profile/Certificate Upload) provides side-by-side **Snap Camera 📸** (interactive live WebRTC viewfinder modal) and **Choose File 📁** (native file manager/gallery picker).
2. **Eircode Location Privacy**:
   - Displays exact Irish 3-character Routing Keys (e.g. `T12`) publicly on listings. Exact Eircode bytes are hidden until an order is accepted.
3. **Haversine Distance & Regional Pooled Transport**:
   - Calculates distance in km offline using a 60+ Irish location coordinate database (`seed/irish_locations.py`). Groups orders by county/hub for bulk regional transport runs.
4. **The ±10% Quality Variance Rule**:
   $$\text{Variance \%} = \left( \frac{\text{Farm Score} - \text{Delivery Score}}{\text{Farm Score}} \right) \times 100$$
   - $\le 10.00\%$: **PASS** $\rightarrow$ Order marked `delivered`, invoice PDF generated, payment released.
   - $> 10.00\%$: **DISPUTE** $\rightarrow$ Order marked `disputed`, payment held in escrow, admin dispute raised.
5. **Stock Reservation Concurrency Control**:
   - Uses optimistic locking to prevent double-selling of surplus stock under concurrent buyer claims, returning clean `HTTP 409 Conflict` errors.
6. **ReportLab PDF Certificate & Invoice Engine**:
   - Generates official PDF Quality Certificates (`cert_XXXX.pdf`) and Invoices with embedded CV quality summaries (`inv_XXXX.pdf`).

---

## Seeded Demonstration Login Credentials

All seeded accounts use the standard test password: `Password123!` (Admin uses `Admin123!`).

| Role | Name | Email | Password | Business Detail |
| :--- | :--- | :--- | :--- | :--- |
| **Admin** | System Admin | `admin@organiclink.ie` | `Admin123!` | Dispute resolution queue & platform audit logs |
| **Farmer (Produce)** | Sean O'Mahony | `farmer.cork1@organiclink.ie` | `Password123!` | **Glenbeg Organic Farm (Cork, 100kg yield - 80kg contract = 20kg surplus)** |
| **Retailer** | Bandon Farm Shop | `retail.cork1@organiclink.ie` | `Password123!` | Organic shop / deli commercial buyer (Bandon, Co. Cork) |
| **Farmer (Dairy)** | Aoife Flaherty | `galway.dairy@organic.ie` | `Password123!` | Corrib Organic Dairy (Tuam, Co. Galway) |
| **Farmer (Mixed)** | Liam Ryan | `tipp.produce@organic.ie` | `Password123!` | Golden Vale Organic Produce (Nenagh, Co. Tipperary) |
| **Consumer** | Mary Fitzgerald | `consumer1@organic.ie` | `Password123!` | Individual organic buyer |
| **Restaurant** | Wild Plum Bistro | `rest1@bistro.ie` | `Password123!` | Farm-to-Fork restaurant |
| **Institution** | St. Patrick's College | `inst1@school.ie` | `Password123!` | School canteen bulk buyer |
| **Manufacturer** | Kerry Organic Foods | `mfg1@processor.ie` | `Password123!` | Organic processor / contract holder |

---

## End-to-End Demonstration Walkthrough

1. **Surplus Calculation**:
   - Log in as `farmer.cork1@organiclink.ie` (`Password123!`).
   - Navigate to `/farmer/dashboard`. Review the Surplus Assistant card showing: **"You produced 100kg tomatoes, 80kg is committed — list your 20kg surplus."**

2. **CV Quality Analysis & Stock Listing**:
   - Click **"List Surplus"** (`/farmer/listings/new`).
   - Select **Tomato** from the verified bulk produce dropdown.
   - Click **"Snap Camera 📸"** or **"Choose File 📁"** to load a produce photo.
   - Click **"Run CV Quality Inspection"**. Observe the YOLOv8 5-step analysis, inner 75% crop bounding boxes, and score breakdown.
   - Click **"Publish Certified Surplus Listing"**.

3. **Marketplace Search & Haversine Distance Filter**:
   - Log in as buyer `rest1@bistro.ie` (`Password123!`).
   - Navigate to `/marketplace`. Filter by produce category, county, or distance in km calculated from farm Eircode routing keys.

4. **Order Placement & Stock Reservation**:
   - Select the published produce listing, specify order quantity, and submit order.

5. **Dispatch & Delivery Quality Verification (±10% Rule)**:
   - Farmer uploads dispatch photo $\rightarrow$ order status transitions to `quality_verified` $\rightarrow$ farmer dispatches (`in_transit`).
   - Buyer uploads delivery arrival photo:
     - If variance $\le 10\%$: status becomes `delivered`, invoice PDF is generated.
     - If variance $> 10\%$: status becomes `disputed`, payment held in escrow, admin alerted.

6. **Admin Dispute Resolution Queue**:
   - Log in as `admin@organiclink.ie` (`Admin123!`).
   - Navigate to `/admin`. Review side-by-side dispatch vs delivery photo comparison and score variance.
   - Execute binding resolution with rationale (e.g., Partial Refund or Escrow Release).

---

## Installation & Setup Instructions

### Backend Setup:
```bash
cd backend
python -m venv venv

# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
python -m seed.seed_data
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup:
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5174
```

### Mobile Phone Access:
To test on a mobile device connected to your machine's network/hotspot:
Open Chrome/Safari on your mobile phone and enter:
```text
http://<YOUR_LOCAL_IP>:5174
```

---

## Key Technical & Architectural Decisions

1. **Visual Grading Excluded for Liquid Dairy (Milk)**:
   - Chemical quality indicators for milk (bacterial count, fat/protein content) cannot be measured visually by a camera. OrganicLink uses a per-product flag (`cv_gradable`). Milk listings display **"Visual grading not applicable"** and bypass visual variance checks.
2. **Legal Provenance vs. Visual Grading**:
   - Organic status is a legal certification attribute (IOA/Organic Trust), not a visual property. The CV engine evaluates physical quality (blemishes, rot, discolouration), while organic authenticity is validated via document verification by platform administrators.
3. **Dynamic Model Synchronization**:
   - `backend/cv/inference.py` monitors file modification timestamps on `grading_model.pt`. When background training updates model weights, the FastAPI backend auto-reloads the newest checkpoint without service restart.
4. **Offline Location Resolution**:
   - Eircodes and Irish locations are resolved via an offline lookup module (`seed/irish_locations.py`) covering 60+ Irish towns to ensure complete reliability without third-party API dependencies.

---

### License & Thesis Notice
Developed for MSc Computer Science Thesis. All rights reserved.
