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
* **Module**: CE6013 Digital Futures Project
* **Institution**: University of Limerick
* **Supervisors**: Dr. Elfed Lewis (CE6013), Dr. Annmarie Ryan (Digital Futures Lab)

---

## Executive Summary

**OrganicLink** is a full-stack web marketplace and computer-vision quality-assessment platform designed for the Irish organic agricultural sector. It connects certified Irish organic produce and dairy farmers directly with commercial buyers (retailers, farm-to-fork restaurants, institutions, aggregators, and consumers) to enable direct trade of surplus yields exceeding fixed processor contracts.

The platform addresses the central trust barrier in remote produce transactions: the impossibility of verifying produce quality at a distance. OrganicLink solves this through a novel **Dual-Inspection Quality Variance Protocol** (grading produce at both dispatch and delivery using the identical model to automatically detect transit quality drops), a **Two-Stage YOLOv8 + ResNet-18 Bulk Grading Pipeline**, **Perceptual Hashing Leakage Control**, an **Admin Organic Certificate Verification Gate**, and an instant **Digital QR Produce Traceability Passport**.

---

## Table of Contents
1. [The Organic Market-Access Problem in Ireland](#the-organic-market-access-problem-in-ireland)
2. [Key Contributions & Core Features](#key-contributions--core-features)
3. [Computer Vision Architecture & Hybrid Scoring](#computer-vision-architecture--hybrid-scoring)
4. [Dual-Inspection Variance Protocol (Main Contribution)](#dual-inspection-variance-protocol-main-contribution)
5. [Two-Stage Bulk Produce Grading Pipeline](#two-stage-bulk-produce-grading-pipeline)
6. [Dataset Quality & Perceptual Hashing Leakage Control](#dataset-quality--perceptual-hashing-leakage-control)
7. [Digital QR Code Produce Passport](#digital-qr-code-produce-passport)
8. [System Architecture & Technology Stack](#system-architecture--technology-stack)
9. [Project Directory Layout](#project-directory-layout)
10. [API Endpoint Reference](#api-endpoint-reference)
11. [Frontend Routes & Components](#frontend-routes--components)
12. [Seeded Demonstration Login Credentials](#seeded-demonstration-login-credentials)
13. [Installation & Setup Instructions](#installation--setup-instructions)
14. [Resume Bullet Points & Elevator Pitch](#resume-bullet-points--elevator-pitch)

---

## The Organic Market-Access Problem in Ireland

Demand for organic food in Ireland has grown steadily, supported by national policy targets to significantly expand organic farmland. However, small, dispersed organic producers face major barriers in reaching buyers:
- **Vegetable Sector (Cosmetic Rejection)**: Over **122,398 tonnes** of vegetables are lost at the farm level annually in Ireland (EPA Research 410, 2022). Approximately **30%** of fruit and vegetables are rejected by commercial retail buyers solely on cosmetic standards (Irish Examiner, 2024), despite being completely fit to eat.
- **Meat Sector (Leakage)**: Estimates indicate that **70%** of organic lambs and **30%** of organic cattle are processed as conventional (Agriland, 2024), forfeiting their organic premium due to weak links to organic processors and buyers.
- **Dairy Sector (Unsold Surplus)**: Consultation with Teagasc organic dairy specialist Joe Kelleher highlighted that Ireland's small organic milk pool (around 80 farmers nationally) produces surplus volume beyond processor contracts that lacks direct market mechanisms.

**The Core Challenge**: Trust in remote transactions. Buyers cannot inspect produce physically; disputes over produce condition upon arrival reduce to subjective ("he-said-she-said") arguments. OrganicLink provides an objective, automated, evidence-based quality verification layer.

---

## Key Contributions & Core Features

### 1. Dual-Inspection Quality Variance Protocol
- Produce is graded at two points: first by the farmer at **Dispatch**, and again by the buyer at **Delivery Arrival**.
- Uses the exact same multi-head model at both ends to yield an objective, comparable score.
- If quality drops beyond an acceptable tolerance ($\text{Variance} > 10\%$), payment is held in escrow and a negotiation step opens, escalating to admin dispute resolution only if negotiation fails.

### 2. Multi-Role Direct-Trade Marketplace
- Supports 4 distinct user roles: Farmers (sellers), Commercial Buyers (retailers, restaurants, institutions, manufacturers), Consumers, and Administrators.
- Features direct produce listing, browsing, filtering by county/Eircode routing key, in-app price/quantity negotiation, and payment status tracking.

### 3. Farmer Organic Registration Gate & Admin Queue
- Farmer registration requires an organic certificate upload (`verification_status="pending_verification"`).
- Pending accounts are blocked from accessing seller dashboards, profile pages, and listing creation until reviewed.
- Admin dashboard (`AdminDashboard.jsx`) provides explicit **Approve** and **Reject** controls.

### 4. Deliberate Design Boundaries
- **Visually Gradable Produce**: Automated CV quality grading is applied exclusively to fruits and vegetables where decay and blemishes are visually observable.
- **Certificate-Based Products**: Milk (chemical/bacterial quality) and Meat (handling/safety) are non-visually gradable; quality is managed via administrative certification.
- **Organic Provenance**: Organic authenticity cannot be detected visually; it is verified strictly through official certification (e.g. IOA / Organic Trust).

---

## Computer Vision Architecture & Hybrid Scoring

The computer-vision engine (`backend/cv/`) employs a **ResNet-18 Multi-Head Classifier** pre-trained on ImageNet:
- **Shared Backbone**: ResNet-18 extracts feature representations.
- **Product Head**: Classifies 14 produce types (`apple`, `banana`, `capsicum`, `carrot`, `cucumber`, `grape`, `guava`, `jujube`, `mango`, `orange`, `pomegranate`, `potato`, `strawberry`, `tomato`).
- **Defect Head**: Binary classification (`fresh` vs `defect`).

### Hybrid Scoring Formula (80:20 Weighting)
To ground neural learned patterns with physically interpretable appearance properties, final quality scores combine neural classifier probability (80%) with OpenCV classical metrics (20%):

$$\text{Final Score} = 0.80 \times (\text{Neural Quality Score}) + 0.20 \times (\text{Classical OpenCV Metrics})$$

Where OpenCV metrics analyze:
1. **Colour Vibrancy**: Mean saturation in HSV space.
2. **Colour Uniformity**: Hue variation.
3. **Surface Defect Coverage**: Adaptive thresholding identifying discoloured/damaged surface regions.

Scores ($0-100$) map to letter grades:
- `Score >= 90.0` $\rightarrow$ **Grade A** (Premium)
- `Score >= 75.0` $\rightarrow$ **Grade B** (Good)
- `Score >= 50.0` $\rightarrow$ **Grade C** (Fair)
- `Score < 50.0` $\rightarrow$ **Grade R** (Reject)

---

## Dual-Inspection Variance Protocol (Main Contribution)

$$\text{Quality Variance \%} = \left( \frac{\text{Dispatch Score} - \text{Delivery Score}}{\text{Dispatch Score}} \right) \times 100$$

```
+---------------------------------------------------------------------------------------------------+
|                                 DUAL-INSPECTION VARIANCE LIFECYCLE                                |
+---------------------------------------------------------------------------------------------------+
|  1. DISPATCH INSPECTION --> Farmer uploads photo before shipping --> Score A (94.0/100)          |
|  2. DELIVERY INSPECTION --> Buyer uploads photo upon arrival       --> Score A (92.5/100)          |
|  3. VARIANCE CHECK     --> (94.0 - 92.5) / 94.0 * 100 = 1.6% drop  --> Within 10% Tolerance        |
|  4. RESOLUTION         --> PASS: Order Completed, Invoice Generated, Escrow Payment Released      |
|  5. IF VARIANCE > 10%  --> DISPUTE: Payment Held, Negotiation Step Opened, Admin Escalation    |
+---------------------------------------------------------------------------------------------------+
```

---

## Two-Stage Bulk Produce Grading Pipeline

For multi-item photographs (baskets or crates of produce), single-image classification is insufficient. OrganicLink implements a **Two-Stage YOLOv8 + ResNet-18 Pipeline** (`backend/cv/bulk_grading.py`):

1. **Whole-Image Product Pre-Check**: Evaluates full photo against ResNet-18 classifier to catch product mismatches before item detection.
2. **YOLOv8 Detection & NMS Filtering**: Localizes individual items, applies Non-Maximum Suppression (IoU=0.50), and shrinks bounding boxes by 95% inner crop ratio to eliminate neighboring pixel bleed.
3. **Item Crop Classification**: Crops detected items and grades each individually using the ResNet-18 defect head.
4. **Batch Aggregation**: Aggregates item results into a fair batch grade (e.g. "3 of 4 items fresh") rather than condemning an entire basket for a single defective item.

---

## Dataset Quality & Perceptual Hashing Leakage Control

Public produce datasets contain extensive duplicate and near-duplicate imagery (e.g., re-photographed items or augmented duplicates). If split randomly across train and test sets, models exhibit **data leakage**, inflating reported accuracy through memorization.

- **Perceptual Hashing**: Images were hashed using perceptual hashing (Hamming distance). The audit revealed **34.7% to 61.8%** near-duplicate contamination across datasets.
- **Leakage-Free Grouped Split**: Implemented a grouped train/validation split where every group of near-duplicates was assigned exclusively to either train or test.
- **Held-Out Model Performance**:
  - **Product Identification Accuracy**: **96.8%** on held-out test set.
  - **Quality Assessment Accuracy**: **98.3%** on held-out test set.
  - **Per-Product F1-Scores**:
    - Banana: **99.16%**
    - Strawberry: **99.03%**
    - Pomegranate: **98.70%**
    - Apple: **98.41%**
    - Orange: **97.83%**
    - Grape: **97.56%**
    - Mango: **97.01%**
    - Guava: **96.47%**
    - Cucumber: **95.65%**
    - Tomato: **95.24%**
    - Carrot: **94.50%**
    - Jujube: **90.53%**
    - Potato: **88.80%**
    - Capsicum: **88.54%**

---

## Digital QR Code Produce Passport

Every listing and order generates an instant Digital Produce Passport accessible via QR code (`GET /api/traceability/qr`):

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
- **Database**: SQLite by default for development (`backend/organiclink.db`); PostgreSQL supported for production deployment.

---

## Project Directory Layout

```
organiclink/
├── backend/                      FastAPI Application Root
│   ├── main.py                   Lifespan application entrypoint & middleware
│   ├── config.py                 Pydantic SettingsConfigDict (DB URL, JWT, constants)
│   ├── database.py                SQLAlchemy engine & session factory
│   ├── models/
│   │   └── all_models.py         SQLAlchemy models (User, Farm, Order, QualityInspection, etc.)
│   ├── schemas/
│   │   └── schemas.py            Pydantic v2 schemas with ConfigDict
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

All routes are served under `/api` by FastAPI (interactive OpenAPI docs at `/docs` and `/redoc`).

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

# Seed demonstration database
python -m seed.seed_data

# Start FastAPI development server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend

# Install frontend dependencies
npm install

# Start Vite development server
npm run dev -- --host 0.0.0.0 --port 5174
```

Access the application in your browser at: `http://localhost:5174`

---

## Resume Bullet Points & Elevator Pitch

### Short Version:
- Built **OrganicLink**, a full-stack computer-vision marketplace (FastAPI, React, PostgreSQL, PyTorch, YOLOv8) grading organic produce quality from photos at 96.8%/98.3% accuracy.
- Designed a novel dual-inspection protocol that grades produce at dispatch and delivery, automatically detecting quality disputes with objective evidence.
- Identified and corrected 34.7%+ dataset leakage via perceptual hashing, proving reported model accuracy reflected genuine generalization.

### Elevator Pitch (for interviews):
> *"OrganicLink is a marketplace I built that lets organic farmers sell directly to buyers, using AI to solve the trust problem in remote food trade. The core idea is a dual-inspection system: the AI grades the produce from a photo when it's sent and again when it's delivered, and if quality dropped in transit, it automatically flags a dispute — so there's objective evidence instead of an argument. I also found that a third of my training data were near-duplicate images inflating accuracy, so I corrected for it — which most projects never check. It's built with FastAPI, React, PostgreSQL, PyTorch, and YOLOv8."*

---

### License & Project Information
Developed for MEng in Computer Vision & Artificial Intelligence thesis project at University of Limerick (CE6013 Digital Futures Project). All rights reserved.
