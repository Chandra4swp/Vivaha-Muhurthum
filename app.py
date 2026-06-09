import os
import sqlite3
import uuid
import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "matrimonial_secret_key"

# Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
DB_PATH = os.path.join(BASE_DIR, "matrimonial.db")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ── Database ──────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                email       TEXT UNIQUE NOT NULL,
                phone       TEXT,
                dob         TEXT,
                gender      TEXT,
                religion    TEXT,
                caste       TEXT,
                education   TEXT,
                occupation  TEXT,
                income      TEXT,
                height      TEXT,
                city        TEXT,
                state       TEXT,
                country     TEXT DEFAULT 'India',
                bio         TEXT,
                photo       TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_email"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


def api_login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_email"):
            return jsonify({"error": "authentication_required"}), 401
        return view(*args, **kwargs)
    return wrapped_view


def get_user_by_email(email):
    with get_db() as conn:
        return conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def create_user(email, password):
    password_hash = generate_password_hash(password)
    with get_db() as conn:
        conn.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, password_hash))
        conn.commit()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
@login_required
def register():
    if request.method == "POST":
        data = request.form
        photo_filename = None

        if "photo" in request.files:
            file = request.files["photo"]
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit(".", 1)[1].lower()
                photo_filename = f"{uuid.uuid4().hex}.{ext}"
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], photo_filename))

        profile_id = "MAT" + uuid.uuid4().hex[:8].upper()

        try:
            with get_db() as conn:
                conn.execute("""
                    INSERT INTO profiles
                        (id, name, email, phone, dob, gender, religion, caste,
                         education, occupation, income, height, city, state, country, bio, photo)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    profile_id,
                    data.get("name"), data.get("email"), data.get("phone"),
                    data.get("dob"), data.get("gender"), data.get("religion"),
                    data.get("caste"), data.get("education"), data.get("occupation"),
                    data.get("income"), data.get("height"), data.get("city"),
                    data.get("state"), data.get("country", "India"),
                    data.get("bio"), photo_filename
                ))
                conn.commit()
            return jsonify({"success": True, "id": profile_id, "message": f"Profile created! Your ID: {profile_id}"})
        except sqlite3.IntegrityError:
            return jsonify({"success": False, "message": "Email already registered."}), 400
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

    return render_template("register.html")


@app.route("/search")
@login_required
def search():
    return render_template("search.html")


@app.route("/api/search")
@api_login_required
def api_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])

    like = f"%{query}%"
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM profiles
            WHERE id LIKE ? OR name LIKE ? OR email LIKE ?
            ORDER BY created_at DESC LIMIT 20
        """, (like, like, like)).fetchall()

    results = []
    for r in rows:
        d = dict(r)
        if d["photo"]:
            d["photo_url"] = url_for("static", filename=f"uploads/{d['photo']}")
        else:
            d["photo_url"] = None
        results.append(d)

    return jsonify(results)


@app.route("/profile/<profile_id>")
@login_required
def profile(profile_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    if not row:
        return render_template("404.html"), 404
    data = dict(row)
    if data["photo"]:
        data["photo_url"] = url_for("static", filename=f"uploads/{data['photo']}")
    else:
        data["photo_url"] = None

    if data.get("dob"):
        try:
            dob = datetime.date.fromisoformat(data["dob"])
            today = datetime.date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            data["age"] = f"{age} yrs"
        except ValueError:
            data["age"] = None
    else:
        data["age"] = None

    return render_template("profile.html", profile=data)


@app.route("/api/profiles")
@api_login_required
def api_all_profiles():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM profiles ORDER BY created_at DESC").fetchall()
    results = []
    for r in rows:
        d = dict(r)
        if d["photo"]:
            d["photo_url"] = url_for("static", filename=f"uploads/{d['photo']}")
        else:
            d["photo_url"] = None
        results.append(d)
    return jsonify(results)


@app.route("/browse")
@login_required
def browse():
    return render_template("browse.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_email"):
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_user_by_email(email)
        if not user or not check_password_hash(user["password_hash"], password):
            error = "Invalid email or password."
        else:
            session["user_email"] = email
            return redirect(url_for("index"))

    return render_template("login.html", error=error)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("user_email"):
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if not email or not password or not confirm:
            error = "Please fill all fields."
        elif password != confirm:
            error = "Passwords do not match."
        elif get_user_by_email(email):
            error = "This email is already registered."
        else:
            try:
                create_user(email, password)
                session["user_email"] = email
                return redirect(url_for("index"))
            except sqlite3.IntegrityError:
                error = "This email is already registered."

    return render_template("register_user.html", error=error)


@app.route("/logout")
def logout():
    session.pop("user_email", None)
    return redirect(url_for("login"))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    init_db()
    print("\n" + "="*50)
    print("  💍 Matrimonial App running!")
    print("  Open: http://127.0.0.1:5000")
    print("="*50 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
