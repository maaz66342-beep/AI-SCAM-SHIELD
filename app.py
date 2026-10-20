from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import pickle
import sqlite3
import os
import re
import json
import hashlib
from functools import wraps
from datetime import datetime
from werkzeug.utils import secure_filename

from phishing_checker import check_link
from screenshot_checker import analyze_screenshot, extract_text_from_image
from explainable_ai import explain_prediction
from offer_letter_checker import check_offer_letter

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ai-scam-shield-secret-key-change-this-for-production")

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "history.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

with open(os.path.join(BASE_DIR, "model", "job_model.pkl"), "rb") as f:
    job_model = pickle.load(f)

SUSPICIOUS_JOB_KEYWORDS = [
    "registration fee", "processing fee", "security deposit", "refundable deposit",
    "pay rs", "pay a fee", "urgent hiring", "no experience needed", "guaranteed income",
    "guaranteed job", "whatsapp only", "limited seats", "joining kit", "aadhar card",
    "bank details", "no interview required", "100% job guarantee", "earn upto",
]


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            module TEXT,
            summary TEXT,
            result TEXT,
            confidence TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            message TEXT NOT NULL,
            rating INTEGER,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Please log in first."}), 401
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Please log in first."}), 401
            return redirect(url_for("admin_login"))
        if not session.get("is_admin"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Admin access only."}), 403
            flash("That account does not have admin access.")
            return redirect(url_for("admin_login"))
        return view_func(*args, **kwargs)
    return wrapper


def log_history(module, summary, result, confidence):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO history (user_id, module, summary, result, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (session.get("user_id"), module, summary[:120], result, str(confidence), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def find_flagged_phrases(text, keyword_list):
    text_lower = text.lower()
    return [kw for kw in keyword_list if kw in text_lower]


@app.route("/")
@login_required
def home():
    return render_template("index.html", username=session.get("username"), is_admin=session.get("is_admin", False))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not username or not password:
            flash("Please fill in all fields.")
            return redirect(url_for("register"))
        if password != confirm:
            flash("Passwords do not match.")
            return redirect(url_for("register"))
        if len(password) < 4:
            flash("Password should be at least 4 characters.")
            return redirect(url_for("register"))

        conn = sqlite3.connect(DB_PATH)
        is_first_user = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()[0] == 0
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?)",
                (username, hash_password(password), 1 if is_first_user else 0, datetime.now().isoformat())
            )
            conn.commit()
        except sqlite3.IntegrityError:
            flash("That username is already taken.")
            conn.close()
            return redirect(url_for("register"))
        conn.close()

        if is_first_user:
            flash("Account created! You are the first user, so you're the Admin. Please log in.")
        else:
            flash("Account created! Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and user["password_hash"] == hash_password(password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["is_admin"] = bool(user["is_admin"])
            return redirect(url_for("home"))

        flash("Invalid username or password.")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if not user or user["password_hash"] != hash_password(password):
            flash("Invalid admin username or password.")
            return redirect(url_for("admin_login"))

        if not user["is_admin"]:
            flash("This account does not have admin access.")
            return redirect(url_for("admin_login"))

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["is_admin"] = True
        return redirect(url_for("admin_panel"))

    return render_template("admin_login.html")


# ---------- Module 1: Fake Job Detector ----------
@app.route("/api/predict-job", methods=["POST"])
@login_required
def predict_job():
    data = request.get_json()
    title = data.get("title", "")
    company = data.get("company", "")
    description = data.get("description", "")
    salary = data.get("salary", "")
    requirements = data.get("requirements", "")

    combined_text = f"{title} {company} {description} {salary} {requirements}"
    proba = job_model.predict_proba([combined_text])[0]
    fraud_prob = proba[1]
    prediction = int(fraud_prob >= 0.5)
    flagged = find_flagged_phrases(combined_text, SUSPICIOUS_JOB_KEYWORDS)

    result_label = "Fraudulent" if prediction == 1 else "Genuine"
    confidence = round(fraud_prob * 100, 2) if prediction == 1 else round((1 - fraud_prob) * 100, 2)
    explanation = explain_prediction(job_model, combined_text)

    log_history("Job Detector", title or "Untitled job", result_label, f"{confidence}%")

    return jsonify({
        "result": result_label, "confidence": confidence, "flagged_phrases": flagged,
        "fraud_words": explanation["fraud_words"], "genuine_words": explanation["genuine_words"],
    })


# ---------- Module 2: Phishing Link Checker ----------
@app.route("/api/check-link", methods=["POST"])
@login_required
def api_check_link():
    data = request.get_json()
    url = data.get("url", "")
    if not url.strip():
        return jsonify({"error": "Please enter a URL."}), 400

    result = check_link(url)
    log_history("Phishing Checker", url, result["result"], f"{result['score']}/100")
    return jsonify(result)


# ---------- Module 3: Fake Offer Letter Checker ----------
@app.route("/api/check-offer-letter", methods=["POST"])
@login_required
def api_check_offer_letter():
    sender_email = request.form.get("sender_email", "")
    letter_text = request.form.get("letter_text", "").strip()

    ocr_text = ""
    uploaded_file = request.files.get("letter_file")
    if uploaded_file and uploaded_file.filename:
        filename = secure_filename(uploaded_file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        uploaded_file.save(filepath)
        try:
            ocr_text = extract_text_from_image(filepath)
        except RuntimeError as e:
            return jsonify({"error": str(e)}), 400
        finally:
            try:
                os.remove(filepath)
            except OSError:
                pass

    combined_text = (letter_text + "\n" + ocr_text).strip()

    if not combined_text:
        return jsonify({"error": "Please paste the offer letter text or upload an image of it."}), 400

    result = check_offer_letter(combined_text, sender_email)
    result["extracted_text"] = ocr_text.strip()

    log_history("Offer Letter Checker", combined_text, result["result"], f"{result['score']}/100")

    return jsonify(result)


# ---------- Module 4: Fake UPI/Payment Screenshot Detector ----------
@app.route("/api/check-screenshot", methods=["POST"])
@login_required
def api_check_screenshot():
    if "screenshot" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files["screenshot"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    result = analyze_screenshot(filepath)
    log_history("Screenshot Checker", filename, result["result"], f"{result['score']}/100")

    try:
        os.remove(filepath)
    except OSError:
        pass

    return jsonify(result)


# ---------- Feedback / Review chatbox ----------
@app.route("/api/feedback", methods=["GET", "POST"])
@login_required
def api_feedback():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        message = (data.get("message") or "").strip()
        rating = data.get("rating")

        if not message:
            conn.close()
            return jsonify({"error": "Feedback message cannot be empty."}), 400
        if len(message) > 1000:
            message = message[:1000]

        try:
            rating = int(rating) if rating is not None else None
            if rating is not None and not (1 <= rating <= 5):
                rating = None
        except (TypeError, ValueError):
            rating = None

        conn.execute(
            "INSERT INTO feedback (user_id, username, message, rating, created_at) VALUES (?, ?, ?, ?, ?)",
            (session["user_id"], session.get("username"), message, rating, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})

    # GET: return this user's own feedback thread
    rows = conn.execute(
        "SELECT * FROM feedback WHERE user_id = ? ORDER BY id ASC", (session["user_id"],)
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


# ---------- Per-user history for dashboard ----------
@app.route("/api/history")
@login_required
def history():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM history WHERE user_id = ? ORDER BY id DESC LIMIT 30",
        (session["user_id"],)
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.route("/api/stats")
@login_required
def stats():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    uid = session["user_id"]

    total = conn.execute("SELECT COUNT(*) AS c FROM history WHERE user_id = ?", (uid,)).fetchone()["c"]
    by_module = conn.execute(
        "SELECT module, COUNT(*) AS c FROM history WHERE user_id = ? GROUP BY module", (uid,)
    ).fetchall()

    flagged_words = ("fraud", "malicious", "scam", "fake", "suspicious")
    all_rows = conn.execute("SELECT result FROM history WHERE user_id = ?", (uid,)).fetchall()
    flagged_count = sum(1 for r in all_rows if any(w in r["result"].lower() for w in flagged_words))
    safe_count = total - flagged_count

    conn.close()

    return jsonify({
        "total_checks": total,
        "flagged_count": flagged_count,
        "safe_count": safe_count,
        "by_module": [{"module": row["module"], "count": row["c"]} for row in by_module],
    })


# ---------- Model Comparison ----------
@app.route("/api/model-comparison")
@login_required
def model_comparison():
    try:
        with open(os.path.join(BASE_DIR, "model_comparison.json")) as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": "Run compare_models.py first to generate this data."}), 404


# ---------- Admin Panel ----------
@app.route("/admin")
@admin_required
def admin_panel():
    return render_template("admin.html", username=session.get("username"))


@app.route("/api/admin/users")
@admin_required
def admin_users():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT u.id, u.username, u.is_admin, u.created_at,
               COUNT(h.id) AS check_count
        FROM users u
        LEFT JOIN history h ON h.user_id = u.id
        GROUP BY u.id
        ORDER BY u.id ASC
    """).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.route("/api/admin/stats")
@admin_required
def admin_stats():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    total_users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    total_checks = conn.execute("SELECT COUNT(*) AS c FROM history").fetchone()["c"]

    by_module = conn.execute(
        "SELECT module, COUNT(*) AS c FROM history GROUP BY module"
    ).fetchall()

    flagged_words = ("fraud", "malicious", "scam", "fake", "suspicious")
    all_rows = conn.execute("SELECT result FROM history").fetchall()
    flagged_count = sum(1 for r in all_rows if any(w in r["result"].lower() for w in flagged_words))
    safe_count = total_checks - flagged_count

    conn.close()

    return jsonify({
        "total_users": total_users,
        "total_checks": total_checks,
        "flagged_count": flagged_count,
        "safe_count": safe_count,
        "by_module": [{"module": row["module"], "count": row["c"]} for row in by_module],
    })


@app.route("/api/admin/history")
@admin_required
def admin_history():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT h.*, u.username
        FROM history h
        LEFT JOIN users u ON u.id = h.user_id
        ORDER BY h.id DESC
        LIMIT 100
    """).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.route("/api/admin/feedback")
@admin_required
def admin_feedback():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT f.*, u.username AS current_username
        FROM feedback f
        LEFT JOIN users u ON u.id = f.user_id
        ORDER BY f.id DESC
        LIMIT 200
    """).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
