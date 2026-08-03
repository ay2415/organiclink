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
2. [Project Structure](#project-structure)
3. [5-Step Bulk Produce Computer Vision Architecture](#5-step-bulk-produce-computer-vision-architecture)
4. [System Architecture & Technology Stack](#system-architecture--technology-stack)
5. [Model Evaluation & Dataset Metrics](#model-evaluation--dataset-metrics)
6. [Key Platform Capabilities](#key-platform-capabilities)
7. [API Reference](#api-reference)
8. [Frontend Routes & Components](#frontend-routes--components)
9. [Seeded Demonstration Login Credentials](#seeded-demonstration-login-credentials)
10. [End-to-End Demonstration Walkthrough](#end-to-end-demonstration-walkthrough)
11. [Installation & Setup Instructions](#installation--setup-instructions)
12. [Key Technical & Architectural Decisions](#key-technical--architectural-decisions)
13. [Known Gaps](#known-gaps)

---

## The Organic Surplus Problem

Certified Irish organic farmers operate under strict processor and aggregator contracts. For example:
- A farmer produces **100 kg** of organic tomatoes or apples per month.
- A retail contract commits **80 kg/month** (graded, packed, and delivered to distribution hubs).
- This leaves **20 kg surplus per month** with no direct market channel — traditionally wasted or sold as non-organic.

OrganicLink models this business logic: `Surplus = Produced Yield - Contracted Volume`. The platform automatically alerts farmers to list this surplus yield to local buyers within regional transport range, preserving organic premium value and reducing food waste across Ireland.

---

## Project Structure

```
organiclink/
├── backend/                      FastAPI application
│   ├── main.py                   App entrypoint, CORS, startup CV engine init, /api/health
│   ├── config.py                 Pydantic Settings (DB URL, JWT, variance/commission constants)
│   ├── database.py                SQLAlchemy engine/session/Base
│   ├── models/all_models.py       20 SQLAlchemy models (User, Farm, Product, Order, ...)
│   ├── schemas/schemas.py         Pydantic v2 request/response schemas
│   ├── routers/                   17 route modules (see API Reference)
│   ├── services/                  audit, demand scoring, geo/Haversine, PDF docs, reputation
│   ├── cv/
│   │   ├── inference.py           ResNet-18 dual-head grading engine, hot-reloads on file mtime
│   │   ├── detection.py           YOLOv8 produce detector (ultralytics)
│   │   ├── grading.py             Quality score, grade thresholds, variance calibration
│   │   ├── bulk_grading.py        Two-stage bulk pipeline (detect → match → grade → aggregate)
│   │   ├── train.py / train_v7.py Classifier training pipelines
│   │   ├── models/                Checkpoints: grading_model.pt, produce_detector.pt, eval reports
│   │   ├── models_backup/         Backup checkpoint (kept in git)
│   │   ├── debug/                 Runtime annotated debug images (detection/bulk grading)
│   │   └── data/, quality dataset/  Training data (git-ignored)
│   ├── seed/                      seed_data.py, irish_locations.py (60+ towns), clean_dummy.py
│   ├── uploads/                   Runtime-generated images & PDFs (git-ignored)
│   ├── tests/test_organiclink.py  Pytest suite
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                     React 18 + Vite + Tailwind SPA
│   ├── src/
│   │   ├── pages/                17 route-level pages (see Frontend Routes & Components)
│   │   ├── components/           Navbar, Footer, CameraOrUploadInput, CVBreakdownPanel, GradeBadge, VarianceBadge
│   │   ├── context/AuthContext.jsx  JWT auth via React Context + localStorage
│   │   ├── api/axios.js          Axios instance, Bearer token interceptor
│   │   └── App.jsx               Route table
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml            postgres + backend + frontend services
├── .env.example                  Environment variable template
├── PROJECT_STATUS.md              Function-level feature audit (file:line references)
├── scratch/                       Ad-hoc dev/debug scripts (not part of the app)
└── unused_files/                  Archived/dead code and DB backups (not part of the app)
```

---

## 5-Step Bulk Produce Computer Vision Architecture

For bulk produce photos (e.g., crates of apples, tomatoes, potatoes), OrganicLink implements a **Two-Stage YOLOv8 + ResNet-18 Pipeline** (`backend/cv/bulk_grading.py`, `backend/cv/detection.py`):

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

An IOU-based overlap filter (`compute_iou` / `filter_overlapping_boxes` in `bulk_grading.py`) removes duplicate/overlapping detector boxes before grading. Overlapping raw detections are written for inspection to `backend/cv/debug/detection_debug.jpg` and the final annotated batch result to `backend/cv/debug/bulk_grading_annotated.jpg`.

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
  | SQLite (dev)  |              | PyTorch ResNet-18  |              | ReportLab Engine   |
  | / PostgreSQL 15|             | YOLOv8 Detector    |              | Quality Certs      |
  | Optimistic Lock|             | Dynamic Auto-Reload|              | Invoices + Summary |
  +---------------+              +--------------------+              +--------------------+
```

### Core Technologies:
- **Backend Framework**: Python 3.11, FastAPI, SQLAlchemy 2.0, Pydantic v2.
- **Computer Vision & ML**: PyTorch, Torchvision (ResNet-18), Ultralytics YOLOv8, OpenCV.
- **Frontend Framework**: React 18, Vite, Tailwind CSS, Lucide Icons, Chart.js, Axios.
- **Document Generation**: ReportLab PDF Engine (Certificates & Invoices).
- **Database**: SQLite by default for local development (`backend/organiclink.db`); PostgreSQL 15 via `DATABASE_URL` / Docker Compose for production-like setups. SQLAlchemy migrations managed with Alembic.

---

## Model Evaluation & Dataset Metrics

The production classifier (`backend/cv/models/grading_model.pt`) uses a **ResNet-18 Dual-Head Architecture** trained on **48,817 produce images** with a near-duplicate grouped split (`step1_dedupe_split.py`) to prevent train/validation data leakage.

### Validation Results (9,763 Held-Out Images) — active production model:

| Evaluation Metric | Result | Held-Out Sample |
| :--- | :--- | :--- |
| **Product Classification Accuracy** | **99.33%** | 9,763 Images |
| **Product Macro F1-Score** | **0.9250** | 16 Produce Classes |
| **Quality Grading Accuracy** | **99.40%** | Fresh, Minor Defect, Major Defect |
| **Quality Macro F1-Score** | **0.9898** | Clean Grouped Split |

### Verified Produce Classes (16):
`apple`, `banana`, `bitter_gourd`, `capsicum`, `carrot`, `cucumber`, `grape`, `guava`, `jujube`, `lime`, `mango`, `orange`, `pomegranate`, `potato`, `strawberry`, `tomato`.

> Note: `bitter_gourd` has zero support in the current held-out validation split — treat its per-class metrics as unverified until more labelled samples are added.

### In-progress retraining run (`train_v7.py`, 2026-08-01):
A second training pipeline is being evaluated against an alternate, larger source dataset ("Fruit And Vegetable Diseases Dataset", 29,291 usable images, 14 classes, binary `fresh`/`defect` quality labels instead of the 3-way fresh/minor/major split). Best checkpoint so far: epoch 13 (`grading_model_2026-08-01_ep13.pt`), 97.38% val / 96.79% held-out test product accuracy, 98.18% val / 98.29% test quality accuracy. **This checkpoint has not been promoted to `grading_model.pt`** — it is a candidate under evaluation, not the model currently served by the API.

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

## API Reference

All routes are served under `/api` by FastAPI (interactive docs at `/docs` and `/redoc`). `GET /api/health` returns service status.

| Router | Prefix | Purpose |
| :--- | :--- | :--- |
| `auth.py` | `/api/auth` | Register, login, `GET /me` |
| `farms.py` | `/api/farms` | Farm CRUD, certification, production logs, sales history, surplus suggestion |
| `contracts.py` | `/api` | Processor contract CRUD per farm |
| `products.py` | `/api` | Listings CRUD, price updates, `GET /marketplace` |
| `quality.py` | `/api/quality` | Run CV inspection, fetch inspection results/certificate |
| `orders.py` | `/api/orders` | Order lifecycle: create, accept/reject/negotiate/dispatch, dispatch/delivery photo uploads, payment send/receive |
| `payments.py` | `/api/payments` | List payments, mark paid, fetch invoice PDF |
| `ratings.py` | `/api` | Post ratings, farm rating list, user reputation |
| `hubs.py` / `local_hubs.py` | `/api/hubs` | Hub directory, nearest hub, collection points |
| `demand.py` | `/api/demand` | Regional demand signal |
| `messages.py` | `/api/messages` | Direct messaging, conversation threads, read receipts |
| `notifications.py` | `/api/notifications` | User notifications feed |
| `admin.py` | `/api/admin` | Farm verification, dispute queue/resolution, platform metrics, audit logs, settings |
| `production_logs.py` | `/api/production-logs` | Daily/bulk production logging, surplus calculation |
| `delivery.py` | `/api/delivery` | Delivery rules, slots, regional delivery runs |
| `profile.py` | `/api` | Own profile edit/photo/certificate, public profile view |

---

## Frontend Routes & Components

**Routes** (`frontend/src/App.jsx`, React Router v6):

| Path | Page | Audience |
| :--- | :--- | :--- |
| `/`, `/marketplace`, `/product/:id`, `/farm/:id` | `Marketplace`, `ProductDetail`, `FarmProfile` | Public/all |
| `/login`, `/register` | `Login`, `Register` | Public |
| `/profile`, `/users/:id` | `Profile`, `PublicProfile` | Authenticated |
| `/farmer/dashboard`, `/production`, `/contracts`, `/listings/new`, `/hubs`, `/sales-history` | `FarmerDashboard`, `FarmerProduction`, `FarmerContracts`, `FarmerNewListing`, `FarmerHubs`, `FarmerSalesHistory` | Farmer |
| `/buyer/dashboard` | `BuyerDashboard` | Buyer |
| `/orders/:id` | `OrderDetail` | Farmer & buyer |
| `/messages` | `Messages` | All authenticated |
| `/admin` | `AdminDashboard` | Admin |

**Shared components**: `CameraOrUploadInput` (WebRTC camera + file picker), `CVBreakdownPanel` (CV score breakdown), `GradeBadge` (A/B/C/R badge), `VarianceBadge` (farm-vs-delivery variance indicator), `Navbar`, `Footer`.

**Auth/API**: `AuthContext` stores the JWT in `localStorage` (`organiclink_token`), hydrates the current user via `GET /api/auth/me` on load. `api/axios.js` attaches the bearer token to every request and proxies through Vite to the backend during development.

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

### Option A — Local (SQLite, fastest for development)

**Backend:**
```bash
cd backend
python -m venv venv

# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
pip install ultralytics>=8.0.0   # YOLOv8 detector — required by cv/detection.py, not yet in requirements.txt
python -m seed.seed_data
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
No `.env` file is required for this option — `config.py` defaults `DATABASE_URL` to a local `organiclink.db` SQLite file.

**Frontend:**
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5174
```
Vite proxies `/api` and `/static` to `http://127.0.0.1:8000`, so the frontend and backend must both be running.

### Option B — Docker Compose (PostgreSQL)
```bash
docker compose up --build
```
Starts `postgres` (5432), `backend` (8000), and `frontend` (5173) with the database URL wired to the Postgres container. Copy `.env.example` to `.env` and adjust `SECRET_KEY` before any non-local use.

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

## Known Gaps

- `ultralytics` (YOLOv8) is imported by `backend/cv/detection.py` but is missing from `backend/requirements.txt` — install it manually as shown above until the requirements file is updated.
- The `train_v7.py` retraining run (2026-08-01, epoch 13/14 checkpoints) uses a different dataset, class list, and a binary quality label scheme; it is a candidate under evaluation and has **not** been promoted to the production `grading_model.pt`.
- `scratch/` and `unused_files/` contain ad-hoc debug scripts and archived/dead code respectively — neither is part of the running application.

---

### License & Thesis Notice
Developed for MSc Computer Science Thesis. All rights reserved.
