# Matritwa — Project Documentation

> **Safe motherhood starts here 🌸**
> A digital maternal health companion designed for pregnant women, doctors, and
> Female Community Health Volunteers (FCHVs) in Nepal.

---

## 1. Tech Stack

| Layer       | Technology               |
|-------------|--------------------------|
| Backend     | Django 5.1 (Python)      |
| Database    | SQLite (development)     |
| Frontend    | Django Templates + CSS   |
| Auth        | Custom User model (email)|
| Media       | Pillow / ImageField      |

---

## 2. Project Structure

```
codeyatra2.0_access_denied_matritwa/
├── config/                  # Django project settings
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py / asgi.py
│
├── accounts/                # Auth & user management app
│   ├── models.py            # User, PatientProfile, DoctorProfile, FCHVProfile
│   ├── managers.py          # UserManager (email-based auth)
│   ├── forms.py             # Registration, Login, Onboarding forms
│   ├── views.py             # register, login, logout, onboarding
│   ├── urls.py              # /accounts/register|login|logout|onboarding
│   └── admin.py             # Admin for all user models
│
├── main/                    # Core feature app (patient-facing)
│   ├── models.py            # Feature models (pregnancy, vaccinations, etc.)
│   ├── views.py             # All patient feature views
│   ├── urls.py              # Patient feature routes
│   ├── forms.py             # Feature forms
│   ├── utils.py             # Helpers (pregnancy week calc, etc.)
│   ├── context_processors.py
│   └── admin.py
│
├── templates/
│   ├── base.html            # Base layout with navbar, flash msgs, footer
│   ├── nav.html             # Responsive navbar (auth-aware)
│   ├── accounts/            # Auth templates
│   │   ├── register.html
│   │   ├── login.html
│   │   └── onboarding.html
│   └── main/                # Feature templates
│       ├── index.html
│       ├── welcome_dashboard.html
│       ├── pregnancy_timeline.html
│       ├── health_streaks_tracker.html
│       ├── smart_symptom_checker.html
│       ├── report_danger_sign.html
│       ├── danger_sign_reported.html
│       ├── reminders_notifications.html
│       ├── vaccination_details.html
│       ├── vaccination_history.html
│       ├── vaccination_confirmation_success.html
│       ├── emergency_contacts.html
│       ├── emergency_sos_details.html
│       ├── doctor_consultation.html
│       ├── awareness_education.html
│       ├── doctors_dashboard.html
│       └── fchv_dashboard.html
│
├── static/
│   ├── css/style.css
│   ├── images/
│   └── js/
│
├── media/                   # User-uploaded files
├── db.sqlite3
├── manage.py
└── requirements.txt
```

---

## 3. User Roles

| Role    | Description                                     | Dashboard             |
|---------|------------------------------------------------|------------------------|
| patient | Pregnant women — primary users                 | welcome_dashboard      |
| doctor  | Doctors — monitor patients, consultations      | doctors_dashboard      |
| fchv    | Female Community Health Volunteers             | fchv_dashboard         |
| admin   | System admins                                  | Django admin           |

---

## 4. Feature Map — Pregnant Women (Patient)

### 4.1 Welcome Dashboard
- Overview of pregnancy progress (current week, trimester)
- Quick-access cards: Timeline, Vaccinations, Symptoms, Emergency
- Upcoming reminders preview
- Health streak status

### 4.2 Pregnancy Timeline
- Week-by-week pregnancy tracker (calculated from LMP)
- Current week highlight with baby development info
- Milestone markers (ultrasounds, check-ups)
- Trimester progress bar

### 4.3 Health Streaks Tracker
- Daily habits: took vitamins, exercised, drank water, ate balanced meal
- Streak counter & calendar view
- Motivational messages

### 4.4 Smart Symptom Checker
- Log symptoms with severity (1-5)
- Pre-defined symptom list common in pregnancy
- Severity-based recommendations
- History of logged symptoms

