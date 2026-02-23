# Matritwa — Maternal Health Tracking System

**Matritwa** is an offline-first Progressive Web App (PWA) built to empower Female Community Health Volunteers (FCHVs) in tracking and managing maternal health in underserved communities. It provides real-time SOS emergency support, antenatal care (ANC) visit tracking, risk alerts, and healthcare analytics — all accessible even without an internet connection.

> Built for **CodeYatra 2.0 Hackathon** by **Team Access Denied**

---

## Features

- **Mother Registration** — Multi-step registration with GPS-based location capture and photo upload
- **ANC Visit Tracking** — Record antenatal care visits with vitals, symptoms, and automatic danger-sign detection
- **SOS Emergency System** — One-tap emergency trigger with offline queuing and automatic sync via IndexedDB + Service Worker
- **Priority Alerts** — Automated alerts for high-risk pregnancies, missed appointments, and emergencies (Critical / High / Medium / Low)
- **Hospital Consultations** — Referral management with symptom logging and sync status tracking
- **Awareness Programs** — Schedule and track community health education events (Nutrition, Hygiene, Mental Health, Vaccinations)
- **Monthly Reports** — Auto-generated performance metrics with goal tracking and weekly breakdowns
- **Healthcare Dashboard** — Aggregate statistics for healthcare workers: total mothers, high-risk cases, visits, and consultations
- **Offline-First PWA** — Service Worker caching + IndexedDB for full functionality without connectivity
- **Role-Based Access** — Healthcare Workers and Admins with scoped permissions

---

## Tech Stack

| Layer          | Technology                          |
|----------------|-------------------------------------|
| Backend        | Django 5.1 (Python)                 |
| Database       | SQLite (dev) / PostgreSQL (prod)    |
| Frontend       | Django Templates, HTML5, CSS3, JS   |
| PWA            | Service Worker, Web App Manifest    |
| Offline Sync   | IndexedDB + REST API               |
| Image Handling | Pillow                              |
| CORS           | django-cors-headers                 |
| Deployment     | Gunicorn, ngrok (tunneling)         |

---

## Project Structure

```
matritwa/
├── accounts/          # User authentication, FCHV registration, Mother profiles
├── healthcare/        # Healthcare worker dashboard & analytics
├── mother/            # Core maternal health bounded context
│   ├── application/   #   Commands (write) & Queries (read)
│   ├── domain/        #   Business logic, value objects, domain services
│   ├── models.py      #   ORM models (ANCVisit, Alert, SOS, Reports, etc.)
│   ├── views.py       #   Thin HTTP adapter layer
│   ├── api.py         #   REST endpoints for offline SOS sync
│   └── forms.py       #   Django forms
├── config/            # Django project settings & URL configuration
├── templates/         # HTML templates (base, accounts, mother)
├── static/            # CSS, JS, Service Worker, PWA manifest, images
├── media/             # Uploaded files (mother photos)
└── manage.py
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/<your-org>/codeyatra2.0_access_denied_matritwa.git
cd codeyatra2.0_access_denied_matritwa

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Run the development server
python manage.py runserver
```

The app will be available at **http://127.0.0.1:8000/**

### Environment Variables (optional)

| Variable                | Default                                              | Description                    |
|-------------------------|------------------------------------------------------|--------------------------------|
| `DJANGO_SECRET_KEY`     | *(insecure dev key)*                                 | Django secret key              |
| `DJANGO_DEBUG`          | `True`                                               | Enable/disable debug mode      |
| `DJANGO_ALLOWED_HOSTS`  | `localhost,127.0.0.1,.ngrok-free.app,.ngrok.io`      | Comma-separated allowed hosts  |

---

## API Endpoints

### SOS Emergency API (offline-first)

| Method | Endpoint                      | Description                          |
|--------|-------------------------------|--------------------------------------|
| POST   | `/api/sos/`                   | Create a new SOS emergency           |
| POST   | `/api/sos/sync/`              | Sync offline-queued SOS records      |
| GET    | `/api/sos/active/`            | List active SOS emergencies          |
| POST   | `/api/sos/<id>/resolve/`      | Resolve an SOS emergency             |

---

## Key Modules

### Accounts
- Custom `User` model with role-based access (Healthcare Worker / Admin)
- `MotherProfile` — data record for pregnant women (not a system user), including pregnancy details, GPS location, blood group, and medical history

### Mother (Core Domain)
- **ANC Visits** — Visit records with automatic danger-sign detection based on symptom classification
- **Alerts** — Priority-based alert system (SOS, High Risk, Missed Visit, System)
- **SOS Emergencies** — UUID-based offline deduplication, GPS capture, risk-level assessment, and resolution workflow
- **Scheduled Visits** — ANC/PNC visit scheduling with overdue detection
- **Hospital Consultations** — Referral tracking with sync status
- **Awareness Programs** — Community education event management
- **Monthly Reports** — Aggregated metrics with goal progress tracking

### Healthcare
- Dashboard with aggregate statistics across all registered mothers

---

## Architecture

The project follows a **clean architecture** pattern within the `mother` app:

- **Domain Layer** (`mother/domain/`) — Pure business logic, value objects, and domain services (e.g., `PregnancyCalculator`, `SOSRiskEvaluator`, `TimeAgoFormatter`)
- **Application Layer** (`mother/application/`) — Commands (writes) and Queries (reads) that orchestrate domain logic
- **Infrastructure Layer** (`mother/models.py`, `mother/views.py`) — Django ORM models and thin HTTP adapters

Views contain zero business logic — they only parse requests, delegate to application services, and return responses.

---

## License

This project was developed as part of the CodeYatra 2.0 Hackathon.

---

## Team

**Access Denied**
