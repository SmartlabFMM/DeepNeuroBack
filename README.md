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
├── models/
│   └── database.py
├── routes/
│   ├── auth.py
│   └── diagnosis.py
└── services/
    └── email_service.py
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