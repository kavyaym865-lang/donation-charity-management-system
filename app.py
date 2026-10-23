# app.py — FULL UPDATED
import os
import uuid
import io
import re
import hashlib
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Rect, Line, Circle, String
from reportlab.lib.units import inch
from reportlab.platypus import Image
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import inch

def draw_certificate_border(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.gold)
    canvas.setLineWidth(4)

    # Outer border
    canvas.rect(30, 30, doc.width + 40, doc.height + 40)

    canvas.setLineWidth(2)

    # Inner border
    canvas.rect(40, 40, doc.width + 20, doc.height + 20)

    canvas.restoreState()


from flask import (
    Flask, g, render_template, request, redirect,
    url_for, session, flash, jsonify, send_file
)

from flask import Flask, render_template, request, redirect, session
from flask_mail import Mail, Message
import random

app = Flask(__name__)
app.secret_key = "your-secret-key"

# ----------- EMAIL CONFIG -----------
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "yourgmail@gmail.com"  # <-- your email
app.config["MAIL_PASSWORD"] = "your-app-password"    # <-- Gmail app password
app.config["MAIL_DEFAULT_SENDER"] = app.config["MAIL_USERNAME"]

from flask_mail import Mail
mail = Mail(app)
# ------------------------------------

import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import stripe
import qrcode

import uuid
import smtplib
from email.mime.text import MIMEText

import re

def is_valid_password(password):
    # Password must be EXACTLY 8 characters
    if len(password) != 8:
        return False

    # Must contain uppercase, lowercase, digit, and "@"
    if not re.search(r"[A-Z]", password):  
        return False
    if not re.search(r"[a-z]", password):  
        return False
    if not re.search(r"[0-9]", password):  
        return False
    if "@" not in password:               
        return False

    # Allowed characters ONLY: A-Z, a-z, 0-9, @
    if not re.fullmatch(r"[A-Za-z0-9@]+", password):
        return False

    return True


# ----------- CONFIG -----------
DATABASE = 'charity.db'
SECRET_KEY = "CHANGE_THIS_TO_A_STRONG_SECRET"   # change before production

# Replace with your Stripe test keys (put your test keys here)
STRIPE_SECRET_KEY = "sk_test_your_test_key_here"
STRIPE_PUBLISHABLE_KEY = "pk_test_your_test_key_here"

# UPI ID CONFIG (confirmed by you)
UPI_ID = "shridevielager1145@okaxis"
PAYEE_NAME_FOR_QR = "Donation & Charity Trust"

app = Flask(__name__)
# make logo urls available in all templates
@app.context_processor
def inject_logos():
    try:
        charity_logo = url_for('static', filename='logos/charity_logo.png')
        trusted_logo = url_for('static', filename='logos/trusted_logo.png')
    except RuntimeError:
        # when called outside request context (rare), just provide filenames
        charity_logo = '/static/logos/charity_logo.png'
        trusted_logo = '/static/logos/trusted_logo.png'
    return dict(CHARITY_LOGO=charity_logo, TRUSTED_LOGO=trusted_logo)

app.config['SECRET_KEY'] = SECRET_KEY
stripe.api_key = STRIPE_SECRET_KEY

# folder used historically; we won't necessarily write QR files
QR_FOLDER = "static/upi_qr"
os.makedirs(QR_FOLDER, exist_ok=True)

# ---------- Aadhaar helpers ----------
# Use an environment-provided pepper in production. Change default before production.
AADHAAR_PEPPER = os.environ.get("AADHAAR_PEPPER", "CHANGE_THIS_PEPPER")
def is_valid_aadhaar(a: str) -> bool:
    """Return True if aadhaar is exactly 12 digits."""
    if not a:
        return False
    return bool(re.fullmatch(r"\d{12}", a))

def hash_aadhaar(a: str) -> str:
    """Return SHA-256 hash of aadhaar + pepper."""
    return hashlib.sha256((a + AADHAAR_PEPPER).encode()).hexdigest()

