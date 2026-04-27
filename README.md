# My Wallet — Personal Finance Manager

A modern, industry-grade personal finance web application built with Django and Tailwind CSS.

## ✨ Features

- **Secure Authentication** — Login, signup, logout with per-user private data
- **Dashboard** — Month/year selector with income, expense & balance cards + charts
- **Transaction Management** — Add, edit, delete income & expense transactions
- **Transactions History** — Bank statement style table with filters
- **Analytics** — Annual trend chart, expense & income breakdown pie charts
- **Modern UI** — Dark fintech aesthetic, responsive sidebar, animated transitions

## 🚀 Quick Start

### 1. Set up a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run database migrations

```bash
python manage.py migrate
```

### 4. (Optional) Load demo data

```bash
python manage.py seed_demo
# Creates user: demo / demo1234 with 3 months of sample transactions
```

### 5. Create your own admin (optional)

```bash
python manage.py createsuperuser
```

### 6. Start the development server

```bash
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

## 📁 Project Structure

```
fintrack/
├── fintrack/               # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                   # Main application
│   ├── models.py           # Transaction model
│   ├── views.py            # All views
│   ├── forms.py            # Income & Expense forms
│   ├── urls.py             # URL routing
│   ├── admin.py            # Admin registration
│   ├── templates/core/     # HTML templates
│   │   ├── base.html       # Base layout with sidebar
│   │   ├── login.html
│   │   ├── signup.html
│   │   ├── dashboard.html
│   │   ├── add_income.html
│   │   ├── add_expense.html
│   │   ├── transactions.html
│   │   ├── edit_transaction.html
│   │   ├── delete_confirm.html
│   │   └── analytics.html
│   └── management/
│       └── commands/
│           └── seed_demo.py
├── manage.py
└── requirements.txt
```

## 🎨 Tech Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Backend    | Django 5.0                          |
| Database   | SQLite (dev) / PostgreSQL (prod)    |
| Frontend   | Tailwind CSS (CDN) + Vanilla JS     |
| Charts     | Chart.js 4.4                        |
| Fonts      | DM Sans + DM Mono (Google Fonts)    |

## 🔐 Production Notes

Before deploying to production:

1. Change `SECRET_KEY` in `settings.py`
2. Set `DEBUG = False`
3. Update `ALLOWED_HOSTS`
4. Use PostgreSQL or another production DB
5. Set up proper static file serving

## 📝 Income Sources
Salary, Freelance, Gift, Investment, Business, Rental, Bonus, Refund, Other

## 💸 Expense Categories
Food & Dining, Transport, Rent & Housing, Shopping, Healthcare, Entertainment, Utilities, Education, Travel, Subscriptions, Insurance, Savings, Other
