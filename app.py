import os
import uuid
import datetime
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, session
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

# Import database layer
from db import (
    get_db_connection, close_db_connection, init_db, get_user_by_email,
    create_user, create_profile, get_profile_by_id, search_profiles,
    get_all_profiles, row_to_dict, USE_POSTGRES, SQLITE_DB_PATH
)

app = Flask(__name__)
app.secret_key = "matrimonial_secret_key"

# Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB

# Try to create upload folder (will fail on read-only filesystems like Vercel)
try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except (OSError, PermissionError):
    pass  # Read-only filesystem (e.g., Vercel serverless)



# ── Decorators & Utilities ────────────────────────────────────────────────────

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


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
@login_required
def register():
    if request.method == "POST":
        try:
            data = request.form
            photo_filename = None

            if "photo" in request.files:
                file = request.files["photo"]
                if file and file.filename and allowed_file(file.filename):
                    try:
                        ext = file.filename.rsplit(".", 1)[1].lower()
                        photo_filename = f"{uuid.uuid4().hex}.{ext}"
                        file.save(os.path.join(app.config["UPLOAD_FOLDER"], photo_filename))
                    except (OSError, PermissionError) as e:
                        print(f"Warning: Could not save photo: {e}")
                        photo_filename = None  # Continue without photo

            profile_id = "MAT" + uuid.uuid4().hex[:8].upper()

            create_profile(profile_id, data, photo_filename)
            return jsonify({"success": True, "id": profile_id, "message": f"Profile created! Your ID: {profile_id}"})
        except sqlite3.IntegrityError as e:
            print(f"Profile integrity error: {e}")
            return jsonify({"success": False, "message": "Email already registered."}), 400
        except Exception as e:
            print(f"Profile creation error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

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

    try:
        rows = search_profiles(query, limit=20)
        results = []
        for r in rows:
            d = row_to_dict(r)
            if d.get("photo"):
                d["photo_url"] = url_for("static", filename=f"uploads/{d['photo']}")
            else:
                d["photo_url"] = None
            results.append(d)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/profile/<profile_id>")
@login_required
def profile(profile_id):
    try:
        row = get_profile_by_id(profile_id)
        if not row:
            return render_template("404.html"), 404
        
        data = row_to_dict(row)
        if data.get("photo"):
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
    except Exception as e:
        return render_template("404.html"), 404


@app.route("/api/profiles")
@api_login_required
def api_all_profiles():
    try:
        rows = get_all_profiles()
        results = []
        for r in rows:
            d = row_to_dict(r)
            if d.get("photo"):
                d["photo_url"] = url_for("static", filename=f"uploads/{d['photo']}")
            else:
                d["photo_url"] = None
            results.append(d)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
        try:
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = get_user_by_email(email)
            if user:
                # Convert row to dict if needed
                user_dict = row_to_dict(user) if not isinstance(user, dict) else user
                if check_password_hash(user_dict.get("password_hash", ""), password):
                    session["user_email"] = email
                    return redirect(url_for("index"))
            error = "Invalid email or password."
        except Exception as e:
            error = f"Login error: {str(e)}"
            print(f"Login error: {e}")

    return render_template("login.html", error=error)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("user_email"):
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        try:
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            confirm = request.form.get("confirm", "")
            if not email or not password or not confirm:
                error = "Please fill all fields."
            elif password != confirm:
                error = "Passwords do not match."
            else:
                # Check if user already exists
                existing_user = get_user_by_email(email)
                if existing_user:
                    error = "This email is already registered."
                else:
                    try:
                        create_user(email, password)
                        session["user_email"] = email
                        return redirect(url_for("index"))
                    except sqlite3.IntegrityError:
                        error = "This email is already registered."
        except Exception as e:
            error = f"Error: {str(e)}"
            print(f"Signup error: {e}")

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


# ── Error Handlers ────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error", "message": str(error)}), 500


@app.route("/health")
def health():
    """Health check endpoint for monitoring"""
    return jsonify({"status": "ok", "message": "Server is running"}), 200


# Initialize database on startup
try:
    init_db()
except Exception as e:
    print(f"Warning: Could not initialize database: {e}")

if __name__ == "__main__":
    print("\n" + "="*50)
    print("  💍 Matrimonial App running! Please hang on")
    print("  Open: http://127.0.0.1:5000")
    print("="*50 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
