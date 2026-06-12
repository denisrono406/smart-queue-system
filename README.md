# Smart Queue Management System

Enterprise-grade multi-tenant queue management system built with Flask, supporting schools, hospitals, banks, universities, and any service-based organization.

## Features

- **Multi-Tenant**: Multiple organizations with isolated data
- **4 User Roles**: Super Admin, Org Admin, Staff, Customer
- **Dynamic Service Desks**: Create/edit/delete desks from dashboard (not hardcoded)
- **Queue Management**: Join, track, and manage queues in real-time
- **Priority Queues**: Emergency, PWD, Pregnant, Senior, VIP, Normal
- **QR Code Generation**: Auto-generated QR codes on tickets with verification
- **Real-Time Updates**: SocketIO-powered live position and status updates
- **Reports**: Daily, weekly, monthly, desk performance, queue performance (PDF/Excel)
- **Dark Mode**: Toggle between light and dark themes
- **Password Policy**: Configurable minimum length, uppercase, lowercase, numbers, special chars
- **Authentication**: Login with email or phone, Remember Me, Forgot/Reset Password

## Tech Stack

- Python 3.10+ / Flask
- SQLAlchemy ORM / PostgreSQL (Supabase)
- Flask-SocketIO (real-time)
- Flask-Login (authentication)
- Flask-WTF (CSRF + forms)
- Bootstrap 5 (UI)
- QR Code generation (qrcode library)
- ReportLab / openpyxl (PDF/Excel reports)

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Seed the database (creates tables + sample data)
python seed.py

# Run the application
python run.py
```

The app runs at http://localhost:5000

## Test Login Credentials

The Smart Queue Management System includes pre-configured user accounts for testing and evaluation purposes.

### Super Admin
- Email: admin@queueapp.com
- Password: Admin@123

### Organization Admin
- Email: admin@city-general-hospital.com
- Password: Admin@123

### Staff
- Email: staff.reception@city-general-hospital.com
- Password: Staff@123

### Customer
- Email: customer@example.com
- Password: Customer@123

## Access Instructions

1. Open the application URL.
2. Sign in using any of the credentials above.
3. Each account provides access to features based on its assigned role.
4. The Super Admin account has full system access for evaluation purposes.

## Organization Types Supported

School, University, College, Hospital, Bank, Government Office, SACCO, Insurance Company, NGO, Utility Company, and any service-based organization.

## Project Structure

```
app/
  __init__.py          # App factory
  config.py            # Configuration classes
  extensions.py        # Flask extensions
  models.py            # SQLAlchemy models
  forms.py             # WTForms
  utils.py             # Utilities (password, QR, notifications)
  auth.py              # Auth blueprint
  admin.py             # Admin blueprint
  user.py              # Customer blueprint
  staff.py             # Staff blueprint
  reports.py           # Reports blueprint
  queue_ws.py          # SocketIO events
  main_routes.py       # Core routes
  templates/           # Jinja2 templates
  static/
    css/style.css      # Custom styles
    js/app.js          # Client-side JS
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| FLASK_ENV | Environment | development |
| SECRET_KEY | Flask secret | dev-secret-key |
| DATABASE_URL | PostgreSQL URL | sqlite fallback |
| MAIL_SERVER | SMTP server | smtp.gmail.com |
| MAIL_USERNAME | SMTP user | - |
| MAIL_PASSWORD | SMTP password | - |
| TWILIO_ACCOUNT_SID | Twilio SID | - |
| TWILIO_AUTH_TOKEN | Twilio token | - |
| TWILIO_PHONE_NUMBER | Twilio number | - |

## Password Policy (Configurable per Organization)

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character
- All configurable by org admin in Settings

## Ticket Format

Tickets use desk prefix + sequential number:
- Reception Desk: REC001, REC002...
- Loans Desk: LOA001, LOA002...
- Admissions Desk: ADM001, ADM002...

## Priority Queue Order

1. Emergency
2. Persons with Disabilities (PWD)
3. Pregnant Women
4. Senior Citizens
5. VIP
6. Normal


## Future Enhancements
- *Notifications**: Email, SMS, and browser notifications
- Email Alerts
- QR-code based ticket check-in
- Queue analytics dashboard