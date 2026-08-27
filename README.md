# OrganicLink: A Computer-Vision Marketplace for Irish Organic Producers with Automated Produce Quality Grading

[![Python 3.13](https://img.shields.io/badge/Backend-Python_3.13_|_FastAPI_|_SQLAlchemy_2.0-green.svg)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/CV_Engine-PyTorch_|_ResNet--18_Multi--Head-orange.svg)](https://pytorch.org)
[![YOLOv8](https://img.shields.io/badge/Object_Detection-YOLOv8_Bulk_Inspection-yellow.svg)](https://ultralytics.com)
[![React 18](https://img.shields.io/badge/Frontend-React_18_|_Vite_|_Tailwind_CSS-blue.svg)](https://vitejs.dev)
[![QR Passport](https://img.shields.io/badge/Traceability-Digital_QR_Produce_Passport-emerald.svg)](#)
[![UL MEng Project](https://img.shields.io/badge/MEng-Computer_Vision_&_AI_|_University_of_Limerick-purple.svg)](#)

---

### Project Metadata
* **Full Title**: OrganicLink: A Computer-Vision Marketplace for Irish Organic Producers with Automated Produce Quality Grading
* **Author**: Aashrith Sai Yamsani (Student ID: 25287419)
* **Degree**: MEng in Computer Vision and Artificial Intelligence
* **Module**: LK489  Master of Engineering in Computer Vision and Artificial Intelligence Master's Project
* **Institution**: University of Limerick
* **Supervisors**: Dr. Elfed Lewis (CE6013), Dr. Annmarie Ryan (Digital Futures Lab)

---

## Executive Summary

**OrganicLink** is a full-stack web marketplace and computer-vision quality-assessment platform engineered specifically for the Irish organic agricultural sector. It connects certified Irish organic farmers directly with commercial buyers (retailers, farm-to-fork restaurants, institutions, aggregators) and direct consumers to enable transparent trade of surplus yields exceeding fixed processor contracts.

The platform directly eliminates the central trust barrier in remote produce transactions—the impossibility of verifying produce quality and freshness at a distance. OrganicLink solves this through an end-to-end technological pipeline:
1. **Dual-Inspection Quality Variance Protocol**: Grades produce at both **Dispatch** (farmer) and **Delivery Arrival** (buyer) using the identical multi-head ResNet-18 model to automatically detect in-transit quality drops with objective visual evidence.
2. **Two-Stage Bulk Produce Grading**: Combines fine-tuned YOLOv8 bounding-box detection with ResNet-18 crop grading to evaluate multi-item crates and baskets without condemning entire batches for single blemished items.
3. **Hybrid Quality Scoring (80:20)**: Blends deep-learning defect probability (80%) with classical OpenCV colour saturation and uniformity metrics (20%) for robust, physically grounded grades (A, B, C, R).
4. **Data Leakage Control**: Employs perceptual hashing (pHash) to isolate 34.7% near-duplicate contamination across datasets into disjoint grouped splits, verifying true model generalization.
5. **Organic Provenance Verification**: Implements an administrative certification gate for IOA / Organic Trust licenses, combined with an instant **Digital QR Produce Traceability Passport**.

---

## Table of Contents
1. [The Irish Organic Agricultural Problem](#the-irish-organic-agricultural-problem)
2. [Core Platform Features & Business Logic](#core-platform-features--business-logic)
3. [Computer Vision & Hybrid Grading Engine](#computer-vision--hybrid-grading-engine)
4. [Dual-Inspection Quality Variance Protocol](#dual-inspection-quality-variance-protocol)
5. [Two-Stage Bulk Produce Grading Pipeline](#two-stage-bulk-produce-grading-pipeline)
6. [Dataset Quality & Perceptual Hashing Leakage Control](#dataset-quality--perceptual-hashing-leakage-control)
7. [Digital QR Produce Passport & Traceability](#digital-qr-produce-passport--traceability)
8. [System Architecture & Technology Stack](#system-architecture--technology-stack)
9. [Project Directory Layout](#project-directory-layout)
10. [API Endpoint Reference](#api-endpoint-reference)
11. [Frontend Routes & Components](#frontend-routes--components)
12. [Demonstration Login Credentials](#demonstration-login-credentials)
13. [Installation & Setup Guide](#installation--setup-guide)

---

## The Irish Organic Agricultural Problem

Despite rapid expansion targets under the Irish Climate Action Plan to scale organic farmland, small and regional organic producers encounter critical market-access bottlenecks:
- **Vegetable Sector (Cosmetic Waste)**: Over **122,398 tonnes** of vegetables are lost at the farm level annually in Ireland (EPA Research 410, 2022). Approximately **30%** of fruit and vegetables are rejected by supermarket retail chains solely on cosmetic imperfections, despite being nutritionally sound.
- **Meat Sector (Organic Premium Forfeiture)**: Up to **70% of organic lambs** and **30% of organic cattle** are processed into conventional supply chains (Agriland, 2024), losing their organic price premium due to a lack of direct links to specialized organic abattoirs and retailers.
- **Dairy Sector (Uncontracted Surplus)**: Ireland's organic dairy pool (~80 producers nationally) experiences seasonal surplus volumes beyond fixed processor quotas that lack localized direct-to-buyer sales channels.

**The Solution**: An automated, transparent quality-grading marketplace that provides verifiable grading from harvest to delivery, giving buyers confidence to purchase surplus organic produce remotely.

---

## Core Platform Features & Business Logic

### 1. Dual-Inspection Quality Variance Protocol
- Produce is graded at harvest/dispatch by the farmer and upon arrival by the buyer.
- Quality degradation $>10\%$ triggers simulated payment hold and automatically initiates a **negotiation phase**, escalating to administrative arbitration only if direct negotiation fails.

### 2. 10 kg Weight-Based Logistics Optimization
- **< 10 kg**: Routed as convenient local drop-off / collection point pickup.
- **≥ 10 kg**: Activates scheduled farm delivery and pooled collection service options.

### 3. Organic Registration Gate & Admin Verification Queue
- Farmers must upload official certification (e.g., IOA or Organic Trust license) during onboarding.
- Accounts remain locked in `pending_verification` status until reviewed and approved by an administrator in `AdminDashboard.jsx`.

### 4. Deliberate Quality Boundaries
- **Visually Gradable**: Fruits and vegetables undergo automated CV inspection.
- **Certificate-Based**: Dairy and meat products (where freshness is microbiological or chemical) are authenticated via certified declarations and cold-chain compliance.

---

## Computer Vision & Hybrid Grading Engine

```
                                RESNET-18 MULTI-HEAD ARCHITECTURE
                                
   Input Image (224x224 RGB)
              │
              ▼
   ┌──────────────────────┐
   │ ResNet-18 Backbone   │  (Feature Extraction, Conv + Residual Blocks)
   └──────────┬───────────┘
              │
      ┌───────┴──────────────────┐
      ▼                          ▼
┌───────────────────┐      ┌───────────────────┐
│   Product Head    │      │    Defect Head    │
│  (Linear 512->14) │      │  (Linear 512->2)  │
│  14 Produce Types │      │   Fresh vs Defect │
└───────────────────┘      └───────────────────┘
```

### Supported Produce Classes (14)
`apple`, `banana`, `capsicum`, `carrot`, `cucumber`, `grape`, `guava`, `jujube`, `mango`, `orange`, `pomegranate`, `potato`, `strawberry`, `tomato`.

### Hybrid 80:20 Quality Score Formula
$$S_{\text{final}} = 0.80 \times S_{\text{neural}} + 0.20 \times S_{\text{colour}}$$

Where:
- $S_{\text{neural}} = 100.0 \cdot P(\text{fresh}) + 55.0 \cdot P(\text{minor}) + 8.0 \cdot P(\text{major})$
- $S_{\text{colour}} = 0.60 \cdot \text{Vibrancy}_{\text{HSV}} + 0.40 \cdot \text{Uniformity}_{\text{Hue}}$

### Letter Grade Mapping
- **Grade A (Premium)**: $P(\text{fresh}) \ge 0.85$ or $S_{\text{final}} \ge 85.0$
- **Grade B (Good)**: $0.70 \le P(\text{fresh}) < 0.85$ or $70.0 \le S_{\text{final}} < 85.0$
- **Grade C (Fair)**: $0.50 \le P(\text{fresh}) < 0.70$ or $50.0 \le S_{\text{final}} < 70.0$
- **Grade R (Reject)**: $P(\text{fresh}) < 0.50$ or $S_{\text{final}} < 50.0$

---

## Dual-Inspection Quality Variance Protocol

$$\text{Variance \%} = \left( \frac{S_{\text{dispatch}} - S_{\text{delivery}}}{S_{\text{dispatch}}} \right) \times 100$$

```
+---------------------------------------------------------------------------------------------------+
|                                 DUAL-INSPECTION VARIANCE LIFECYCLE                                |
+---------------------------------------------------------------------------------------------------+
|  1. DISPATCH INSPECTION --> Farmer uploads photo before shipping --> Score A (94.0/100)          |
|  2. DELIVERY INSPECTION --> Buyer uploads photo upon arrival       --> Score A (92.5/100)          |
|  3. VARIANCE CHECK     --> (94.0 - 92.5) / 94.0 * 100 = 1.6% drop  --> Within 10% Tolerance        |
|  4. RESOLUTION         --> PASS: Order Completed, Invoice Generated, Payment Settled (Simulated)  |
|  5. IF VARIANCE > 10%  --> FLAG: Payment Held, Negotiation Opened, Escalation to Admin if Unresolved|
+---------------------------------------------------------------------------------------------------+
```

---

## Two-Stage Bulk Produce Grading Pipeline

```
  Multi-Item Image ──► [ ResNet-18 Whole-Image Pre-Check ] ──► (Verify Produce Type)
                               │
                               ▼
                       [ YOLOv8 Detector ] ──► Localize Bounding Boxes
                               │
                               ▼
                       [ NMS + 95% Inner Crop ] ──► Isolate Individual Items
                               │
                               ▼
                       [ ResNet-18 Defect Head ] ──► Grade Each Item Individually
                               │
                               ▼
                       [ Batch Aggregation ] ──► Fair Batch Score (e.g. 7 of 8 Fresh)
```

---

## Dataset Quality & Perceptual Hashing Leakage Control

The model was trained exclusively on **two verified datasets** (*Fruit and Vegetable Diseases Dataset* + *Processed Images_Fruits*):
- **pHash Audit**: Revealed a **34.7% near-duplicate rate** across combined image sets.
- **Grouped Disjoint Split**: Near-duplicate clusters were assigned atomically to either train or test sets to eliminate data leakage.
- **Held-Out Test Performance**:
  - **Product Classification Accuracy**: **96.8%**
  - **Quality Grading Accuracy**: **98.3%**
  - **Top Per-Product F1 Scores**: Banana (**99.16%**), Strawberry (**99.03%**), Pomegranate (**98.70%**), Apple (**98.41%**), Orange (**97.83%**), Grape (**97.56%**), Mango (**97.01%**).

---

## Digital QR Produce Passport & Traceability

Every listing and completed order produces a live, verifiable **Digital QR Produce Passport** (`GET /api/traceability/qr`):
- **Origin Provenance**: Farm name, location, and verified organic certification body/license number.
- **Lifecycle Chain**: Listing creation timestamp, dispatch grade, delivery arrival grade, and recorded variance percentage.
- **Visual Evidence**: Side-by-side farm inspection photo and delivery inspection photo.

---

## System Architecture & Technology Stack

```
                                    ORGANICLINK SYSTEM ARCHITECTURE

  +---------------------------------------------------------------------------------------------------+
  |                                        REACT 18 + VITE FRONTEND                                   |
  |  Marketplace Feed | Farmer Dashboard | Buyer Dashboard | Admin Arbitration | Traceability Passport |
  |  CameraOrUploadInput Component (Live WebRTC Camera Viewfinder + Native File Upload Fallback)       |
  +---------------------------------------------------------------------------------------------------+
                                                      │  HTTP / REST API (Axios + JWT)
                                                      ▼
  +---------------------------------------------------------------------------------------------------+
  |                                         FASTAPI BACKEND                                           |
  |  /api/auth     | /api/farms        | /api/contracts  | /api/products  | /api/quality | /api/orders  |
  |  /api/payments | /api/ratings      | /api/hubs       | /api/demand    | /api/messages| /api/admin   |
  |  /api/delivery | /api/production   | /api/traceability| /api/profile                               |
  +---------------------------------------------------------------------------------------------------+
         │                                │                                   │
         ▼                                ▼                                   ▼
  +---------------+              +--------------------+              +--------------------+
  | DATABASE LAYER|              | COMPUTER VISION CV |              | PDF DOCUMENTS SVC  |
  | SQLite (dev)  |              | PyTorch ResNet-18  |              | ReportLab Engine   |
  | SQLAlchemy 2.0|              | YOLOv8 Detector    |              | Quality Certs      |
  +---------------+              +--------------------+              +--------------------+
```

### Technology Matrix
* **Backend**: Python 3.13, FastAPI, SQLAlchemy 2.0, Pydantic v2, Uvicorn.
* **Computer Vision**: PyTorch, Torchvision, Ultralytics YOLOv8, OpenCV (`cv2`), PIL, NumPy.
* **Frontend**: React 18, Vite, Tailwind CSS, Lucide React Icons, Axios, React Router v6.
* **Document Engine**: ReportLab (Invoices & Quality Certificates).

---

## Project Directory Layout

```
organiclink/
├── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
│
├── backend/
│   ├── main.py                     FastAPI entrypoint, CORS, static mounts & routers
│   ├── config.py                   Pydantic settings (JWT keys, tolerance thresholds)
│   ├── database.py                 SQLAlchemy database engine and session factory
│   ├── sync_db.py                  Schema migration and column alignment helper
│   ├── requirements.txt            Python dependencies
│   ├── Dockerfile                  Backend container definition
│   │
│   ├── cv/
│   │   ├── inference.py            ResNet-18 multi-head quality inference engine
│   │   ├── detection.py            YOLOv8 produce detection engine
│   │   ├── grading.py              80/20 hybrid quality scoring formula & grade bands
│   │   ├── bulk_grading.py         Two-stage bulk crate/tray grading pipeline
│   │   └── models/
│   │       ├── grading_model.pt    Trained ResNet-18 weights (14 classes, binary defect)
│   │       ├── produce_detector.pt Fine-tuned YOLOv8 bounding box weights
│   │       ├── eval_report.json    Model performance metrics
│   │       └── eval_report.txt     Confusion matrices and per-product F1 scores
│   │
│   ├── models/
│   │   └── all_models.py           SQLAlchemy ORM models (User, Product, Order, etc.)
│   ├── schemas/
│   │   └── schemas.py              Pydantic validation schemas
│   ├── routers/                    18 modular REST API routers
│   ├── seed/                       Demonstration data and 60+ Irish location coordinates
│   ├── services/                   Audit, demand scoring, geo-Haversine, ReportLab PDF generator
│   ├── tests/                      Automated pytest test suite
│   └── uploads/                    Dynamic inspection photos and generated documents
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── Dockerfile
│   └── src/
│       ├── App.jsx                 Application router with pending verification guards
│       ├── main.jsx                React application mount point
│       ├── index.css               Global CSS and Tailwind directives
│       ├── context/AuthContext.jsx JWT authentication state provider
│       ├── api/axios.js            Axios instance with Bearer token interceptor
│       ├── components/             CameraOrUploadInput, CVBreakdownPanel, GradeBadge, etc.
│       └── pages/                  19 React application pages
│
├── report_figures/                 300 DPI high-resolution figures for report/thesis
└── report_screenshots/             Interface walkthrough screenshots
```

---

## API Endpoint Reference

All routes are served under `/api` by FastAPI (interactive OpenAPI documentation available at `/docs` and `/redoc`).

| Router Module | Route Prefix | Key Functionality |
| :--- | :--- | :--- |
| `auth.py` | `/api/auth` | `/register` (with certificate upload), `/login`, `/me` |
| `admin.py` | `/api/admin` | `/farms` (verification queue), `/disputes`, `/audit-logs`, `/settings` |
| `farms.py` | `/api/farms` | Farm profile management, certificates, production history |
| `products.py` | `/api` | `/marketplace`, `/farms/{id}/products`, single/bulk listing creation |
| `quality.py` | `/api/quality` | Direct image inspection execution, certificate retrieval |
| `orders.py` | `/api/orders` | Order lifecycle, negotiation, dispatch/delivery inspection uploads |
| `traceability.py` | `/api/traceability` | `/qr` generation, public produce passports |
| `payments.py` | `/api/payments` | Simulated payment settlement, invoice PDF generation |
| `ratings.py` | `/api` | Post-delivery star ratings and farmer reputation updates |
| `hubs.py` / `local_hubs.py`| `/api/hubs` | Regional aggregation hub locator and distance calculation |
| `demand.py` | `/api/demand` | 30-day regional produce demand indicator |
| `messages.py` | `/api/messages` | Direct buyer-farmer messaging |
| `notifications.py`| `/api/notifications` | Real-time user notification feed |
| `profile.py` | `/api/profile` | User profile management |
| `delivery.py` | `/api/delivery` | Delivery slots, pooled transport coordination |

---

## Frontend Routes & Components

| Path | Component | Audience & Gating |
| :--- | :--- | :--- |
| `/marketplace` | `Marketplace.jsx` | Public / All users |
| `/product/:id` | `ProductDetail.jsx` | Public / All users |
| `/farm/:id` | `FarmProfile.jsx` | Public / All users |
| `/login`, `/register` | `Login.jsx`, `Register.jsx` | Public |
| `/pending-approval` | `PendingApproval.jsx` | Unverified / Pending farmers |
| `/farmer/dashboard` | `FarmerDashboard.jsx` | Verified Farmers |
| `/farmer/listings/new`| `FarmerNewListing.jsx`| Verified Farmers |
| `/farmer/production` | `FarmerProduction.jsx` | Verified Farmers |
| `/farmer/contracts` | `FarmerContracts.jsx` | Verified Farmers |
| `/buyer/dashboard` | `BuyerDashboard.jsx` | Commercial Buyers & Consumers |
| `/orders/:id` | `OrderDetail.jsx` | Order participants (Dual-inspection flow) |
| `/traceability/:type/:id` | `Traceability.jsx` | Public QR Traceability Passport |
| `/admin` | `AdminDashboard.jsx` | System Administrators |

---

## Demonstration Login Credentials

All demonstration accounts use the password `Password123!` (Admin uses `Admin123!`).

| Role | Name | Email | Password | Details / Primary Feature |
| :--- | :--- | :--- | :--- | :--- |
| **System Admin** | Admin User | `admin@organiclink.ie` | `Admin123!` | Farm verification queue, dispute arbitration |
| **Farmer (Produce)** | Sean O'Mahony | `farmer.cork1@organiclink.ie` | `Password123!` | Glenbeg Organic Farm (Bandon, Co. Cork) |
| **Commercial Retailer**| Bandon Farm Shop| `retail.cork1@organiclink.ie` | `Password123!` | Commercial retail buyer (Cork) |
| **Farmer (Dairy)** | Aoife Flaherty | `galway.dairy@organic.ie` | `Password123!` | Corrib Organic Dairy (Tuam, Co. Galway) |
| **Farmer (Mixed)** | Liam Ryan | `tipp.produce@organic.ie` | `Password123!` | Golden Vale Organic Produce (Nenagh, Co. Tipperary)|
| **Restaurant Buyer** | Wild Plum Bistro| `rest1@bistro.ie` | `Password123!` | Farm-to-fork restaurant buyer |
| **Direct Consumer** | Mary Fitzgerald | `consumer1@organic.ie` | `Password123!` | Individual organic household consumer |

---

## Installation & Setup Guide

### Prerequisites
* **Python 3.11+** (Python 3.13 recommended)
* **Node.js 18+** and **npm**
* **Git**

### 1. Clone & Set Up Backend
```bash
# Navigate to backend directory
cd backend

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Seed demonstration database
python -m seed.seed_data

# Start FastAPI server (runs at http://127.0.0.1:8000)
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Set Up Frontend
```bash
# Open a new terminal and navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Start Vite development server (runs at http://localhost:5173 or 5174)
npm run dev
```

### 3. Run Automated Tests
```bash
cd backend
python -m pytest tests/test_organiclink.py -v
```

---

### Academic Notice
Developed as part of the MEng in Computer Vision & Artificial Intelligence thesis at the University of Limerick (CE6013 Digital Futures Project).
