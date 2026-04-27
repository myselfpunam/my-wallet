# My Wallet — Personal Finance Manager

A full-featured, production-ready personal finance web application built with **Django 5** and **Tailwind CSS**. Designed to give individuals complete visibility and control over their money — income, expenses, loans, and receivables — all in one clean, dark-themed dashboard.

---

## Project Aim

Most people track money in scattered notes, spreadsheets, or don't track it at all. **My Wallet** solves this by providing a single, private place to:

- Record every rupee that comes in and goes out
- Track money you've borrowed (Loans) and money others owe you (Receivables / Pawna)
- Visualise monthly trends and spending patterns through charts
- Get a real-time financial snapshot on the dashboard every time you log in

The goal is a tool that feels like a personal finance app you'd actually want to use — fast, minimal, and honest about your money.

---

## Features

### Authentication & Security
- Signup with **email OTP verification** (6-digit code, 10-min expiry)
- Login / Logout
- **Forgot password** flow with OTP reset
- Rate-limited OTP resends (max 3) and attempts (max 5)
- Per-user data isolation — no user can see another's data
- Secure password storage (Django PBKDF2-SHA256)

### Dashboard
- Month / year selector to browse any period
- Stat cards: Total Income, Total Expenses, Monthly Balance, Overall Balance, Active Lenders, Outstanding Loan, Total Receivables
- **Income vs Expense** doughnut chart for the selected period
- **6-Month Trend** bar chart (income & expense side by side)
- **Loan vs Receivables** bar chart comparing what you owe vs what others owe you
- 5 most recent transactions at a glance

### Income & Expense Tracking
- Add income with source category (Salary, Freelance, Gift, Investment, Business, Rental, Bonus, Refund, Other)
- Add expense with category (Food & Dining, Transport, Rent & Housing, Shopping, Healthcare, Entertainment, Utilities, Education, Travel, Subscriptions, Insurance, Savings, Other)
- Edit and delete any transaction
- Full transaction history with month/year filter and income/expense toggle

### Analytics
- Annual overview line chart (all 12 months)
- Expense breakdown doughnut chart with percentage legend
- Income breakdown doughnut chart with percentage legend
- Monthly stat cards (income, expense, balance)

### Loan Management
- Add loans (who you borrowed from, amount, date, note)
- Record repayments (partial payments supported)
- Filter loans: All / Active (still owed) / Paid off
- Summary strip: Total Loaned, Total Paid, Outstanding
- Full payment history table

### Receivables Management (Pawna)
- Add receivables (who owes you money, amount, date, note)
- Record payments received (partial payments supported)
- Filter: All / Pending / Fully Received
- Summary strip: Total Given, Total Received, Outstanding
- Full repayment history table
- Dashboard card shows total outstanding receivables

### User Profile
- View and edit profile (first name, last name, address, phone)
- Upload profile picture (JPG/PNG, max 5 MB)
- Change password with current-password verification
- Delete profile picture

---

## Tech Stack

| Layer        | Technology                            |
|--------------|---------------------------------------|
| Backend      | Django 5.2                            |
| Database     | SQLite (dev) / PostgreSQL (prod)      |
| Frontend     | Tailwind CSS (CDN) + Vanilla JS       |
| Charts       | Chart.js 4.4                          |
| Fonts        | DM Sans + DM Mono (Google Fonts)      |
| Email        | SMTP (Gmail / Outlook / SendGrid)     |
| Static files | WhiteNoise                            |
| Forms        | django-crispy-forms + crispy-tailwind |

---

## Setup Guide

### Prerequisites

- Python 3.10 or higher
- pip
- Git

---

### 1. Clone the repository

```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```

---

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows (Command Prompt)
venv\Scripts\activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

---

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Configure environment variables

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and set the following:

```env
# Django core
SECRET_KEY=your-secret-key-here          # generate one at https://djecrety.ir/
DEBUG=True                                # set to False in production
ALLOWED_HOSTS=localhost,127.0.0.1

# Email — pick one of the options below

# Option A: Console backend (prints emails to terminal, no SMTP needed — great for development)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Option B: Gmail SMTP (for real OTP emails)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-gmail@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-app-password   # see Gmail App Passwords below
DEFAULT_FROM_EMAIL=My Wallet <your-gmail@gmail.com>

# OTP settings (optional — defaults shown)
OTP_EXPIRY_MINUTES=10
OTP_MAX_ATTEMPTS=5
OTP_MAX_RESENDS=3
```

#### Setting up a Gmail App Password