# ----------- DB helpers ----------
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exc):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    cur = db.cursor()
    # users (added aadhaar_hash column)
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        aadhaar_hash TEXT
    )''')

    # charities
    cur.execute('''CREATE TABLE IF NOT EXISTS charities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        location TEXT,
        address TEXT,
        money_required REAL DEFAULT 0,
        purpose TEXT,
        image_url TEXT,
        contact TEXT,
        trust_logo TEXT
    )''')
    # donations (added aadhaar_hash column)
    cur.execute('''CREATE TABLE IF NOT EXISTS donations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        charity_id INTEGER,
        donor_name TEXT,
        donor_address TEXT,
        donor_mobile TEXT,
        donor_email TEXT,
        aadhaar_hash TEXT,
        amount REAL,
        timestamp TEXT,
        stripe_payment_intent TEXT,
        FOREIGN KEY(charity_id) REFERENCES charities(id)
    )''')
    db.commit()

    # sample charities (only if empty)
    cur.execute('SELECT COUNT(*) as cnt FROM charities')
    if cur.fetchone()['cnt'] == 0:
        sample = [
            ("Sunshine Orphanage", "Orphanage", "Mumbai, India", "123 Sunshine Road", 50000,
             "Food, education and shelter", "https://images.unsplash.com/photo-1582560471009-e0ea6ba0b9d2", "+91-9000000001", "/static/images/trust.png"),
            ("Hope Old Age Home", "Old Age Home", "Delhi, India", "45 Elder St", 30000,
             "Medical care and accommodations", "https://images.unsplash.com/photo-1503387762-592deb58ef4e", "+91-9000000002", "/static/images/trust.png"),
            ("City Hospital Trust", "Hospital", "Bengaluru, India", "88 Health Ave", 200000,
             "Surgery equipment and medicines", "https://images.unsplash.com/photo-1588776814546-1f47f1e94f7d", "+91-9000000003", "/static/images/trust.png"),
            ("Shree Temple Fund", "Temple", "Varanasi, India", "Temple Road", 10000,
             "Maintenance and community meals", "https://images.unsplash.com/photo-1512453979798-5ea266f8880c", "+91-9000000004", "/static/images/trust.png"),
            ("Bright Future School", "School", "Chennai, India", "12 School Lane", 75000,
             "Scholarships and books", "https://images.unsplash.com/photo-1503676260728-1c00da094a0b", "+91-9000000005", "/static/images/trust.png"),
        ]
        cur.executemany('INSERT INTO charities (name,category,location,address,money_required,purpose,image_url,contact,trust_logo) VALUES (?,?,?,?,?,?,?,?,?)', sample)
        db.commit()

# Initialize DB on startup (works with Flask 3+)
with app.app_context():
    init_db()


# ----------- Helper: build NPCI-compatible UPI url ----------
def build_upi_url(amount, upi_id=UPI_ID, payee=PAYEE_NAME_FOR_QR):
    """
    Build an NPCI-compatible UPI URL including transaction ids and optional fields.
    This format is widely accepted by GPay/PhonePe/Paytm/BHIM.
    """
    # ensure amount formatting: two decimals if float-like, else integer
    try:
        # allow strings like "100" or numbers
        amt_val = float(amount)
        # represent with up to two decimal places (no trailing zeros if integer)
        if amt_val.is_integer():
            am_str = str(int(amt_val))
        else:
            am_str = f"{amt_val:.2f}"
    except Exception:
        am_str = "1"

    # unique ids for transaction
    tid = uuid.uuid4().hex[:20]
    tr = uuid.uuid4().hex[:20]
    # URL-encode payee name (spaces -> %20); we will rely on simple replacement to avoid importing urllib for clarity
    pn = str(payee).replace(" ", "%20")

    # build canonical UPI string — this includes optional fields that improve compatibility
    upi_url = (
        f"upi://pay?"
        f"pa={upi_id}&"
        f"pn={pn}&"
        f"mc=0000&"
        f"tid={tid}&"
        f"tr={tr}&"
        f"tn=Donation&"
        f"am={am_str}&"
        f"cu=INR&"
        f"mode=02&"
        f"purpose=00"
    )
    return upi_url


# ------- LIVE QR GENERATION ENDPOINT -------
@app.route("/generate_qr")
def generate_qr():
    amount = request.args.get("amount", "1")
    # accept decimal amounts like 250.50 but sanitize
    if amount is None or amount.strip() == "":
        amount = "1"
    # build UPI URL
    upi_url = build_upi_url(amount)
    # generate QR into memory
    img = qrcode.make(upi_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

# ----------- Routes ----------
@app.route("/")
def welcome():
    return render_template("welcome.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        aadhaar = request.form.get("aadhaar", "")

        # Validate password
        if not is_valid_password(password):
           flash("Password must be exactly 8 characters and contain uppercase, lowercase, number, and '@' only.")
           return redirect(url_for("register"))

        # Require Aadhaar on registration (per your request to add it)
        if not (name and email and password and aadhaar):
            flash("Please fill all fields including Aadhaar.")
            return redirect(url_for("register"))

        if not is_valid_aadhaar(aadhaar):
            flash("Invalid Aadhaar number. It must be exactly 12 digits.")
            return redirect(url_for("register"))

        aadhaar_hash = hash_aadhaar(aadhaar)

        db = get_db()
        cur = db.cursor()
        try:
            cur.execute(
                "INSERT INTO users (name,email,password,aadhaar_hash) VALUES (?,?,?,?)",
                (name, email, generate_password_hash(password), aadhaar_hash)
            )
            db.commit()
            flash("Registered! Please login.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already registered.")
            return redirect(url_for("register"))
    return render_template("register.html")



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cur.fetchone()
        if user and check_password_hash(user["password"], password):
            session["user"] = {"id": user["id"], "name": user["name"], "email": user["email"]}
            flash("Logged in successfully.")
            return redirect(url_for("home"))
        else:
            flash("Invalid credentials.")
            return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out.")
    return redirect(url_for("welcome"))

@app.route("/home")
def home():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    db = get_db()
    cur = db.cursor()
    params = []
    sql = "SELECT * FROM charities"
    clauses = []
    if q:
        clauses.append("(name LIKE ? OR category LIKE ? OR location LIKE ? OR purpose LIKE ?)")
        qparam = f"%{q}%"
        params.extend([qparam, qparam, qparam, qparam])
    if category:
        clauses.append("category = ?")
        params.append(category)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY name COLLATE NOCASE"
    cur.execute(sql, params)
    charities = cur.fetchall()
    cur.execute("SELECT DISTINCT category FROM charities")
    cats = [r["category"] for r in cur.fetchall()]
    return render_template("home.html", charities=charities, cats=cats, q=q, category=category)


@app.route("/charity/<int:cid>")
def charity_detail(cid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM charities WHERE id=?", (cid,))
    c = cur.fetchone()
    if not c:
        flash("Charity not found.")
        return redirect(url_for("home"))
    return render_template("charity.html", c=c)


@app.route("/donate/<int:cid>")
def donate(cid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM charities WHERE id=?", (cid,))
    c = cur.fetchone()
    if not c:
        flash("Charity not found.")
        return redirect(url_for("home"))
    # pass STRIPE_PUBLISHABLE_KEY into template so JS can use it
    return render_template("donate.html", c=c, STRIPE_PUBLISHABLE_KEY=STRIPE_PUBLISHABLE_KEY)

@app.route("/certificate/<int:cid>")
def certificate(cid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM charities WHERE id=?", (cid,))
    charity = cur.fetchone()

    if not charity:
        flash("Charity not found.")
        return redirect(url_for("home"))

    # PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        rightMargin=40,
        leftMargin=40,
        topMargin=60,
        bottomMargin=60
    )

    story = []

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontSize=22,
        alignment=1,
        textColor=colors.HexColor("#8B7500"),
        spaceAfter=12
    )
    org_style = ParagraphStyle(
        "OrgName",
        parent=styles["Normal"],
        fontSize=18,
        alignment=1,
        spaceAfter=8
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=12,
        alignment=1,
        leading=16,
        spaceAfter=8
    )

    # ---------------------------------------------------
    # 1️⃣  ADD LOGO (TOP-CENTER) - safe scaled
    # ---------------------------------------------------
    logo_path = os.path.join("static", "logos", "charity_logo.png")
    if os.path.exists(logo_path):
        try:
            # limit to max width 140 and height 90 to avoid large images causing layout problems
            img = Image(logo_path, width=140, height=90)
            img.hAlign = 'CENTER'
            story.append(img)
            story.append(Spacer(1, 12))
        except Exception as e:
            print("Logo load failed:", e)

    # ---------------------------------------------------
    # Title
    # ---------------------------------------------------
    story.append(Paragraph("Government Authorization Certificate", title_style))
    story.append(Spacer(1, 6))

    # ---------------------------------------------------
    # Organisation Name
    # ---------------------------------------------------
    story.append(Paragraph(f"<b>{charity['name']}</b>", org_style))
    story.append(Spacer(1, 8))

    # ---------------------------------------------------
    # Certificate Text - split into multiple Paragraphs (no nested <para>)
    # ---------------------------------------------------
    story.append(Paragraph(
        "This document certifies that the organization named below is a legally registered public "
        "charitable trust and is authorized to carry out welfare, education, relief and community development activities.",
        body_style
    ))

    story.append(Spacer(1, 6))

    reg_num = f"GCT/{(charity['location'] or 'UNK')[:3].upper()}/2025/{int(cid):05d}"
    date_of_issue = datetime.now().strftime('%d %B %Y')

    story.append(Paragraph(
        f"<b>Registration Number:</b> {reg_num}<br/>"
        f"<b>Issuing Authority:</b> Ministry of Social Justice & Health, Government of India<br/>"
        f"<b>Date of Issue:</b> {date_of_issue}<br/>"
        f"<b>Validity:</b> 2025 - 2030",
        body_style
    ))

    story.append(Spacer(1, 12))

    story.append(Paragraph("The organization is authorized to:", body_style))
    bullet_items = [
        "Receive public donations",
        "Conduct charitable activities",
        "Operate programs for public welfare"
    ]
    for item in bullet_items:
        # simple bullet lines (each is short so safe)
        story.append(Paragraph(f"• {item}", body_style))

    story.append(Spacer(1, 18))

    # ---------------------------------------------------
    # Seal (drawn but kept size small so it fits)
    # ---------------------------------------------------
    seal = Drawing(80, 80)   # smaller than before
    seal.add(Circle(40, 40, 36, strokeColor=colors.red, strokeWidth=2, fillColor=None))
    seal.add(Circle(40, 40, 28, strokeColor=colors.red, strokeWidth=1, fillColor=None))
    seal.add(String(12, 38, "GOVT. OF INDIA", fontSize=7, fillColor=colors.red))
    seal.add(String(28, 24, "SEAL", fontSize=9, fillColor=colors.red))
    # center the seal as a flowable by wrapping in a Table cell
    seal_table = Table([[seal]], colWidths=[doc.width])
    seal_table.setStyle(TableStyle([("ALIGN", (0,0), (-1,-1), "CENTER")]))
    story.append(seal_table)
    story.append(Spacer(1, 18))

    # ---------------------------------------------------
    # Signature Block (two columns)
    # ---------------------------------------------------
    signature_box = Table(
        [
            ["", ""],
            ["Authorized Officer", "Seal & Verification"]
        ],
        colWidths=[doc.width/2 - 10, doc.width/2 - 10]
    )
    signature_box.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (0, 0), 1, colors.black),
        ("LINEABOVE", (1, 0), (1, 0), 1, colors.black),
        ("ALIGN", (0, 1), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(signature_box)
    story.append(Spacer(1, 10))

    # BUILD PDF using your canvas border function (do not add border as a flowable)
    doc.build(
        story,
        onFirstPage=draw_certificate_border,
        onLaterPages=draw_certificate_border
    )

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{charity['name']}_certificate.pdf",
        mimetype="application/pdf"
    )


# ------- STRIPE CHECKOUT -------
@app.route("/create-checkout-session/<int:cid>", methods=["POST"])
def create_checkout_session(cid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM charities WHERE id=?", (cid,))
    charity = cur.fetchone()
    if not charity:
        return jsonify({"error": "Charity not found."}), 404
    # read donor fields
    donor_name = request.form.get("donor_name", "").strip()
    donor_address = request.form.get("donor_address", "").strip()
    donor_mobile = request.form.get("donor_mobile", "").strip()
    donor_email = request.form.get("donor_email", "").strip().lower()
    try:
        amount = float(request.form.get("amount", "0"))
    except:
        return jsonify({"error": "Invalid amount"}), 400
    if amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400

    # save pending donation data to session so we can persist after Stripe redirect
    session["pending_donation"] = {
        "charity_id": cid,
        "donor_name": donor_name,
        "donor_address": donor_address,
        "donor_mobile": donor_mobile,
        "donor_email": donor_email,
        "amount": amount
    }

    # Create Stripe Checkout Session (INR: amount in paisa)
    try:
        checkout = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "inr",
                    "product_data": {"name": f"Donation to {charity['name']}"},
                    "unit_amount": int(round(amount * 100)),
                },
                "quantity": 1
            }],
            success_url=request.url_root + "stripe-success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.url_root + f"donate/{cid}"
        )
        return jsonify({"sessionId": checkout.id, "publishableKey": STRIPE_PUBLISHABLE_KEY})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Stripe redirect handler (after checkout)
@app.route("/stripe-success")
def stripe_success():
    session_id = request.args.get("session_id")
    if not session_id:
        flash("Missing Stripe session id.")
        return redirect(url_for("home"))
    try:
        s = stripe.checkout.Session.retrieve(session_id)
        payment_intent = s.payment_intent
    except Exception as e:
        flash("Error verifying payment: " + str(e))
        return redirect(url_for("home"))

    pending = session.pop("pending_donation", None)
    if not pending:
        flash("Donation data missing (session expired).")
        return redirect(url_for("home"))

    db = get_db()
    cur = db.cursor()
    ts = datetime.utcnow().isoformat()
    cur.execute("""
        INSERT INTO donations (charity_id, donor_name, donor_address, donor_mobile, donor_email, amount, timestamp, stripe_payment_intent)
        VALUES (?,?,?,?,?,?,?,?)
    """, (pending["charity_id"], pending["donor_name"], pending["donor_address"], pending["donor_mobile"], pending["donor_email"], pending["amount"], ts, payment_intent))
    db.commit()
    donation_id = cur.lastrowid

    return redirect(url_for("payment_success", donation_id=donation_id))


@app.route("/payment_success/<int:donation_id>")
def payment_success(donation_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT d.*, c.name as charity_name 
        FROM donations d 
        JOIN charities c ON d.charity_id = c.id
        WHERE d.id = ?
    """, (donation_id,))
    d = cur.fetchone()

    if not d:
        flash("Donation not found.")
        return redirect(url_for("home"))

    return render_template("payment_success.html", d=d)

@app.route("/upi-success/<int:cid>", methods=["GET", "POST"])
def upi_success(cid):
    # Get txn from query param
    txn = request.args.get("txn")
    if not txn:
        flash("Transaction ID missing.")
        return redirect(url_for("donate", cid=cid))

    # For GET requests, optionally show a simple confirmation form
    if request.method == "GET":
        return render_template("upi_confirm.html", cid=cid, txn=txn)

    # POST: process donation
    donor_name = request.form.get("donor_name", "").strip() or "Anonymous"
    donor_address = request.form.get("donor_address", "").strip() or ""
    donor_mobile = request.form.get("donor_mobile", "").strip() or ""
    donor_email = request.form.get("donor_email", "").strip().lower() or ""
    try:
        amount = float(request.form.get("amount", "0"))
    except:
        flash("Invalid amount.")
        return redirect(url_for("donate", cid=cid))
    if amount <= 0:
        flash("Invalid amount.")
        return redirect(url_for("donate", cid=cid))

    db = get_db()
    cur = db.cursor()
    ts = datetime.utcnow().isoformat()
    cur.execute("""
        INSERT INTO donations (charity_id, donor_name, donor_address, donor_mobile, donor_email, amount, timestamp, stripe_payment_intent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (cid, donor_name, donor_address, donor_mobile, donor_email, amount, ts, f"UPI-{txn}"))
    db.commit()
    donation_id = cur.lastrowid

    # create PDF
    try:
        cur.execute("SELECT d.*, c.name as charity_name FROM donations d JOIN charities c ON d.charity_id=c.id WHERE d.id=?", (donation_id,))
        donation_row = cur.fetchone()
        pdf_path = os.path.join(RECEIPT_FOLDER, f"{donation_id}.pdf")
        create_pdf_receipt(dict(donation_row), pdf_path)
    except Exception as e:
        print("PDF creation failed:", e)

    return redirect(url_for("payment_success", donation_id=donation_id))

@app.route("/receipt/<int:donation_id>")
def receipt(donation_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT d.*, c.name as charity_name, c.address as charity_address
        FROM donations d 
        JOIN charities c ON d.charity_id = c.id
        WHERE d.id = ?
    """, (donation_id,))
    d = cur.fetchone()

    if not d:
        flash("Receipt not found.")
        return redirect(url_for("home"))

    return render_template("receipt.html", d=d)

# ----------------- ADMIN LOGIN PAGE -----------------
@app.route("/admin")
def admin_redirect():
    return redirect(url_for("admin_login"))


# ----------------- ADMIN LOGIN -----------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "admin123"

    if request.method == "POST":
        u = request.form.get("admin_username")
        p = request.form.get("admin_password")

        if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin/dashboard")
        else:
            return render_template("admin_login.html", error="Invalid login")

    return render_template("admin_login.html")

# ----------------- ADMIN DASHBOARD -----------------
@app.route("/admin/dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect("/admin/login")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    users = cur.execute("SELECT id, name, email, aadhaar FROM users").fetchall()
    charities = cur.execute("SELECT id, name, category, location FROM charities").fetchall()
    donations = cur.execute(
        "SELECT id, charity_id, donor_name, donor_email, amount, timestamp, transaction_id FROM donations"
    ).fetchall()

    conn.close()

    return render_template("admin_dashboard.html",
                           users=users,
                           charities=charities,
                           donations=donations)


# ----------------- ADMIN LOGOUT -----------------
@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect("/admin/login")


if __name__ == "__main__":
    app.run(debug=True)

if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)

if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)
