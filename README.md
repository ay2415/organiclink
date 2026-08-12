# OrganicLink: Direct-Trade Organic Agricultural Marketplace & Dual-Inspection Quality Assurance Platform

[![Python 3.13](https://img.shields.io/badge/Backend-Python_3.13_|_FastAPI_|_SQLAlchemy_2.0-green.svg)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/CV_Engine-PyTorch_|_ResNet--18_Multi--Head-orange.svg)](https://pytorch.org)
[![YOLOv8](https://img.shields.io/badge/Object_Detection-YOLOv8_Bulk_Inspection-yellow.svg)](https://ultralytics.com)
[![React 18](https://img.shields.io/badge/Frontend-React_18_|_Vite_|_Tailwind_CSS-blue.svg)](https://vitejs.dev)
[![QR Passport](https://img.shields.io/badge/Traceability-Digital_QR_Produce_Passport-emerald.svg)](#)
[![License](https://img.shields.io/badge/Thesis_Project-MSc_Computer_Science-purple.svg)](#)

**OrganicLink** is an enterprise-grade B2B/B2C agricultural marketplace and computer-vision quality assurance platform built specifically for the Irish organic farming ecosystem. It connects certified Irish organic produce and dairy farmers directly with commercial buyers (retailers, farm-to-fork restaurants, institutions, aggregators, and consumers) to market surplus yields exceeding fixed processor contracts.

The platform integrates a two-stage **YOLOv8 + ResNet-18 Computer Vision Quality Engine**, a **Dual-Inspection Quality Variance Tracking System (±10% transit rule)**, an **Admin Organic Certification Verification Gate**, and an instant **Digital QR Produce Traceability Passport**.

---

## Table of Contents
1. [Platform Overview & Business Model](#platform-overview--business-model)
2. [Key System Capabilities](#key-system-capabilities)
3. [Computer Vision Subsystem Architecture](#computer-vision-subsystem-architecture)
4. [Digital QR Produce Passport & Traceability](#digital-qr-produce-passport--traceability)
5. [System Architecture & Technology Stack](#system-architecture--technology-stack)
6. [Project Directory Layout](#project-directory-layout)
7. [API Endpoint Reference](#api-endpoint-reference)
8. [Frontend Routes & Components](#frontend-routes--components)
9. [Seeded Demonstration Login Credentials](#seeded-demonstration-login-credentials)
10. [Installation & Setup Instructions](#installation--setup-instructions)
11. [Automated Verification & Testing](#automated-verification--testing)

---

## Platform Overview & Business Model

Certified organic farmers in Ireland operate under rigid processor and aggregator contracts. For example:
- A farmer produces **100 kg** of organic tomatoes or apples per month.
- A retail contract commits **80 kg/month** (graded, packed, and delivered to distribution hubs).
- This leaves **20 kg surplus per month** with no direct market channel — traditionally wasted or sold at non-organic prices.

OrganicLink models this business logic: $$\text{Surplus} = \text{Produced Yield} - \text{Contracted Volume}$$

The platform automatically prompts farmers to list surplus yield directly to local buyers within regional transport range, preserving organic premium value, ensuring legal organic verification, and preventing agricultural food waste.

```
+-------------------------------------------------------------------------------------------------------+
|                                    ORGANICLINK END-TO-END WORKFLOW                                    |
+-------------------------------------------------------------------------------------------------------+
|  FARMER REGISTRATION  --> Uploads Organic Cert --> Pending Admin Review (Blocked from Selling)        |
|  ADMIN APPROVAL       --> Admin Reviews Certificate --> APPROVE / REJECT --> Active Seller Status      |
|  LISTING CREATION     --> Upload Produce Photo --> Whole-Image Pre-Check & ResNet/YOLOv8 Grading     |
|  B2B ORDER & NEGOTIATE--> Buyer Places Claim / Negotiates Price & Quantity                            |
|  FARM DISPATCH        --> Farmer Uploads Dispatch Photo --> Farm Inspection Recorded                  |
|  DELIVERY ARRIVAL     --> Buyer Uploads Delivery Photo --> Arrival Inspection & Variance Calc         |
|  AUTOMATED AUDIT      --> Variance <= 10%: RELEASE PAYMENT | Variance > 10%: DISPUTE ESCROW           |
|  QR TRACEABILITY      --> Scan Digital QR Passport for Farm Origin, Cert & 3-Stage Inspection Log     |
+-------------------------------------------------------------------------------------------------------+
```

---

## Key System Capabilities

### 1. Farmer Registration & Admin Approval Gate
- **Mandatory Certificate Upload**: Farmers must upload an organic certificate during registration.
- **Pending Gating**: Accounts are created in a `pending` state, restricting access to seller dashboards, marketplace listing creation, and profile features. A dedicated **"Waiting for Admin Approval"** view (`PendingApproval.jsx`) informs the farmer of their status.
- **Admin Review Queue**: Platform administrators evaluate uploaded certificates in `AdminDashboard.jsx` with explicit **Approve** and **Reject** controls. Approval unlocks active status (`status="verified"`), while rejection keeps the account locked (`status="rejected"`).

### 2. Dual-Inspection Quality Engine & ±10% Transit Variance Rule
- Quality is evaluated twice per transaction: at **Farm Dispatch** (by the seller) and upon **Delivery Arrival** (by the buyer).
- **Quality Variance Calculation**:
  $$\text{Variance \%} = \left( \frac{\text{Farm Score} - \text{Delivery Score}}{\text{Farm Score}} \right) \times 100$$
  - $\le 10.00\%$: **PASS** $\rightarrow$ Order marked `delivered`, invoice PDF generated, payment released.
  - $> 10.00\%$: **DISPUTE** $\rightarrow$ Order marked `disputed`, payment held in escrow, admin arbitration alert triggered.

### 3. Whole-Image Product Mismatch Pre-Check
- Prevents mislabeling fraud in bulk grading. Before localizing item bounding boxes, the whole image is evaluated against the trained product classifier.
- If the predicted produce type disagrees with the user's selected produce (e.g. tomato selected but banana photo uploaded), inspection immediately returns a `Product Mismatch` error and halts grading.

### 4. Concealed Produce Multi-Photo Evaluation
- Supports multi-angle image uploads for listing creation, dispatch inspection, and delivery inspection.
- The inspection engine analyzes every uploaded photo and assigns the **lowest quality score / worst grade** across all angles to ensure conservative quality guarantees.

### 5. Digital QR Code Produce Passport
- Generates downloadable PNG QR codes (`GET /api/traceability/qr`) encoding unique traceability URLs.
- Provides public traceability records (`GET /api/traceability/order/{id}` and `GET /api/traceability/product/{id}`) detailing farm of origin, IOA organic license, listing harvest grade, dispatch timestamp, buyer recipient details, dispatch grade, delivery date, arrival grade, and transit quality variance.

### 6. Dynamic Regional Demand Indicator
- Hybrid 30-day demand engine: computes real-time demand scores ($0-100$) based on active regional orders and marketplace searches. If local activity is low, it seamlessly falls back to Irish seasonal crop baselines.

---

## Computer Vision Subsystem Architecture

The computer vision engine (`backend/cv/`) combines deep learning classification, object detection, and colorimetry:

```
+---------------------------------------------------------------------------------------------------+
|                                5-STEP BULK PRODUCE GRADING PIPELINE                               |
+---------------------------------------------------------------------------------------------------+
|  STEP 1: WHOLE-IMAGE PRODUCT PRE-CHECK                                                            |
|  Evaluates full photo against ResNet-18 Product Classifier. Halts if product mismatch detected.   |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|  STEP 2: DETECT & NMS FILTERING                                                                   |
|  YOLOv8 produce detector localizes individual items. Non-Maximum Suppression (IoU=0.50) drops     |
|  overlapping boxes. Bounding boxes shrunk by 95% inner ratio to prevent neighbor edge bleed.      |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|  STEP 3: MULTI-HEAD QUALITY CLASSIFICATION                                                        |
|  Evaluates crops using ResNet-18 Defect Head (fresh vs defect) + OpenCV HSV color metrics         |
|  (vibrancy, uniformity, brightness, defect coverage).                                             |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|  STEP 4: SCORE & GRADE BANDING AGGREGATION                                                        |
|  Blends 80% neural classifier confidence + 20% OpenCV color metrics.                              |
|  Maps final score to Grade Bands: >= 90% Grade A | >= 75% Grade B | >= 50% Grade C | < 50% Grade R.   |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|  STEP 5: ANNOTATED RENDER & DIAGNOSTICS                                                           |
|  Generates annotated debug bounding box visualization for inspection diagnostics.                 |
+---------------------------------------------------------------------------------------------------+
```

### Verified Produce Classes (14):
`apple`, `banana`, `capsicum`, `carrot`, `cucumber`, `grape`, `guava`, `jujube`, `mango`, `orange`, `pomegranate`, `potato`, `strawberry`, `tomato`.

---

## Digital QR Produce Passport & Traceability

Scanning an OrganicLink QR code directs users to the interactive **Traceability Passport** (`/traceability/:type/:id`), which renders live data directly from the blockchain-ready audit pipeline:

```
+---------------------------------------------------------------------------------------------------+
|                                   DIGITAL PRODUCE PASSPORT (QR)                                   |
+---------------------------------------------------------------------------------------------------+
|  [FARM OF ORIGIN]                                 [ORGANIC CERTIFICATION]                         |
|  Glenbeg Organic Farm                             Irish Organic Association (IOA)                 |
|  Bandon, Co. Cork                                 License: IOA-2026-9841 (Verified)              |
+---------------------------------------------------------------------------------------------------+
|  [1. HARVEST LISTING]           [2. DISPATCH & RECIPIENT]        [3. DELIVERY ARRIVAL]          |
|  Grade: A (94.2/100)            Date: 2026-08-10 09:14           Date: 2026-08-10 14:30         |
|  Photo Verified                 Recipient: Bandon Organic Shop   Grade: A (92.5/100)            |
|                                 Grade: A (93.8/100)              Variance: -1.8% (PASS)         |
+---------------------------------------------------------------------------------------------------+
```

---

## System Architecture & Technology Stack

```
                                    ORGANICLINK SYSTEM ARCHITECTURE

  +---------------------------------------------------------------------------------------------------+
  |                                        REACT 18 + VITE FRONTEND                                   |
  |  Marketplace Feed | Farmer Dashboard | Buyer Dashboard | Admin Arbitration | Traceability Passport |
  |  CameraOrUploadInput Component (Live WebRTC Viewfinder Modal + Native File Picker Fallback)       |
  +---------------------------------------------------------------------------------------------------+
                                                      |  HTTP / REST API (Axios + JWT)
                                                      v
  +---------------------------------------------------------------------------------------------------+
  |                                         FASTAPI BACKEND                                           |
  |  /api/auth     | /api/farms        | /api/contracts  | /api/products  | /api/quality | /api/orders  |
  |  /api/payments | /api/ratings      | /api/hubs       | /api/demand    | /api/messages| /api/admin   |
  |  /api/delivery | /api/production   | /api/traceability| /api/profile                               |
  +---------------------------------------------------------------------------------------------------+
         |                                |                                   |
         v                                v                                   v
  +---------------+              +--------------------+              +--------------------+
  | DATABASE LAYER|              | COMPUTER VISION CV |              | PDF DOCUMENTS SVC  |
  | SQLite (dev)  |              | PyTorch ResNet-18  |              | ReportLab Engine   |
  | / PostgreSQL  |              | YOLOv8 Detector    |              | Quality Certs      |
  | SQLAlchemy 2.0|              | Dynamic Auto-Reload|              | Invoices + Summary |
  +---------------+              +--------------------+              +--------------------+
```

### Core Technologies
- **Backend Framework**: Python 3.13, FastAPI, SQLAlchemy 2.0, Pydantic v2.
- **Computer Vision & ML**: PyTorch, Torchvision (ResNet-18), Ultralytics YOLOv8, OpenCV.
- **Frontend Framework**: React 18, Vite 4, TailwindCSS 3, Lucide React Icons, Axios, React Router v6.
- **Document Generation**: ReportLab PDF Engine (Certificates & Invoices).
- **Database**: SQLite by default for local development (`backend/organiclink.db`); PostgreSQL supported via `DATABASE_URL` / Docker Compose.

---

## Project Directory Layout

```
organiclink/
├── backend/                      FastAPI Application Root
│   ├── main.py                   Lifespan application entrypoint & middleware configuration
│   ├── config.py                 Pydantic SettingsConfigDict (DB URL, JWT, constants)
│   ├── database.py                SQLAlchemy engine and session factory
│   ├── models/
│   │   └── all_models.py         SQLAlchemy database schemas (User, Farm, Order, Inspection, etc.)
│   ├── schemas/
│   │   └── schemas.py            Pydantic v2 request/response schemas with ConfigDict
│   ├── routers/                  18 REST API route modules
│   ├── services/                 Audit, demand scoring, geo/Haversine, PDF doc generator, reputation
│   ├── cv/
│   │   ├── inference.py           ResNet-18 multi-head inference engine
│   │   ├── detection.py           YOLOv8 produce detector integration
│   │   ├── grading.py             Quality score computation & probability calibration
│   │   ├── bulk_grading.py        Two-stage bulk inspection pipeline & product mismatch pre-check
│   │   └── models/                Trained weights: grading_model.pt, produce_detector.pt
│   ├── seed/                     Data seed scripts & 60+ Irish location coordinate database
│   ├── uploads/                   Runtime uploaded media & generated PDF files
│   ├── tests/
│   │   └── test_organiclink.py    Pytest automated test suite
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                     React 18 + Vite SPA Frontend
│   ├── src/
│   │   ├── pages/                19 route-level pages (Marketplace, Dashboards, Traceability, etc.)
│   │   ├── components/           Shared components (CameraOrUploadInput, CVBreakdownPanel, GradeBadge)
│   │   ├── context/AuthContext.jsx JWT authentication context provider
│   │   ├── api/axios.js          Axios instance with Bearer token interceptors
│   │   └── App.jsx               React Router configuration with PendingApproval guards
│   ├── package.json
│   └── Dockerfile
├── unused_files/                  Archived temporary files and historical test scripts
├── docker-compose.yml            Multi-container deployment config
└── README.md                     Platform documentation
```

---

## API Endpoint Reference

All routes are served under `/api` by FastAPI (interactive OpenAPI docs available at `/docs` and `/redoc`).

| Router File | Route Prefix | Primary Endpoints & Operations |
| :--- | :--- | :--- |
| `auth.py` | `/api/auth` | `/register` (with cert upload), `/login`, `/me` |
| `admin.py` | `/api/admin` | `/farms` (verify/reject queue), `/disputes`, `/audit-logs`, `/settings` |
| `farms.py` | `/api/farms` | Farm CRUD, certification management, production history |
| `products.py` | `/api` | `/marketplace`, `/farms/{id}/products`, product price/status updates |
| `quality.py` | `/api/quality` | Single/bulk CV inspection execution, certificate retrieval |
| `orders.py` | `/api/orders` | Order creation, accept/reject, price negotiation, dispatch/delivery photo uploads |
| `traceability.py` | `/api/traceability` | `/qr` (PNG generator), `/product/{id}`, `/order/{id}` (traceability passport) |
| `payments.py` | `/api/payments` | Payment listing, escrow release, invoice PDF download |
| `ratings.py` | `/api` | Star rating creation, reputation score updates |
| `hubs.py` / `local_hubs.py` | `/api/hubs` | Regional hub directory, nearest hub locator |
| `demand.py` | `/api/demand` | 30-day regional demand indicator |
| `messages.py` | `/api/messages` | Direct buyer-farmer messaging & thread history |
| `notifications.py` | `/api/notifications` | User notification feed |
| `profile.py` | `/api/profile` | Own profile management, farmer cert upload |
| `delivery.py` | `/api/delivery` | Delivery rules, delivery slots, regional pooled runs |

---

## Frontend Routes & Components

**Routes Table** (`frontend/src/App.jsx`):

| Path | Page Component | Audience & Gating |
| :--- | :--- | :--- |
| `/`, `/marketplace` | `Marketplace` | Public / All users |
| `/product/:id` | `ProductDetail` | Public / All users |
| `/farm/:id` | `FarmProfile` | Public / All users |
| `/login`, `/register` | `Login`, `Register` | Public |
| `/pending-approval` | `PendingApproval` | Unapproved farmers (Pending/Rejected screen) |
| `/profile`, `/users/:id` | `Profile`, `PublicProfile` | Authenticated users (Blocked for pending farmers) |
| `/farmer/dashboard` | `FarmerDashboard` | Approved Farmers only |
| `/farmer/listings/new` | `FarmerNewListing` | Approved Farmers only |
| `/farmer/production`, `/contracts`, `/hubs`, `/sales-history` | `FarmerProduction`, `FarmerContracts`, `FarmerHubs`, `FarmerSalesHistory` | Approved Farmers only |
| `/buyer/dashboard` | `BuyerDashboard` | Buyers (Retailers, Restaurants, Consumers) |
| `/orders/:id` | `OrderDetail` | Farmer & Buyer transaction participants |
| `/traceability/:type/:id` | `Traceability` | Public Digital QR Produce Passport |
| `/admin` | `AdminDashboard` | Platform Administrators |

---

## Seeded Demonstration Login Credentials

All seeded accounts use password `Password123!` (Admin uses `Admin123!`).

| Role | Name | Email | Password | Primary Feature / Detail |
| :--- | :--- | :--- | :--- | :--- |
| **Admin** | System Admin | `admin@organiclink.ie` | `Admin123!` | Farm verification queue (Approve/Reject), Dispute arbitration |
| **Farmer (Produce)** | Sean O'Mahony | `farmer.cork1@organiclink.ie` | `Password123!` | **Glenbeg Organic Farm (Cork, 20kg surplus active)** |
| **Retailer** | Bandon Farm Shop | `retail.cork1@organiclink.ie` | `Password123!` | Commercial organic deli buyer (Bandon, Co. Cork) |
| **Farmer (Dairy)** | Aoife Flaherty | `galway.dairy@organic.ie` | `Password123!` | Corrib Organic Dairy (Tuam, Co. Galway) |
| **Farmer (Mixed)** | Liam Ryan | `tipp.produce@organic.ie` | `Password123!` | Golden Vale Organic Produce (Nenagh, Co. Tipperary) |
| **Restaurant** | Wild Plum Bistro | `rest1@bistro.ie` | `Password123!` | Farm-to-Fork restaurant buyer |
| **Consumer** | Mary Fitzgerald | `consumer1@organic.ie` | `Password123!` | Individual organic consumer |
| **Institution** | St. Patrick's College | `inst1@school.ie` | `Password123!` | Institutional canteen buyer |
| **Manufacturer** | Kerry Organic Foods | `mfg1@processor.ie` | `Password123!` | Processor / contract holder |

---

## Installation & Setup Instructions

### Prerequisites
- Python 3.11+ (Python 3.13 recommended)
- Node.js 18+ and npm
- Git

### 1. Backend Setup
```bash
cd backend

# Create & activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt

# Seed demonstration database with Irish farms, locations, and sample products
python -m seed.seed_data

# Start FastAPI development server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
*Note: The backend automatically creates a local SQLite database (`backend/organiclink.db`) on startup. No external database configuration is needed for local development.*

### 2. Frontend Setup
```bash
cd frontend

# Install frontend dependencies
npm install

# Start Vite development server
npm run dev -- --host 0.0.0.0 --port 5174
```
Vite automatically proxies `/api` and `/static` requests to `http://127.0.0.1:8000`.

Access the application in your browser at: `http://localhost:5174`

---

## Automated Verification & Testing

To run the complete backend test suite:
```bash
python -m pytest backend/tests/test_organiclink.py
```

To build the frontend for production:
```bash
npm --prefix frontend run build
```

---

### License & Thesis Notice
Developed for MSc Computer Science Thesis. All rights reserved.
