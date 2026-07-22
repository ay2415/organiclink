# OrganicLink — Irish Organic Farm Surplus Marketplace with Computer Vision Quality Grading

[![Python 3.11](https://img.shields.io/badge/Backend-Python_3.11_|_FastAPI_|_SQLAlchemy_2.0-green.svg)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/CV_Engine-PyTorch_|_EfficientNet--B0_|_OpenCV-orange.svg)](https://pytorch.org)
[![React 18](https://img.shields.io/badge/Frontend-React_18_|_Vite_|_Tailwind_CSS-blue.svg)](https://vitejs.dev)
[![Docker](https://img.shields.io/badge/Deployment-Docker_Compose-blue.svg)](https://www.docker.com)

OrganicLink is a full-stack platform designed specifically for the Irish organic agricultural ecosystem. It connects certified Irish organic produce and dairy farmers with local buyers (consumers, retailers, farm-to-fork restaurants, institutions, and processors) to market surplus yield that exceeds fixed processor contracts.

The platform integrates a **Computer Vision (CV) Quality Engine** built on PyTorch (`EfficientNet-B0` backbone) and OpenCV. Produce quality is assessed at listing dispatch (`farm` level) and again upon arrival (`delivery` level). If quality degrades by more than **10.0%** in transit, an automated dispute is raised, payment is held in escrow, and platform administrators are notified for binding dispute resolution.

---

## The Organic Surplus Problem

Irish organic farmers face strict processor contracts. For example:
- A farmer produces **100 kg** of organic onions per month.
- A retail aggregator contract commits **80 kg/month** (branded, bagged, and distributed to supermarkets).
- This leaves **20 kg surplus per month** with no direct market channel — traditionally wasted or downgraded and sold cheaply as non-organic.

OrganicLink models this exact business rule: `Surplus = Produced Yield - Contracted Volume`. The platform automatically suggests listing this 20 kg surplus to local buyers, preserving organic premium value and reducing food waste across Ireland.

---

## Technical Architecture

```
                                    ORGANICLINK SYSTEM ARCHITECTURE
                                    
  +---------------------------------------------------------------------------------------------------+
  |                                        REACT 18 + VITE FRONTEND                                   |
  |  Farmer Dashboard | Surplus Assistant | Marketplace Feed | CV Breakdown Panel | Dispute Resolution |
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
  | PostgreSQL 15 |              | PyTorch EffNet-B0  |              | ReportLab Engine   |
  | SQLAlchemy 2.0|              | OpenCV Sub-metrics |              | Quality Certs      |
  | Alembic Migr. |              | Dual-Grade Variance|              | Invoices + Summary |
  +---------------+              +--------------------+              +--------------------+
```

---

## Features & Core Capabilities

- **Organic Certification as First-Class Concept:** Every farm profile, product card, and PDF document embeds verified Irish organic certification details (IOA / Organic Trust).
- **Offline Irish Geo & Haversine Distance:** Offline lookup table covering 60+ Irish towns and Eircode routing keys (`seed/irish_locations.py`) calculating exact distance in km without third-party paid APIs.
- **Dual-Inspection CV Quality Grading:** PyTorch transfer-learning classifier combined with OpenCV visual sub-metrics (`colour_vibrancy`, `colour_uniformity`, `brightness`, `defect_coverage_percent`).
- **Listing Gate Enforcement:** Produce of Grade A (≥85), B (70–84), or C (50–69) is accepted. Grade R (<50) is automatically rejected at listing time with explanatory defect feedback.
- **The ±10% Quality Variance Rule:**
  $$\text{Variance \%} = \left( \frac{\text{Farm Score} - \text{Delivery Score}}{\text{Farm Score}} \right) \times 100$$
  - $\le 10.00\%$: **PASS** $\rightarrow$ Order marked `delivered`, invoice generated, payment pending.
  - $> 10.00\%$: **DISPUTE** $\rightarrow$ Order marked `disputed`, payment held in escrow, admin notified.
- **Hybrid Market Demand Indicator:** Uses real 30-day activity (searches + orders $\ge 5$) for live demand scores, or falls back to an Irish seasonal growing baseline with an explicit **"Seasonal estimate"** tag in the UI.
- **Farmer Reputation Formula:**
  $$\text{Reputation} = 0.40(\text{Stars} \times 20) + 0.30(\text{Mean Quality}) + 0.20(\text{On-Time \%}) + 0.10(100 - \text{Dispute \%})$$
- **Immutable Audit Logging:** Insert-only `audit_logs` table tracking every state machine transition.

---

## Computer Vision Training & Evaluation

The CV model is trained using PyTorch with an `EfficientNet-B0` backbone pretrained on ImageNet. Early layers are frozen, and the final classification head is retrained on three target classes: `fresh`, `minor_defect`, `major_defect`.

If no dataset is present, `backend/cv/train.py` automatically generates a synthetic bootstrap produce dataset (900 images across classes with varying defect spot coverage) so the system runs immediately.

### Model Evaluation Report Location
- `backend/cv/models/eval_report.json`
- `backend/cv/models/eval_report.txt`

### Swapping Synthetic Bootstrap for Real Produce Dataset
To train on a real produce dataset (e.g., Kaggle Fresh & Rotten Fruits/Vegetables):
1. Place labeled images into `backend/cv/data/train/{fresh,minor_defect,major_defect}/` and `backend/cv/data/val/{fresh,minor_defect,major_defect}/`.
2. Run the training script:
   ```bash
   python backend/cv/train.py
   ```
3. The new weights (`quality_model.pt`) and evaluation report will be updated automatically.

---

## Seeded Login Credentials

All non-admin users share the password: `Password123!`

| Role | Name | Email | Password | Details |
|------|------|-------|----------|---------|
| **Admin** | System Admin | `admin@organiclink.ie` | `Admin123!` | Dispute resolution queue & audit logs |
| **Farmer (Onion)** | Sean O'Mahony | `farmer@corkorganic.ie` | `Password123!` | **Glenbeg Organic Farm (100kg yield - 80kg contract = 20kg surplus)** |
| **Farmer (Dairy)** | Aoife Flaherty | `galway.dairy@organic.ie` | `Password123!` | Corrib Organic Dairy (Tuam, Co. Galway) |
| **Farmer (Mixed)** | Liam Ryan | `tipp.produce@organic.ie` | `Password123!` | Golden Vale Organic Produce (Nenagh, Co. Tipperary) |
| **Consumer** | Mary Fitzgerald | `consumer1@organic.ie` | `Password123!` | Small volume individual buyer |
| **Retailer** | Bandon Farm Shop | `retail1@farmshop.ie` | `Password123!` | Organic shop / deli buyer |
| **Restaurant** | Wild Plum Bistro | `rest1@bistro.ie` | `Password123!` | Farm-to-Fork restaurant |
| **Institution** | St. Patrick's College | `inst1@school.ie` | `Password123!` | School canteen bulk buyer |
| **Manufacturer** | Kerry Organic Foods | `mfg1@processor.ie` | `Password123!` | Processor / contract holder |

---

## Demo Walkthrough Instructions

1. **Surplus Calculation:**
   - Log in as `farmer@corkorganic.ie` (`Password123!`).
   - Navigate to `/farmer/dashboard`. Observe the Surplus Assistant card showing: **"You produced 100kg onions, 80kg is committed — list your 20kg surplus."**

2. **CV Produce Quality Listing:**
   - Click **"List Surplus"** or navigate to `/farmer/listings/new`.
   - Select an image. Click **"Run Instant CV Quality Analysis"**.
   - Review the CV score, grade, and OpenCV sub-metrics breakdown panel. Click **"Publish Certified Surplus Listing"**.

3. **Marketplace & Haversine Distance Search:**
   - Log in as a buyer (`rest1@bistro.ie`).
   - Navigate to `/marketplace`. Filter by product type, county, or distance. Notice distance in km computed from farm Eircodes.

4. **Order Negotiation & State Machine:**
   - Select a produce listing, fill out the order form, and click **"Place Surplus Order"**.
   - Negotiate a counter-offer or accept as farmer.

5. **Dispatch & Delivery Photo Quality Audit (±10% Rule):**
   - **Quality Gate:** Attempting to dispatch without a farm photo returns HTTP 409 Conflict.
   - Farmer uploads dispatch photo $\rightarrow$ order status becomes `quality_verified` $\rightarrow$ farmer dispatches (`in_transit`).
   - Buyer uploads delivery photo:
     - If variance $\le 10\%$: status becomes `delivered`, invoice PDF is generated.
     - If variance $> 10\%$: status becomes `disputed`, payment is held, and an open dispute is raised.

6. **Admin Dispute Resolution:**
   - Log in as `admin@organiclink.ie` (`Admin123!`).
   - Navigate to `/admin`. Review the open dispute displaying side-by-side farm vs delivery photos and score comparison.
   - Select resolution (e.g. Partial Payment), enter rationale, and click **"Execute Binding Dispute Resolution"**.

---

## Setup & Running the Application

### Option 1: Docker Compose (Recommended)

```bash
# Build and launch PostgreSQL, Backend, and Frontend containers
docker-compose up --build
```
- **Backend OpenAPI Docs:** `http://localhost:8000/docs`
- **Frontend App:** `http://localhost:5173`

### Option 2: Local Development Setup

#### Backend:
```bash
cd backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
python -m seed.seed_data
uvicorn main:app --reload --port 8000
```

#### Frontend:
```bash
cd frontend
npm install
npm run dev
```

#### Automated Tests:
```bash
cd backend
pytest -v
```

---

## Key Design Decisions & Assumptions

1. **Offline Irish Geo Lookup:** To guarantee 100% reliability without third-party API rate limits, Eircodes and Irish town names are geocoded using an offline lookup dictionary covering 60+ locations (`seed/irish_locations.py`).
2. **Synthetic CV Dataset Bootstrap:** If pretrained Kaggle weights are absent on first clone, the backend automatically programmatically generates synthetic produce blob images with dark defect spots, trains an EfficientNet-B0 model, and saves `eval_report.txt` and `eval_report.json`.
3. **Escrow Payment Holding:** Payment records default to `platform_mock` and status `held` during disputes. Invoices embed both farm and delivery quality grades along with the exact variance percentage.
