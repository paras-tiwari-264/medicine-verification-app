# MediVerify — Medicine Verification API

AI-powered FastAPI backend for detecting counterfeit medicines using barcode scanning, OCR image analysis, and Firebase Firestore.

---

## Project Structure

```
medicine-verify/
├── app/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Settings loaded from .env
│   ├── dependencies.py          # JWT auth dependencies
│   ├── routers/
│   │   ├── auth.py              # Signup / Login
│   │   ├── medicines.py         # Medicine CRUD
│   │   ├── verification.py      # Core verification endpoints
│   │   ├── reports.py           # Suspicious medicine reports
│   │   ├── admin.py             # Admin dashboard APIs
│   │   └── pharmacy.py          # Pharmacy registration & verification
│   ├── models/                  # Pydantic schemas
│   ├── services/
│   │   ├── firebase.py          # Firestore client
│   │   ├── ocr.py               # Tesseract OCR
│   │   ├── barcode.py           # Barcode / QR scanning
│   │   └── risk_engine.py       # Fake medicine risk scoring
│   └── utils/
│       └── image_processing.py  # OpenCV preprocessing
├── static/                      # Frontend UI (HTML/CSS/JS)
├── .env.example                 # Environment variable template
├── requirements.txt
├── run.bat                      # One-click Windows launcher
└── README.md
```

> **Security note:** Never commit `.env` or your Firebase service account key to version control. Both are listed in `.gitignore`.

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd medicine-verify
```

### 2. Create and activate virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Tesseract OCR

- **Windows**: Download from https://github.com/UB-Mannheim/tesseract/wiki, install to `C:\Program Files\Tesseract-OCR\`
- **Ubuntu/Debian**: `sudo apt install tesseract-ocr`
- **macOS**: `brew install tesseract`

### 5. Install ZBar (for 1D barcode support)

- **Windows**: Download DLLs from https://sourceforge.net/projects/zbar/ and add to PATH
- **Ubuntu**: `sudo apt install libzbar0`
- **macOS**: `brew install zbar`

### 6. Firebase Setup

1. Go to https://console.firebase.google.com and create a project
2. Enable **Firestore Database** (test mode for development)
3. Go to Project Settings → Service Accounts → Generate new private key
4. Save the downloaded JSON file locally — **do not commit it**
5. Note your Project ID from Project Settings

### 7. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
FIREBASE_CREDENTIALS_PATH=path/to/your-service-account-key.json
FIREBASE_PROJECT_ID=your-firebase-project-id
SECRET_KEY=your-strong-random-secret-key
TESSERACT_CMD=tesseract
```

### 8. Run the server

```bash
# Windows — double-click or run:
run.bat

# Or manually:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API docs: http://localhost:8000/docs
- Frontend UI: http://localhost:8000/ui

---

## API Endpoints

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

## Sample Requests

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
  -F "file=@medicine_strip.jpg"
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

## Risk Score

| Score | Status | Meaning |
|-------|--------|---------|
| 0.0 – 0.29 | genuine | Medicine appears authentic |
| 0.3 – 0.59 | suspicious | Anomalies detected — verify manually |
| 0.6 – 1.0 | fake | Likely counterfeit — do not consume |

---

## Tech Stack

- **Backend**: FastAPI, Python 3.12
- **Database**: Firebase Firestore
- **OCR**: Tesseract + OpenCV
- **Barcode**: pyzbar / OpenCV QRCodeDetector
- **Auth**: JWT (python-jose) + bcrypt
- **Frontend**: Vanilla HTML/CSS/JS (served via FastAPI static files)