### 4.5 Report Danger Sign
- Quick form to report danger signs (heavy bleeding, severe headache, etc.)
- Sends alert (logged for FCHV/doctor to see)
- Confirmation page after submission

### 4.6 Reminders & Notifications
- Upcoming ANC (antenatal care) appointments
- Medication / supplement reminders
- Vaccination due dates
- Custom reminders

### 4.7 Vaccination Tracker
- Standard Nepal immunization schedule for pregnancy (TT vaccines)
- Mark vaccinations as completed
- History of past vaccinations

### 4.8 Emergency Contacts
- Add/edit emergency contacts (family, nearest health facility, ambulance)
- One-tap SOS with details screen

### 4.9 Doctor Consultation
- Request consultation with available doctors
- Consultation history

### 4.10 Awareness & Education
- Educational content cards (nutrition, exercise, danger signs, birth prep)
- Categories: Trimester 1 / 2 / 3, Postpartum

---

## 5. Models Overview (main app — Patient Features)

| Model               | Purpose                                          |
|---------------------|--------------------------------------------------|
| PregnancyMilestone  | Week-by-week milestones + tips                   |
| HealthStreak        | Daily health habit log                           |
| SymptomLog          | Patient-reported symptoms with severity          |
| DangerSignReport    | Urgent danger sign submissions                   |
| Reminder            | ANC appointments, medication, custom reminders   |
| Vaccination         | Vaccination schedule & records                   |
| EmergencyContact    | Patient's emergency contacts                     |
| ConsultationRequest | Doctor consultation requests                     |
| EducationContent    | Health education articles / tips                 |

---

## 6. URL Schema (Patient)

| URL                          | View                    | Name                    |
|------------------------------|-------------------------|-------------------------|
| `/`                          | index                   | index                   |
| `/dashboard/`                | welcome_dashboard       | dashboard               |
| `/pregnancy/timeline/`       | pregnancy_timeline      | pregnancy_timeline      |
| `/health/streaks/`           | health_streaks          | health_streaks          |
| `/health/streaks/log/`       | log_health_streak       | log_health_streak       |
| `/symptoms/checker/`         | symptom_checker         | symptom_checker         |
| `/symptoms/log/`             | log_symptom             | log_symptom             |
| `/danger-signs/report/`      | report_danger_sign      | report_danger_sign      |
| `/danger-signs/reported/`    | danger_sign_reported    | danger_sign_reported    |
| `/reminders/`                | reminders               | reminders               |
| `/vaccinations/`             | vaccination_details     | vaccination_details     |
| `/vaccinations/history/`     | vaccination_history     | vaccination_history     |
| `/vaccinations/confirm/<id>` | confirm_vaccination     | confirm_vaccination     |
| `/emergency/contacts/`       | emergency_contacts      | emergency_contacts      |
| `/emergency/sos/`            | emergency_sos           | emergency_sos           |
| `/consultation/`             | doctor_consultation     | doctor_consultation     |
| `/education/`                | awareness_education     | awareness_education     |

---

## 7. Implementation Status

- [x] Custom User model (email-based auth)
- [x] Registration, Login, Logout
- [x] Role-based onboarding (Patient, Doctor, FCHV)
- [x] Base template with navbar & flash messages
- [ ] Patient dashboard
- [ ] Pregnancy timeline
- [ ] Health streaks tracker
- [ ] Smart symptom checker
- [ ] Danger sign reporting
- [ ] Reminders & notifications
- [ ] Vaccination tracker
- [ ] Emergency contacts & SOS
- [ ] Doctor consultation
- [ ] Awareness & education
- [ ] Doctor dashboard
- [ ] FCHV dashboard

---

## 8. Branch Strategy

| Branch | Purpose                     |
|--------|-----------------------------|
| main   | Production-ready code       |
| dev    | Development integration     |
| auth   | Authentication features     |
| patient-features | Patient-facing features |
