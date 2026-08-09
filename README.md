# 🏠 JBS Residency

A **Flask**-based web application for managing residency (PG) rent payments. It connects two roles — **Owners** (who run the residency and collect rent) and **Customers** (the residents) — and lets both sides track monthly rent, confirm payments, and manage their accounts through a clean, dark-themed dashboard.

> **Note:** This project was originally built with Node.js/Express and EJS templates, then fully converted to **Python + Flask + Jinja2**.

---

## ✨ Features

### 🏨 Owner Side
- **Registration** — Create an account with residency name, UPI ID, QR code image, and login credentials (password hashed with bcrypt).
- **Login** — Secure bcrypt password verification.
- **Forgot Password** — Verify identity using Residency Name + User ID + Mobile No, then reset the password.
- **Dashboard** — View total customer count and total confirmed rent amount.
- **Customer Management** — List all customers, view detailed profiles, and delete customers permanently.
- **Payment Confirmation** — Confirm each month's payment as *paid* or *unpaid*.
- **Progressive Month List** — Months are generated progressively based on the customer's join date and current confirmed period.
- **Owner Details** — Update UPI ID, mobile number, QR code, and profile photo anytime.
- **Delete Account** — Permanently remove account (cascades to customers/payments and cleans up uploaded files).

### 👤 Customer Side
- **Registration** — Select your owner/residency, provide personal details, upload Aadhaar front/back images (required) and a profile photo (optional), and set room/rent configuration.
- **Auto-Generated Customer ID** — A unique ID (e.g., `JBSRESIXXXXXXXX`) is generated from name + Aadhaar + timestamp.
- **Login** — Sign in using **Customer ID + DOB + CAPTCHA**.
- **Forgot ID** — Recover your Customer ID using DOB + Aadhaar No + Mobile No.
- **Dashboard** — View your profile, owner info, and photo.
- **Payments** — See a progressive month-by-month rent list and mark each month as *paid* or *unpaid*.
- **Profile Management** — Update name/mobile, upload or change profile photo.
- **Exit Residence** — Mark yourself as exited from the residence.
- **Delete Account** — Remove your account (logged out after deletion).

### 🔒 Security & UX
- bcrypt password hashing for owners.
- CAPTCHA protection on customer login.
- 6 MB upload size limit.
- No-cache headers + bfcache-prevention script to protect private pages after logout/register.
- Foreign-key cascade deletes and uploaded-file cleanup on account deletion.

---

## 🛠️ Tech Stack

| Layer       | Technology                          |
|-------------|-------------------------------------|
| Backend     | Python 3 + Flask 3.1.0               |
| Password    | bcrypt 4.0.1                         |
| File upload | Werkzeug 3.1.3 (`secure_filename`)   |
| Database    | SQLite (`jbs.db`)                    |
| Templates   | Jinja2 (converted from EJS)          |
| Frontend    | HTML, CSS (dark theme, responsive)   |

---

## 📁 Project Structure

```
jbs-residency/
├── README.md
└── flask_app/
    ├── app.py                 # Main Flask application (all routes & logic)
    ├── requirements.txt      # Python dependencies
    ├── TODO.md               # Conversion progress & deployment notes
    ├── jbs.db                # SQLite database (auto-created)
    ├── templates/            # Jinja2 HTML templates
    │   ├── home.html
    │   ├── owner_*.html      # Owner login, register, dashboard, details, etc.
    │   ├── customer_*.html   # Customer login, register, dashboard, payments, etc.
    │   └── partials/         # Reusable partial templates (e.g., footer.html)
    └── uploads/              # Uploaded files (QR codes, Aadhaar, photos)
        ├── misc/
        ├── owner_qr/
        └── profiles/
```

---

## 🚀 Installation & Setup

### 1. Navigate to the app directory
```bash
cd flask_app
```

### 2. Create and activate a virtual environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the application
```bash
python app.py
```

The app will start at **http://localhost:5000** (host `0.0.0.0`, port `5000`).

---

## ⚙️ Environment Configuration

The app uses a secret key for Flask sessions. You can override it via an environment variable:

```bash
export FLASK_SECRET="your-very-secret-key"   # macOS / Linux
set FLASK_SECRET="your-very-secret-key"      # Windows (CMD)
```

If not set, a default development secret is used (`change_this_secret_jbs_residency_2025`). **Always set a strong custom secret in production.**

---

## 🧭 Usage Guide

### As an Owner
1. Go to **Owner Registration** and create your account (residency name, UPI ID, QR code, user ID & password).
2. Log in with your User ID & password.
3. From the dashboard, view your customers and total confirmed rent.
4. In **Customers**, select a customer to see their monthly payment list and confirm each month's payment status.
5. Update your UPI ID / QR / profile photo from **Owner Details** anytime.

### As a Customer
1. Go to **Customer Registration**, select your owner's residency, fill in your details, and upload Aadhaar front/back images.
2. Note your **Customer ID** shown after successful registration.
3. Log in using **Customer ID + DOB + CAPTCHA**.
4. From the **Payments** page, mark each month as *paid* or *unpaid*.
5. Manage your profile photo/details or exit/delete your account from the dashboard.

---

## ☁️ Deployment Notes (PythonAnywhere)

This app is designed to run on PythonAnywhere:

1. Push the project to a Git repository.
2. Create a Web app on PythonAnywhere (Python 3.x, manual config).
3. Point the **WSGI file** to `app.py`.
4. Set the `FLASK_SECRET` environment variable.
5. Test the live deployment.

See `flask_app/TODO.md` for the full deployment checklist.

---

## 🗄️ Database

The database (`jbs.db`) is created automatically on first run. It contains three tables:

- **`owners`** — residency owner account details, UPI & QR info, credentials.
- **`customers`** — resident details, Aadhaar/photo paths, room rent configuration, status.
- **`payments`** — one row per customer per month (year + month), with payment status, customer choice, and owner confirmation.

12 months of payment rows are seeded automatically when a customer registers, and rows are generated progressively as periods advance.

---

## 🧪 Troubleshooting

- **Port already in use?** Change the port in `app.py` (`app.run(host='0.0.0.0', port=5000, ...)`).
- **Upload fails?** Ensure files are under the 6 MB limit.
- **Database schema updates?** The app runs `ALTER TABLE` migrations in `init_db()` where needed.

---

## 📄 License

This project is for educational/personal use. All rights reserved to the project owner.

---

**JBS Residency** © 2026 — Owner & Customer Management.
