# Medicine Verification API

A FastAPI backend for verifying medicine authenticity via barcode scanning and OCR image analysis.

---

## Project Structure

```
medicine-verify/
├── app/
│   ├── main.py               # FastAPI app entry point
│   ├── config.py             # Settings from .env
│   ├── dependencies.py       # JWT auth dependencies
│   ├── routers/
│   │   ├── auth.py           # Signup / Login
│   │   ├── medicines.py      # Medicine CRUD
│   │   ├── verification.py   # Core verification endpoints
│   │   ├── reports.py        # Suspicious medicine reports
│   │   ├── admin.py          # Admin dashboard APIs
│   │   └── pharmacy.py       # Pharmacy registration & verification
│   ├── models/               # Pydantic schemas
│   ├── services/
│   │   ├── firebase.py       # Firestore client
│   │   ├── ocr.py            # Tesseract OCR
│   │   ├── barcode.py        # pyzbar barcode/QR scanning
│   │   └── risk_engine.py    # Fake medicine risk scoring
│   └── utils/
│       └── image_processing.py  # OpenCV preprocessing
├── firebase-credentials.json    # ← your Firebase service account key
├── .env
├── requirements.txt
└── README.md
```

---

## Setup Instructions

### 1. Clone / navigate to project

```bash
cd medicine-verify
```

### 2. Create and activate virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Tesseract OCR

- **Windows**: Download installer from https://github.com/UB-Mannheim/tesseract/wiki
  - Install to `C:\Program Files\Tesseract-OCR\`
  - Set `TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe` in `.env`
- **Ubuntu/Debian**: `sudo apt install tesseract-ocr`
- **macOS**: `brew install tesseract`

### 5. Install ZBar (required by pyzbar)

- **Windows**: Download DLLs from https://sourceforge.net/projects/zbar/ and add to PATH
- **Ubuntu**: `sudo apt install libzbar0`
- **macOS**: `brew install zbar`

### 6. Firebase Setup

1. Go to https://console.firebase.google.com
2. Create a new project
3. Enable **Firestore Database** (start in test mode for development)
4. Go to Project Settings → Service Accounts → Generate new private key
5. Save the downloaded JSON as `firebase-credentials.json` in the project root
6. Copy your Project ID

### 7. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:
```
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
FIREBASE_PROJECT_ID=your-actual-project-id
SECRET_KEY=generate-a-strong-random-key
TESSERACT_CMD=tesseract   # or full path on Windows
```

### 8. Run the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: http://localhost:8000/docs

---

## API Endpoints Summary

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /auth/signup | No | Register user |
| POST | /auth/login | No | Login, get JWT |
| POST | /verify/barcode | JWT | Verify by barcode string |
| POST | /verify/image | JWT | Upload image for OCR + barcode verify |
| GET | /medicines/ | JWT | List all medicines |
| POST | /medicines/ | Admin | Add medicine to DB |
| PATCH | /medicines/{id} | Admin | Update medicine |
| DELETE | /medicines/{id} | Admin | Delete medicine |
| POST | /reports/ | JWT | Report suspicious medicine |
| GET | /reports/ | Admin | List all reports |
| GET | /admin/stats | Admin | Dashboard statistics |
| GET | /admin/users | Admin | List all users |
| POST | /pharmacy/register | JWT | Register pharmacy |
| PATCH | /pharmacy/{id}/verify | Admin | Verify pharmacy |

---

## Sample Test Requests

### Signup
```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret123","full_name":"John Doe","role":"user"}'
```

### Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret123"}'
```

### Add Medicine (admin token required)
```bash
curl -X POST http://localhost:8000/medicines/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Paracetamol 500mg",
    "manufacturer": "ABC Pharma Ltd",
    "batch_number": "BATCH2024A",
    "expiry_date": "12/2026",
    "barcode": "8901234567890",
    "approved_packaging": "White blister pack",
    "active_ingredients": ["Paracetamol"],
    "dosage_form": "tablet"
  }'
```

### Verify by Barcode
```bash
curl -X POST http://localhost:8000/verify/barcode \
  -H "Authorization: Bearer <token>" \
  -F "barcode=8901234567890"
```

### Verify by Image
```bash
curl -X POST http://localhost:8000/verify/image \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/medicine_strip.jpg"
```

### Report Suspicious Medicine
```bash
curl -X POST http://localhost:8000/reports/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "barcode": "8901234567890",
    "description": "Packaging looks different from usual. Color is off.",
    "location": "Downtown Pharmacy, Main St"
  }'
```

---

## Firestore Collections

| Collection | Description |
|------------|-------------|
| `users` | Registered users |
| `medicines` | Verified medicine database |
| `verification_history` | All verification events |
| `reports` | Suspicious medicine reports |
| `pharmacies` | Registered pharmacies |

---

## Risk Score Interpretation

| Score | Status | Meaning |
|-------|--------|---------|
| 0.0 – 0.29 | genuine | Medicine appears authentic |
| 0.3 – 0.59 | suspicious | Anomalies detected, verify manually |
| 0.6 – 1.0 | fake | Likely counterfeit, do not consume |
