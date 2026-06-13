import os, json, hashlib, uuid, logging
from datetime import datetime
from functools import wraps
from flask import Flask, request, session, redirect, url_for, render_template, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")

# ── JSON logging ──────────────────────────────────────────────────────────────
class JSONFmt(logging.Formatter):
    def format(self, record):
        d = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level":     record.levelname,
            "message":   record.getMessage(),
        }
        if hasattr(record, "extra"):
            d.update(record.extra)
        return json.dumps(d)

_handler_file = logging.FileHandler("/app-logs/app.log")
_handler_file.setFormatter(JSONFmt())
_handler_stdout = logging.StreamHandler()
_handler_stdout.setFormatter(JSONFmt())

log = logging.getLogger("webapp")
log.setLevel(logging.INFO)
log.addHandler(_handler_file)
log.addHandler(_handler_stdout)

# ── DB helpers ────────────────────────────────────────────────────────────────
def _db():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASS"],
        cursor_factory=RealDictCursor,
    )

def get_db():
    if "db" not in session:
        import time
        for i in range(5):
            try:
                conn = _db()
                return conn
            except psycopg2.OperationalError:
                time.sleep(2 ** i)
        raise RuntimeError("DB unavailable")
    return session["db"]

def _hash(pw, salt):
    return hashlib.sha256((salt + pw).encode()).hexdigest()

def _seed():
    try:
        conn = _db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()["count"] == 0:
            salt = "elk-lab-admin-salt-01"
            pw_hash = _hash("Admin@2024!", salt)
            cur.execute(
                "INSERT INTO users (username, email, password_hash, salt, role) VALUES (%s,%s,%s,%s,%s)",
                ("admin", "admin@lab.local", pw_hash, salt, "admin"),
            )
            conn.commit()
        conn.close()
    except Exception as e:
        log.error("Seed failed: %s", e)

def _log(action, outcome, **kw):
    entry = {"action": action, "outcome": outcome, **kw,
             "ip": request.remote_addr, "method": request.method,
             "path": request.path, "request_id": str(uuid.uuid4())}
    log.info("event", extra={"extra": entry})
    try:
        conn = _db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO activity_log (user_id, username, action, outcome, ip_address, user_agent, path) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (kw.get("user_id"), kw.get("user"), action, outcome,
             request.remote_addr, request.user_agent.string, request.path),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

# ── Auth decorator ────────────────────────────────────────────────────────────
def lr(f):
    @wraps(f)
    def decorated(*a, **kw):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*a, **kw)
    return decorated

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    try:
        conn = _db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cur.fetchone()
        conn.close()
    except Exception as e:
        log.error("DB error on login: %s", e)
        return render_template("login.html", error="Service unavailable")
    if user and user["password_hash"] == _hash(password, user["salt"]):
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        try:
            conn = _db()
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET last_login=NOW(), login_count=login_count+1 WHERE id=%s",
                (user["id"],),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass
        _log("login", "success", user=username, user_id=user["id"])
        return redirect(url_for("dashboard"))
    _log("login", "failure", user=username)
    return render_template("login.html", error="Invalid credentials")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    username = request.form.get("username", "").strip()
    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    if not username or not password:
        return render_template("register.html", error="Username and password required")
    salt = str(uuid.uuid4())
    pw_hash = _hash(password, salt)
    try:
        conn = _db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, email, password_hash, salt, role) VALUES (%s,%s,%s,%s,'user') RETURNING id",
            (username, email, pw_hash, salt),
        )
        user_id = cur.fetchone()["id"]
        conn.commit()
        conn.close()
    except psycopg2.errors.UniqueViolation:
        return render_template("register.html", error="Username already taken")
    except Exception as e:
        return render_template("register.html", error="Registration failed")
    _log("register", "success", user=username, user_id=user_id)
    return redirect(url_for("login"))

@app.route("/logout")
@lr
def logout():
    _log("logout", "success", user=session.get("username"), user_id=session.get("user_id"))
    session.clear()
    return render_template("logout.html")

@app.route("/dashboard")
@lr
def dashboard():
    try:
        conn = _db()
        cur = conn.cursor()
        cur.execute("SELECT id, username, email, role, created_at, last_login, login_count FROM users ORDER BY id")
        users = cur.fetchall()
        cur.execute("SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 20")
        activity = cur.fetchall()
        conn.close()
    except Exception as e:
        log.error("Dashboard DB error: %s", e)
        users, activity = [], []
    return render_template("dashboard.html", users=users, activity=activity)

@app.route("/api/health")
def health():
    try:
        conn = _db()
        conn.close()
        db_ok = True
    except Exception:
        db_ok = False
    return jsonify({"status": "ok" if db_ok else "degraded", "db": db_ok, "timestamp": datetime.utcnow().isoformat()})

@app.route("/api/users")
@lr
def api_users():
    if session.get("role") != "admin":
        return jsonify({"error": "forbidden"}), 403
    conn = _db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, role, created_at FROM users")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

# ── Startup seed ──────────────────────────────────────────────────────────────
with app.app_context():
    _seed()