1. Enable **2-Step Verification** on your Google account
2. Go to [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Create an App Password for **Mail**
4. Copy the 16-character code (no spaces) into `EMAIL_HOST_PASSWORD`

> For Outlook, Yahoo, or SendGrid — see the `.env.example` file for the correct `EMAIL_HOST` and `EMAIL_PORT` values.

---

### 5. Run database migrations

```bash
python manage.py migrate
```

---

### 6. Create an admin account (optional)

```bash
python manage.py createsuperuser
```

Access the Django admin panel at [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)

---

### 7. Start the development server

```bash
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser and sign up for a new account.

---

## Project Structure

```
fintrack/
├── fintrack/                     # Django project configuration
│   ├── settings.py               # All settings (reads from .env)
│   ├── urls.py                   # Root URL routing
│   └── wsgi.py
│
├── core/                         # Main application
│   ├── models.py                 # All database models
│   │                             #   Transaction, Loan, LoanPayment,
│   │                             #   Receivable, ReceivablePayment,
│   │                             #   UserProfile, PasswordResetToken
│   ├── views.py                  # All view logic
│   ├── forms.py                  # Django forms for every feature
│   ├── urls.py                   # App-level URL routing
│   ├── admin.py                  # Django admin registrations
│   ├── utils.py                  # Email helper functions
│   ├── signals.py                # Post-save signal (auto-create profile)
│   ├── apps.py                   # App config
│   │
│   ├── templates/core/
│   │   ├── base.html             # Sidebar layout, flash messages, JS
│   │   ├── login.html
│   │   ├── signup.html
│   │   ├── signup_verify_otp.html
│   │   ├── forgot_password.html
│   │   ├── verify_otp.html
│   │   ├── reset_password.html
│   │   ├── dashboard.html        # Main dashboard with charts
│   │   ├── add_income.html
│   │   ├── add_expense.html
│   │   ├── transactions.html
│   │   ├── edit_transaction.html
│   │   ├── delete_confirm.html
│   │   ├── analytics.html
│   │   ├── loans.html
│   │   ├── add_loan.html
│   │   ├── loan_payment.html
│   │   ├── edit_loan.html
│   │   ├── delete_loan_confirm.html
│   │   ├── receivables.html      # Receivables overview + history
│   │   ├── add_receivable.html
│   │   ├── receivable_payment.html
│   │   ├── edit_receivable.html
│   │   ├── delete_receivable_confirm.html
│   │   ├── profile.html
│   │   ├── edit_profile.html
│   │   └── change_password.html
│   │
│   └── migrations/               # Auto-generated database migrations
│
├── media/                        # Uploaded profile pictures (git-ignored)
├── .env                          # Your local secrets (git-ignored)
├── .env.example                  # Template for environment variables
├── .gitignore
├── manage.py
└── requirements.txt
```

---

## URL Reference

| URL | Page |
|-----|------|
| `/` | Login |
| `/signup/` | Register |
| `/dashboard/` | Main dashboard |
| `/add-income/` | Add income |
| `/add-expense/` | Add expense |
| `/transactions/` | Transaction history |
| `/analytics/` | Charts & analytics |
| `/loans/` | Loan overview |
| `/add-loan/` | Add loan |
| `/loan-payment/` | Record loan repayment |
| `/receivables/` | Receivables overview |
| `/add-receivable/` | Add receivable |
| `/receivable-payment/` | Record payment received |
| `/profile/` | User profile |
| `/admin/` | Django admin panel |

---

## Production Deployment Checklist

Before going live, make these changes in your `.env` and `settings.py`:

```env
DEBUG=False
SECRET_KEY=a-long-random-50-char-string
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

- Switch database to **PostgreSQL** (update `DATABASES` in `settings.py`)
- Run `python manage.py collectstatic` and serve `/staticfiles/` via your web server
- Use **Gunicorn** or **uWSGI** as the application server
- Put **Nginx** or **Caddy** in front as a reverse proxy
- Set `SECURE_SSL_REDIRECT = True` and use HTTPS

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | Yes | — | Django secret key |
| `DEBUG` | No | `True` | Debug mode |
| `ALLOWED_HOSTS` | No | `*` | Comma-separated allowed hosts |
| `EMAIL_BACKEND` | No | SMTP | Email backend class |
| `EMAIL_HOST` | No | `smtp.gmail.com` | SMTP server |
| `EMAIL_PORT` | No | `587` | SMTP port |
| `EMAIL_USE_TLS` | No | `True` | Use STARTTLS |
| `EMAIL_HOST_USER` | No | `""` | SMTP username |
| `EMAIL_HOST_PASSWORD` | No | `""` | SMTP password / app password |
| `DEFAULT_FROM_EMAIL` | No | derived | From address in emails |
| `OTP_EXPIRY_MINUTES` | No | `10` | OTP validity window |
| `OTP_MAX_ATTEMPTS` | No | `5` | Wrong guesses before OTP locks |
| `OTP_MAX_RESENDS` | No | `3` | Max OTP resend requests |

---

## Income Sources

Salary · Freelance · Gift · Investment · Business · Rental Income · Bonus · Refund · Other

## Expense Categories

Food & Dining · Transport · Rent & Housing · Shopping · Healthcare · Entertainment · Utilities · Education · Travel · Subscriptions · Insurance · Savings · Other

---

## License

This project is open source and available under the [MIT License](https://opensource.org/licenses/MIT).
