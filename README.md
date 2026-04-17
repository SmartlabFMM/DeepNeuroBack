# DeepNeuro Backend

Flask REST API for authentication, email verification, password reset, and diagnosis request workflows.

## Stack

- Python 3.8+
- Flask
- Flask-CORS
- SQLite
- python-dotenv
- SMTP (Gmail by default)

## Project Structure

```text
Backend/
├── app.py
├── config.py
├── requirements.txt
├── .env
├── medical_ai.db
├── uploads/
├── models/
│   └── database.py
├── routes/
│   ├── auth.py
│   └── diagnosis.py
│   └── files.py
└── services/
│   ├── email_service.py
│   └── ai_models/
│       ├── __init__.py
│       └── segmentation_models.py
```

## Prerequisites

- Python 3.8 or newer
- Valid email credentials for SMTP (required by `EmailService` on app startup)

## Installation

```bash
cd Backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Environment Variables

Create `Backend/.env`:

```env
# Flask
FLASK_ENV=development
DEBUG=True
SECRET_KEY=change-this-secret
CORS_ORIGINS=*
DATABASE_PATH=medical_ai.db

# Email (required)
EMAIL_SENDER=your-email@gmail.com
EMAIL_APP_PASSWORD=your-16-char-app-password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

Notes:
- `EMAIL_SENDER` and `EMAIL_APP_PASSWORD` are mandatory; app startup fails without them.
- `CORS_ORIGINS` accepts comma-separated values.
- `DATABASE_PATH` defaults to `../medical_ai.db` if not set in `.env`.

## Run the Backend

```bash
cd Backend
python app.py
```

Default server:

- URL: `http://localhost:5000`
- Health: `GET /api/health`

## API Overview

### Base Endpoints

- `GET /` - API info
- `GET /api/health` - service health

### Auth Routes (`/api/auth`)

- `POST /register`
- `POST /verify-email`
- `POST /login`
- `POST /request-password-reset`
- `POST /verify-reset-code`
- `POST /reset-password`
- `GET /user/<email>`

### Diagnosis Routes (`/api/diagnosis`)

- `POST /submit`
- `GET /doctor/<doctor_email>`
- `GET /radiologist/<radiologist_email>`
- `GET /radiologists`
- `GET /previous-cases/<doctor_email>`
- `PUT /mark-read/doctor/<request_id>`
- `PUT /mark-read/radiologist/<request_id>`

### File Routes (`/api/files`)

- `GET /api/files?uploaded_by_email=<email>`
- `POST /api/files/upload`
- `GET /api/files/<file_id>/download?user_email=<email>`

### Model Routes (`/api/models`)

- `GET /api/models/segmentation`
- `GET /api/models/segmentation?diagnosis_type=<diagnosis_type>`

## Data and Behavior Notes

- SQLite tables are auto-created on startup in `models/database.py`.
- User type is derived from `medical_id` prefix:
  - `01` -> doctor
  - `02` -> radiologist
  - otherwise -> unknown
- Passwords are hashed with SHA-256 before storage.
- Uploaded files are written to `uploads/`, and SQLite stores file metadata only.
- Upload limits default to 25 MB and accept PDFs, images, Office documents, CSV/TXT files, and NIfTI files.

## Quick Test

```bash
curl http://localhost:5000/api/health
```

Expected response includes:

```json
{
  "status": "healthy",
  "service": "DeepNeuro Backend",
  "version": "1.0.0"
}
```

## Troubleshooting

- App crashes on startup with email error:
  - Ensure `.env` exists in `Backend/` and both `EMAIL_SENDER` and `EMAIL_APP_PASSWORD` are set.
- Port 5000 already in use:
  - Stop the conflicting process or run app with a different port in `app.py`.
- Frontend cannot connect:
  - Confirm backend is running and `GET /api/health` works.
