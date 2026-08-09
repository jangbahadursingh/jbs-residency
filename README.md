# 🏠 JBS Residency

A **Flask**-based web application for managing residency (PG) rent payments. It connects two roles — **Owners** (who run the residency and collect rent) and **Customers** (the residents) — and lets both sides track monthly rent, confirm payments, and manage their accounts through a clean, dark-themed dashboard.

**Live Demo:**[https://jbsresidency.pythonanywhere.com/]

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

---

## 🛠️ Tech Stack

| Layer       | Technology                          |
|-------------|-------------------------------------|
| Backend     | Python 3 + Flask 3.1.0               |
| Password    | bcrypt 4.0.1                         |
| File upload | Werkzeug 3.1.3 (`secure_filename`)   |
| Database    | SQLite (`database_filename`)                    |
| Templates   | Jinja2 (converted from EJS)          |
| Frontend    | HTML, CSS (dark theme, responsive)   |


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

The app will start at **http://localhost:**.

---

## ⚙️ Environment Configuration

The app uses a secret key for Flask sessions. You can override it via an environment variable:

```bash
export FLASK_SECRET="your-very-secret-key"   # macOS / Linux
set FLASK_SECRET="your-very-secret-key"      # Windows (CMD)
```


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

## 📄 License

This project is for educational/personal use. All rights reserved to the project owner.

---

**JBS Residency** © 2026 — Owner & Customer Management.
