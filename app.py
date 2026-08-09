import os
import sqlite3
import datetime
import random
import time
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, send_from_directory, jsonify, abort
)
from werkzeug.utils import secure_filename
import bcrypt

# ---------------------------------------------------------------------------
# App Setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'change_this_secret_jbs_residency_2025')

app.config['MAX_CONTENT_LENGTH'] = 6 * 1024 * 1024  # 6 MB
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


BF_CACHE_SCRIPT = """
<script>
  // Prevent the browser from showing a cached (bfcache) version of a page
  // when the user presses the back button after logout/register/login.
  // event.persisted is true when the page is restored from back-forward cache.
  window.addEventListener('pageshow', function (event) {
    if (event.persisted) {
      window.location.reload();
    }
  });
</script>
"""


@app.after_request
def add_no_cache_headers(response):
    """Prevent the browser from caching pages so the back button after
    logout/register/login does not show previously-visited private pages
    (dashboard, register form with filled details, etc.)."""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    # Inject bfcache-prevention script into HTML responses so the back button
    # triggers a reload and the server redirects to the correct page.
    if response.content_type == 'text/html' and isinstance(response.data, bytes):
        try:
            html = response.get_data(as_text=True)
            if '</body>' in html and '<script' not in BF_CACHE_SCRIPT.split('\n')[0]:
                html = html.replace('</body>', BF_CACHE_SCRIPT + '\n</body>')
                response.set_data(html)
        except Exception:
            pass
    return response

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jbs.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS owners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_name TEXT NOT NULL,
            mobile_no TEXT NOT NULL,
            upi_id TEXT NOT NULL,
            qr_code_path TEXT,
            residency_name TEXT NOT NULL,
            user_id TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            customer_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            father_name TEXT,
            dob TEXT,
            aadhar_no TEXT,
            aadhar_front_path TEXT,
            aadhar_back_path TEXT,
            customer_photo_path TEXT,
            mobile_no TEXT,
            address TEXT,
            occupation TEXT,
            room_rent_type TEXT NOT NULL,
            room_rent_monthly INTEGER NOT NULL,
            security_money INTEGER NOT NULL,
            room_rent_image_path TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(owner_id) REFERENCES owners(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'unpaid',
            customer_choice TEXT NOT NULL DEFAULT 'pending',
            customer_payment_note TEXT,
            owner_confirmed INTEGER NOT NULL DEFAULT 0,
            owner_updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            UNIQUE(owner_id, customer_id, year, month),
            FOREIGN KEY(owner_id) REFERENCES owners(id) ON DELETE CASCADE,
            FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
        );
    """)

    try:
        conn.execute("ALTER TABLE customers ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE owners ADD COLUMN profile_photo_path TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


init_db()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def new_captcha():
    return ''.join(random.choices('0123456789', k=6))


def save_upload(file_obj, subdir='misc'):
    if not file_obj or file_obj.filename == '':
        return None
    dest_dir = os.path.join(UPLOAD_FOLDER, subdir)
    os.makedirs(dest_dir, exist_ok=True)
    ext = os.path.splitext(file_obj.filename)[1].lower() or '.jpg'
    safe_name = secure_filename(file_obj.filename).replace(' ', '_')
    if not safe_name:
        safe_name = f"file{ext}"
    filename = f"{int(time.time() * 1000)}_{safe_name}"
    filename = "".join(c for c in filename if c.isalnum() or c in '._-')
    if not filename.lower().endswith(ext):
        filename += ext
    filepath = os.path.join(dest_dir, filename)
    file_obj.save(filepath)
    rel = os.path.relpath(filepath, UPLOAD_FOLDER).replace('\\', '/')
    return rel


def customer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'customer' not in session:
            return redirect(url_for('customer_login'))
        return f(*args, **kwargs)
    return decorated


def owner_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'owner' not in session:
            return redirect(url_for('owner_login'))
        return f(*args, **kwargs)
    return decorated


def current_year():
    return datetime.datetime.now().year

app.jinja_env.globals['current_year'] = current_year

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    session.pop('customer', None)
    return render_template('home.html')


@app.route('/customer/captcha-refresh')
def customer_captcha_refresh():
    code = new_captcha()
    session['captcha'] = code
    return jsonify({'captcha': code})


@app.route('/customer/login', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'GET':
        code = new_captcha()
        session['captcha'] = code
        return render_template('customer_login.html', captchaValue=code, error=None)

    customer_id = request.form.get('customer_id', '').strip()
    dob = request.form.get('dob', '').strip()
    captcha = request.form.get('captcha', '').strip()
    expected = session.pop('captcha', None)

    if not expected or captcha != expected:
        new_code = new_captcha()
        session['captcha'] = new_code
        return render_template('customer_login.html', captchaValue=new_code, error='Invalid captcha')

    conn = get_db()
    customer = conn.execute(
        'SELECT * FROM customers WHERE customer_id = ?', (customer_id,)
    ).fetchone()
    conn.close()

    if not customer:
        new_code = new_captcha()
        session['captcha'] = new_code
        return render_template('customer_login.html', captchaValue=new_code, error='Customer not found')

    if not customer['dob'] or customer['dob'] != dob:
        new_code = new_captcha()
        session['captcha'] = new_code
        return render_template('customer_login.html', captchaValue=new_code, error='DOB mismatch')

    if customer['status'] == 'deleted_by_customer':
        new_code = new_captcha()
        session['captcha'] = new_code
        return render_template('customer_login.html', captchaValue=new_code, error='This account has been deleted. Contact your owner for assistance.')

    session['customer'] = {
        'customerDbId': customer['id'],
        'customer_id': customer['customer_id'],
        'owner_id': customer['owner_id']
    }
    return redirect(url_for('customer_dashboard'))


@app.route('/customer/logout')
def customer_logout():
    session.pop('customer', None)
    return redirect(url_for('customer_login'))


@app.route('/customer/forgot-id', methods=['GET', 'POST'])
def customer_forgot_id():
    if request.method == 'GET':
        return render_template('customer_forgot_id.html', error=None, recovered_id=None)

    dob = request.form.get('dob', '').strip()
    aadhar_no = request.form.get('aadhar_no', '').strip()
    mobile_no = request.form.get('mobile_no', '').strip()

    if not dob or not aadhar_no or not mobile_no:
        return render_template('customer_forgot_id.html', error='All fields are required.', recovered_id=None)

    conn = get_db()
    customer = conn.execute(
        'SELECT customer_id FROM customers WHERE dob = ? AND aadhar_no = ? AND mobile_no = ?',
        (dob, aadhar_no, mobile_no)
    ).fetchone()
    conn.close()

    if not customer:
        return render_template('customer_forgot_id.html', error='No matching customer found. Please verify your details.', recovered_id=None)

    return render_template('customer_forgot_id.html', error=None, recovered_id=customer['customer_id'])


@app.route('/owner/login', methods=['GET', 'POST'])
def owner_login():
    if request.method == 'GET':
        return render_template('owner_login.html', error=None)

    user_id = request.form.get('user_id', '').strip()
    password = request.form.get('password', '')

    conn = get_db()
    owner = conn.execute('SELECT * FROM owners WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()

    if not owner:
        return render_template('owner_login.html', error='Invalid credentials')
    try:
        pw_ok = bcrypt.checkpw(password.encode('utf-8'), owner['password_hash'].encode('utf-8'))
    except Exception:
        pw_ok = False
    if not pw_ok:
        return render_template('owner_login.html', error='Invalid credentials')

    session['owner'] = {
        'ownerDbId': owner['id'],
        'owner_name': owner['owner_name'],
        'residency_name': owner['residency_name']
    }
    return redirect(url_for('owner_dashboard'))


@app.route('/owner/logout')
def owner_logout():
    session.pop('owner', None)
    return redirect(url_for('owner_login'))


@app.route('/owner/delete-account', methods=['POST'])
@owner_required
def owner_delete_account():
    owner_db_id = session['owner']['ownerDbId']
    conn = get_db()

    # Gather owner's uploaded file paths for cleanup
    owner_row = conn.execute('SELECT * FROM owners WHERE id = ?', (owner_db_id,)).fetchone()
    customers = conn.execute(
        'SELECT customer_photo_path, aadhar_front_path, aadhar_back_path, room_rent_image_path FROM customers WHERE owner_id = ?',
        (owner_db_id,)
    ).fetchall()

    file_paths = []
    if owner_row:
        for f in ('qr_code_path', 'profile_photo_path'):
            if owner_row[f]:
                file_paths.append(owner_row[f])
    for c in customers:
        for f in ('customer_photo_path', 'aadhar_front_path', 'aadhar_back_path', 'room_rent_image_path'):
            if c[f]:
                file_paths.append(c[f])

    # Delete the owner (cascades to customers and payments via FK ON DELETE CASCADE)
    conn.execute('DELETE FROM owners WHERE id = ?', (owner_db_id,))
    conn.commit()
    conn.close()

    # Remove uploaded files from disk
    for rel in file_paths:
        try:
            full = os.path.join(UPLOAD_FOLDER, rel)
            if os.path.isfile(full):
                os.remove(full)
        except Exception:
            pass

    # Clear owner session so they are logged out
    session.pop('owner', None)
    return redirect(url_for('owner_login'))


@app.route('/owner/forgot-password', methods=['GET', 'POST'])
def owner_forgot_password():
    if request.method == 'GET':
        return render_template('owner_forgot_password.html', error=None, verified=False, reset_success=False, owner_name=None)

    residency_name = request.form.get('residency_name', '').strip()
    user_id = request.form.get('user_id', '').strip()
    mobile_no = request.form.get('mobile_no', '').strip()

    if not residency_name or not user_id or not mobile_no:
        return render_template('owner_forgot_password.html', error='All fields are required.', verified=False, reset_success=False, owner_name=None)

    conn = get_db()
    owner = conn.execute(
        'SELECT id, owner_name, residency_name, mobile_no FROM owners WHERE residency_name = ? AND user_id = ? AND mobile_no = ?',
        (residency_name, user_id, mobile_no)
    ).fetchone()
    conn.close()

    if not owner:
        return render_template('owner_forgot_password.html', error='No matching owner found. Please verify your details.', verified=False, reset_success=False, owner_name=None)

    session['reset_owner_id'] = owner['id']
    return render_template('owner_forgot_password.html', error=None, verified=True, reset_success=False, owner_name=owner['owner_name'])


@app.route('/owner/forgot-password/reset', methods=['POST'])
def owner_forgot_password_reset():
    owner_id = session.get('reset_owner_id')
    if not owner_id:
        return render_template('owner_forgot_password.html', error='Session expired. Please start again.', verified=False, reset_success=False, owner_name=None)

    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not new_password or len(new_password) < 6:
        return render_template('owner_forgot_password.html', error='Password must be at least 6 characters.', verified=True, reset_success=False, owner_name=None)

    if new_password != confirm_password:
        return render_template('owner_forgot_password.html', error='Passwords do not match.', verified=True, reset_success=False, owner_name=None)

    password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    conn = get_db()
    conn.execute(
        "UPDATE owners SET password_hash = ?, updated_at = datetime('now','localtime') WHERE id = ?",
        (password_hash, owner_id)
    )
    conn.commit()
    conn.close()

    session.pop('reset_owner_id', None)
    return render_template('owner_forgot_password.html', error=None, verified=False, reset_success=True, owner_name=None)


@app.route('/owner/register', methods=['GET', 'POST'])
def owner_register():
    if request.method == 'GET':
        return render_template('owner_register.html', error=None)

    owner_name = request.form.get('owner_name', '').strip()
    mobile_no = request.form.get('mobile_no', '').strip()
    upi_id = request.form.get('upi_id', '').strip()
    residency_name = request.form.get('residency_name', '').strip()
    user_id = request.form.get('user_id', '').strip()
    password = request.form.get('password', '')

    missing = []
    if not owner_name: missing.append('owner name')
    if not mobile_no: missing.append('mobile no')
    if not upi_id: missing.append('upi id')
    if not residency_name: missing.append('residency name')
    if not user_id: missing.append('user id')
    if not password: missing.append('password')

    if missing:
        return render_template('owner_register.html', error=f'Missing required fields: {", ".join(missing)}')

    qr_file = request.files.get('qr_code')
    if not qr_file or qr_file.filename == '':
        return render_template('owner_register.html', error='QR code image is required')

    qr_rel = save_upload(qr_file, 'owner_qr')
    if not qr_rel:
        return render_template('owner_register.html', error='Failed to upload QR code')

    profile_photo_file = request.files.get('profile_photo')
    profile_photo_rel = save_upload(profile_photo_file, 'profiles') if profile_photo_file and profile_photo_file.filename else None

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    conn = get_db()
    try:
        cur = conn.execute(
            'INSERT INTO owners (owner_name, mobile_no, upi_id, qr_code_path, residency_name, user_id, password_hash, profile_photo_path) VALUES (?,?,?,?,?,?,?,?)',
            (owner_name, mobile_no, upi_id, qr_rel, residency_name, user_id, password_hash, profile_photo_rel)
        )
        conn.commit()
        owner_id = cur.lastrowid
        session['owner'] = {
            'ownerDbId': owner_id,
            'owner_name': owner_name,
            'residency_name': residency_name
        }
        conn.close()
        return redirect(url_for('owner_dashboard'))
    except sqlite3.IntegrityError:
        conn.close()
        return render_template('owner_register.html', error='User ID already exists or invalid data')


@app.route('/customer/register', methods=['GET', 'POST'])
def customer_register():
    conn = get_db()
    if request.method == 'GET':
        owners = conn.execute('SELECT id, residency_name FROM owners ORDER BY id DESC').fetchall()
        conn.close()
        return render_template('customer_register.html', owners=owners, error=None)

    owner_id = request.form.get('owner_id', '').strip()
    name = request.form.get('name', '').strip()
    father_name = request.form.get('father_name', '').strip()
    dob = request.form.get('dob', '').strip()
    aadhar_no = request.form.get('aadhar_no', '').strip()
    mobile_no = request.form.get('mobile_no', '').strip()
    address = request.form.get('address', '').strip()
    occupation = request.form.get('occupation', '').strip()
    room_rent_type = request.form.get('room_rent_type', '').strip()
    room_rent_monthly = request.form.get('room_rent_monthly', '').strip()
    security_money = request.form.get('security_money', '').strip()

    customer_photo_file = request.files.get('customer_photo')

    if not owner_id:
        owners = conn.execute('SELECT id, residency_name FROM owners ORDER BY id DESC').fetchall()
        conn.close()
        return render_template('customer_register.html', owners=owners, error='Owner is required')

    missing = []
    if not name: missing.append('customer name')
    if not father_name: missing.append('father/husband name')
    if not dob: missing.append('dob')
    if not aadhar_no: missing.append('aadhar no')
    if not mobile_no: missing.append('mobile no')
    if not address: missing.append('address')
    if not occupation: missing.append('occupation')

    if missing:
        owners = conn.execute('SELECT id, residency_name FROM owners ORDER BY id DESC').fetchall()
        conn.close()
        return render_template('customer_register.html', owners=owners, error=f'Missing required fields: {", ".join(missing)}')

    front_file = request.files.get('aadhar_front')
    back_file = request.files.get('aadhar_back')

    if not front_file or front_file.filename == '' or not back_file or back_file.filename == '':
        owners = conn.execute('SELECT id, residency_name FROM owners ORDER BY id DESC').fetchall()
        conn.close()
        return render_template('customer_register.html', owners=owners, error='Aadhaar front and back images are required')

    aFrontRel = save_upload(front_file, 'misc')
    aBackRel = save_upload(back_file, 'misc')

    customer_photo_rel = save_upload(customer_photo_file, 'profiles') if customer_photo_file and customer_photo_file.filename else None

    first2 = (name.strip().upper()[:2] or 'NA').ljust(2, 'X')
    last4 = ''.join(c for c in aadhar_no if c.isdigit())[-4:].zfill(4)
    customer_id = f"JBSRESI{first2}{last4}{str(int(time.time() * 1000))[-2:]}"

    try:
        cur = conn.execute(
            '''INSERT INTO customers (
                owner_id, customer_id, name, father_name, dob, aadhar_no,
                aadhar_front_path, aadhar_back_path, customer_photo_path,
                mobile_no, address, occupation,
                room_rent_type, room_rent_monthly, security_money
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (
                int(owner_id), customer_id, name, father_name, dob, aadhar_no,
                aFrontRel, aBackRel, customer_photo_rel or aFrontRel,
                mobile_no, address, occupation,
                room_rent_type, int(room_rent_monthly or 0), int(security_money or 0)
            )
        )
        customer_db_id = cur.lastrowid
        owner_id_int = int(owner_id)

        now = datetime.datetime.now()
        for i in range(12):
            d = datetime.date(now.year + ((now.month + i - 1) // 12), ((now.month + i - 1) % 12) + 1, 1)
            y = d.year
            m = d.month
            conn.execute(
                'INSERT OR IGNORE INTO payments (owner_id, customer_id, year, month, status, customer_choice, owner_confirmed) VALUES (?,?,?,?,?,?,0)',
                (owner_id_int, customer_db_id, y, m, 'unpaid', 'pending')
            )
        conn.commit()
        conn.close()
        return render_template('customer_register_success.html', customer_id=customer_id)
    except Exception as e:
        conn.close()
        owners = conn.execute('SELECT id, residency_name FROM owners ORDER BY id DESC').fetchall()
        return render_template('customer_register.html', owners=owners, error=f'Registration failed: {str(e)}')


@app.route('/customer/dashboard')
@customer_required
def customer_dashboard():
    customer_db_id = session['customer']['customerDbId']
    conn = get_db()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_db_id,)).fetchone()
    owner = conn.execute('SELECT * FROM owners WHERE id = ?', (customer['owner_id'],)).fetchone()
    conn.close()
    return render_template('customer_dashboard.html', customer=customer, owner=owner)


@app.route('/customer/save-profile', methods=['POST'])
@customer_required
def customer_save_profile():
    customer_db_id = session['customer']['customerDbId']
    name = request.form.get('name', '').strip()
    mobile_no = request.form.get('mobile_no', '').strip()
    conn = get_db()
    conn.execute(
        "UPDATE customers SET name = ?, mobile_no = ?, updated_at = datetime('now','localtime') WHERE id = ?",
        (name, mobile_no, customer_db_id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for('customer_dashboard'))


@app.route('/customer/exit-residence', methods=['POST'])
@customer_required
def customer_exit_residence():
    customer_db_id = session['customer']['customerDbId']
    conn = get_db()
    conn.execute(
        "UPDATE customers SET status = 'exited', updated_at = datetime('now','localtime') WHERE id = ?",
        (customer_db_id,)
    )
    conn.commit()
    conn.close()
    return redirect(url_for('customer_dashboard'))


@app.route('/customer/delete-account', methods=['POST'])
@customer_required
def customer_delete_account():
    customer_db_id = session['customer']['customerDbId']
    conn = get_db()
    conn.execute(
        "UPDATE customers SET status = 'deleted_by_customer', updated_at = datetime('now','localtime') WHERE id = ?",
        (customer_db_id,)
    )
    conn.commit()
    conn.close()

    # Clear the customer session so they are logged out
    session.pop('customer', None)
    return redirect(url_for('customer_login'))


@app.route('/customer/upload-photo', methods=['POST'])
@customer_required
def customer_upload_photo():
    customer_db_id = session['customer']['customerDbId']
    photo_file = request.files.get('customer_photo')
    if photo_file and photo_file.filename:
        rel = save_upload(photo_file, 'profiles')
        if rel:
            conn = get_db()
            conn.execute(
                "UPDATE customers SET customer_photo_path = ?, updated_at = datetime('now','localtime') WHERE id = ?",
                (rel, customer_db_id)
            )
            conn.commit()
            conn.close()
    return redirect(url_for('customer_dashboard'))


MONTH_NAMES = {1:'January',2:'February',3:'March',4:'April',5:'May',6:'June',7:'July',8:'August',9:'September',10:'October',11:'November',12:'December'}

def build_progressive_month_list(conn, customer, owner_id_int, customer_db_id):
    created_at = customer['created_at']
    try:
        dt = datetime.datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        try:
            dt = datetime.datetime.strptime(created_at, '%Y-%m-%d')
        except ValueError:
            dt = datetime.datetime.now()

    start_year = dt.year
    start_month = dt.month

    last_confirmed = conn.execute(
        'SELECT year, month FROM payments WHERE owner_id = ? AND customer_id = ? AND owner_confirmed = 1 ORDER BY year DESC, month DESC LIMIT 1',
        (owner_id_int, customer_db_id)
    ).fetchone()

    if last_confirmed:
        lc_year = last_confirmed['year']
        lc_month = last_confirmed['month']
        end_month_raw = lc_month + 1
        end_year = lc_year + (end_month_raw - 1) // 12
        end_month = ((end_month_raw - 1) % 12) + 1
    else:
        end_year = start_year
        end_month = start_month

    month_list = []
    cursor = datetime.date(start_year, start_month, 1)
    end_date = datetime.date(end_year, end_month, 1)
    max_iter = 0

    while cursor <= end_date and max_iter < 1200:
        y = cursor.year
        m = cursor.month
        month_list.append({'year': y, 'month': m, 'month_name': MONTH_NAMES[m]})

        existing = conn.execute(
            'SELECT id FROM payments WHERE owner_id = ? AND customer_id = ? AND year = ? AND month = ?',
            (owner_id_int, customer_db_id, y, m)
        ).fetchone()
        if not existing:
            conn.execute(
                'INSERT OR IGNORE INTO payments (owner_id, customer_id, year, month, status, customer_choice, owner_confirmed) VALUES (?,?,?,?,?,?,0)',
                (owner_id_int, customer_db_id, y, m, 'unpaid', 'pending')
            )

        if cursor.month < 12:
            cursor = datetime.date(cursor.year, cursor.month + 1, 1)
        else:
            cursor = datetime.date(cursor.year + 1, 1, 1)
        max_iter += 1

    conn.commit()
    return month_list


@app.route('/customer/payments')
@customer_required
def customer_payments():
    customer_db_id = session['customer']['customerDbId']
    conn = get_db()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_db_id,)).fetchone()
    owner = conn.execute('SELECT * FROM owners WHERE id = ?', (customer['owner_id'],)).fetchone()

    month_list = build_progressive_month_list(conn, customer, customer['owner_id'], customer['id'])

    rows = conn.execute(
        'SELECT * FROM payments WHERE owner_id = ? AND customer_id = ? ORDER BY year ASC, month ASC',
        (customer['owner_id'], customer['id'])
    ).fetchall()
    conn.close()

    pmap = {}
    for r in rows:
        pmap[f"{r['year']}-{r['month']}"] = r

    return render_template('customer_payments.html', customer=customer, owner=owner, monthList=month_list, pmap=pmap, rentMonthly=customer['room_rent_monthly'])


@app.route('/customer/payment-choice', methods=['POST'])
@customer_required
def customer_payment_choice():
    customer_db_id = session['customer']['customerDbId']
    conn = get_db()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_db_id,)).fetchone()

    year = int(request.form.get('year') or 0)
    month = int(request.form.get('month') or 0)
    choice = request.form.get('choice')

    conn.execute(
        "UPDATE payments SET customer_choice = ?, status = ?, updated_at = datetime('now','localtime') WHERE owner_id = ? AND customer_id = ? AND year = ? AND month = ?",
        (choice, 'paid' if choice == 'paid' else 'unpaid', customer['owner_id'], customer['id'], year, month)
    )
    conn.commit()

    if choice == 'paid':
        next_month = month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year += 1
        existing = conn.execute(
            'SELECT id FROM payments WHERE owner_id = ? AND customer_id = ? AND year = ? AND month = ?',
            (customer['owner_id'], customer['id'], next_year, next_month)
        ).fetchone()
        if not existing:
            conn.execute(
                'INSERT OR IGNORE INTO payments (owner_id, customer_id, year, month, status, customer_choice, owner_confirmed) VALUES (?,?,?,?,?,?,0)',
                (customer['owner_id'], customer['id'], next_year, next_month, 'unpaid', 'pending')
            )
            conn.commit()
    conn.close()
    return redirect(url_for('customer_payments'))


@app.route('/owner/dashboard')
@owner_required
def owner_dashboard():
    owner_db_id = session['owner']['ownerDbId']
    conn = get_db()
    owner = conn.execute('SELECT * FROM owners WHERE id = ?', (owner_db_id,)).fetchone()
    customers_count = conn.execute('SELECT COUNT(*) as c FROM customers WHERE owner_id = ?', (owner_db_id,)).fetchone()['c']
    total_row = conn.execute(
        'SELECT SUM(room_rent_monthly) as s FROM payments p JOIN customers c ON c.id = p.customer_id WHERE p.owner_id = ? AND p.status = ? AND p.owner_confirmed = 1',
        (owner_db_id, 'paid')
    ).fetchone()
    total_confirmed = total_row['s'] or 0
    conn.close()
    return render_template('owner_dashboard.html', owner=owner, customersCount=customers_count, totalConfirmed=total_confirmed)


@app.route('/owner/customers')
@owner_required
def owner_customers():
    owner_db_id = session['owner']['ownerDbId']
    conn = get_db()
    customers = conn.execute(
        'SELECT id, customer_id, name, mobile_no, room_rent_monthly, room_rent_type, status FROM customers WHERE owner_id = ? ORDER BY id DESC',
        (owner_db_id,)
    ).fetchall()
    owner_row = conn.execute('SELECT * FROM owners WHERE id = ?', (owner_db_id,)).fetchone()
    conn.close()
    return render_template('owner_customers.html', owner=session['owner'], customers=customers, owner_profile_photo_path=owner_row['profile_photo_path'], owner_user_id=owner_row['user_id'])


@app.route('/owner/customer/<int:customer_id>')
@owner_required
def owner_customer_details(customer_id):
    owner_db_id = session['owner']['ownerDbId']
    conn = get_db()
    customer = conn.execute('SELECT * FROM customers WHERE id = ? AND owner_id = ?', (customer_id, owner_db_id)).fetchone()
    if not customer:
        conn.close()
        abort(404)

    month_list = build_progressive_month_list(conn, customer, owner_db_id, customer['id'])

    broad = conn.execute(
        'SELECT * FROM payments WHERE owner_id = ? AND customer_id = ? ORDER BY year ASC, month ASC',
        (owner_db_id, customer_id)
    ).fetchall()

    owner_row = conn.execute('SELECT * FROM owners WHERE id = ?', (owner_db_id,)).fetchone()
    conn.close()

    pmap = {}
    for r in broad:
        pmap[f"{r['year']}-{r['month']}"] = r

    return render_template('owner_customer_details.html', owner=session['owner'], customer=customer, monthList=month_list, pmap=pmap, owner_profile_photo_path=owner_row['profile_photo_path'], owner_user_id=owner_row['user_id'])


@app.route('/owner/confirm-payment', methods=['POST'])
@owner_required
def owner_confirm_payment():
    owner_db_id = session['owner']['ownerDbId']
    customer_id = int(request.form.get('customer_id') or 0)
    year = int(request.form.get('year') or 0)
    month = int(request.form.get('month') or 0)
    confirm_status = request.form.get('confirm_status')

    conn = get_db()
    conn.execute(
        "UPDATE payments SET status = ?, owner_confirmed = 1, owner_updated_at = datetime('now','localtime'), updated_at = datetime('now','localtime') WHERE owner_id = ? AND customer_id = ? AND year = ? AND month = ?",
        (confirm_status, owner_db_id, customer_id, year, month)
    )
    conn.commit()

    if confirm_status == 'paid':
        next_month = month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year += 1
        existing = conn.execute(
            'SELECT id FROM payments WHERE owner_id = ? AND customer_id = ? AND year = ? AND month = ?',
            (owner_db_id, customer_id, next_year, next_month)
        ).fetchone()
        if not existing:
            conn.execute(
                'INSERT OR IGNORE INTO payments (owner_id, customer_id, year, month, status, customer_choice, owner_confirmed) VALUES (?,?,?,?,?,?,0)',
                (owner_db_id, customer_id, next_year, next_month, 'unpaid', 'pending')
            )
            conn.commit()
    conn.close()
    return redirect(url_for('owner_customer_details', customer_id=customer_id))


@app.route('/owner/customer/<int:customer_id>/delete', methods=['POST'])
@owner_required
def owner_customer_delete(customer_id):
    owner_db_id = session['owner']['ownerDbId']
    conn = get_db()

    # Verify the customer belongs to the logged-in owner
    customer = conn.execute(
        'SELECT * FROM customers WHERE id = ? AND owner_id = ?',
        (customer_id, owner_db_id)
    ).fetchone()
    if not customer:
        conn.close()
        abort(404)

    # Delete payment records for this customer, then the customer row
    conn.execute('DELETE FROM payments WHERE owner_id = ? AND customer_id = ?', (owner_db_id, customer_id))
    conn.execute('DELETE FROM customers WHERE id = ? AND owner_id = ?', (customer_id, owner_db_id))
    conn.commit()
    conn.close()

    return redirect(url_for('owner_customers'))


@app.route('/owner/details', methods=['GET', 'POST'])
@owner_required
def owner_details():
    owner_db_id = session['owner']['ownerDbId']
    conn = get_db()
    if request.method == 'GET':
        owner = conn.execute('SELECT * FROM owners WHERE id = ?', (owner_db_id,)).fetchone()
        conn.close()
        return render_template('owner_details.html', owner=owner, owner_profile_photo_path=owner['profile_photo_path'], owner_user_id=owner['user_id'])

    # POST - update details
    owner = conn.execute('SELECT * FROM owners WHERE id = ?', (owner_db_id,)).fetchone()
    upi_id = request.form.get('upi_id', '').strip()
    mobile_no = request.form.get('mobile_no', '').strip()
    qr_file = request.files.get('qr_code')
    profile_photo_file = request.files.get('profile_photo')

    qr_rel = None
    if qr_file and qr_file.filename:
        qr_rel = save_upload(qr_file, 'owner_qr')

    profile_photo_rel = None
    if profile_photo_file and profile_photo_file.filename:
        profile_photo_rel = save_upload(profile_photo_file, 'profiles')

    if qr_rel and profile_photo_rel:
        conn.execute(
            "UPDATE owners SET upi_id = ?, mobile_no = ?, qr_code_path = ?, profile_photo_path = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (upi_id, mobile_no, qr_rel, profile_photo_rel, owner_db_id)
        )
    elif qr_rel:
        conn.execute(
            "UPDATE owners SET upi_id = ?, mobile_no = ?, qr_code_path = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (upi_id, mobile_no, qr_rel, owner_db_id)
        )
    elif profile_photo_rel:
        conn.execute(
            "UPDATE owners SET upi_id = ?, mobile_no = ?, profile_photo_path = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (upi_id, mobile_no, profile_photo_rel, owner_db_id)
        )
    else:
        conn.execute(
            "UPDATE owners SET upi_id = ?, mobile_no = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (upi_id, mobile_no, owner_db_id)
        )
    conn.commit()
    conn.close()
    return redirect(url_for('owner_details'))


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

