import os
import psycopg2
import requests
from uuid import uuid4
from psycopg2.extras import RealDictCursor
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")
SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "order-documents")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
CORS(app, resources={
    r"/api/*": {
        "origins": "https://editingtool1.github.io"
    }
})
app.secret_key = os.environ.get("SECRET_KEY", "")
ADMIN_USER = os.environ.get("ADMIN_USER", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
if not app.secret_key or not ADMIN_USER or not ADMIN_PASSWORD:
    raise RuntimeError("Set SECRET_KEY, ADMIN_USER and ADMIN_PASSWORD environment variables before starting the app.")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

class DBConnection:
    def __init__(self):
        self.con = psycopg2.connect(
            DATABASE_URL,
            cursor_factory=RealDictCursor
        )

    def cursor(self):
        return self.con.cursor()

    def execute(self, query, params=None):
        cur = self.con.cursor()
        cur.execute(query, params or ())
        return cur

    def commit(self):
        self.con.commit()

    def rollback(self):
        self.con.rollback()

    def close(self):
        self.con.close()


def db():
    return DBConnection()

def init_db():
    con = db()
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
      id SERIAL PRIMARY KEY,
      order_no TEXT UNIQUE NOT NULL,
      customer_name TEXT NOT NULL,
      phone TEXT NOT NULL,
      service TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'جديد',
      notes TEXT DEFAULT '',
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS companies (
      id SERIAL PRIMARY KEY,
      name TEXT NOT NULL,
      phone TEXT DEFAULT '',
      balance REAL NOT NULL DEFAULT 0,
      credit_limit REAL NOT NULL DEFAULT 0,
      markup_type TEXT NOT NULL DEFAULT 'fixed',
      markup_value REAL NOT NULL DEFAULT 0,
      active INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS services (
      id SERIAL PRIMARY KEY,
      name_ar TEXT NOT NULL,
      name_en TEXT DEFAULT '',
      category TEXT NOT NULL DEFAULT 'general',
      active INTEGER NOT NULL DEFAULT 1,
      base_price REAL NOT NULL DEFAULT 0,
      currency TEXT NOT NULL DEFAULT 'IQD',
      requirements TEXT DEFAULT '',
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS transactions (
      id SERIAL PRIMARY KEY,
      company_id INTEGER NOT NULL,
      type TEXT NOT NULL,
      amount REAL NOT NULL,
      note TEXT DEFAULT '',
      created_at TEXT NOT NULL,
      FOREIGN KEY(company_id) REFERENCES companies(id)
    );
    CREATE TABLE IF NOT EXISTS order_files (
    id SERIAL PRIMARY KEY,
    order_no TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_url TEXT NOT NULL,
    file_type TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY(order_no) REFERENCES orders(order_no)
);
    """)
    con.commit()
    cur.close()
    con.close()

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped

@app.route("/")
def home():
    return redirect(url_for("dashboard") if session.get("admin") else url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == ADMIN_USER and request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("dashboard"))
        flash("بيانات الدخول غير صحيحة")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/admin")
@login_required
def dashboard():
    con = db()
    counts = {
        "orders": con.execute("SELECT COUNT(*) c FROM orders").fetchone()["c"],
        "new_orders": con.execute("SELECT COUNT(*) c FROM orders WHERE status='جديد'").fetchone()["c"],
        "companies": con.execute("SELECT COUNT(*) c FROM companies WHERE active=1").fetchone()["c"],
    }
    recent = con.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 8").fetchall()
    con.close()
    return render_template("dashboard.html", counts=counts, recent=recent)

@app.route("/admin/orders")
@login_required
def orders():
    con = db()
    rows = con.execute("""
    SELECT o.*,
           COUNT(f.id) AS files_count
    FROM orders o
    LEFT JOIN order_files f ON f.order_no = o.order_no
    GROUP BY o.id
    ORDER BY o.id DESC
""").fetchall() 
    con.close()
    return render_template("orders.html", rows=rows)
@app.get("/admin/orders/<order_no>/files")
@login_required
def order_files(order_no):
    con = db()

    order = con.execute(
        "SELECT * FROM orders WHERE order_no=%s",
        (order_no,)
    ).fetchone()

    files = con.execute(
        """SELECT * FROM order_files
        WHERE order_no=%s
        ORDER BY id DESC""",
        (order_no,)
    ).fetchall()

    con.close()

    if not order:
        return "الطلب غير موجود", 404

    return render_template(
        "order_files.html",
        order=order,
        files=files
    )@app.get("/admin/files/<int:file_id>")
@login_required
def admin_file(file_id):
    con = db()

    file_row = con.execute(
        "SELECT * FROM order_files WHERE id=%s",
        (file_id,)
    ).fetchone()

    con.close()

    if not file_row:
        return "الملف غير موجود", 404

    storage_path = file_row["file_url"]

    sign_url = (
        f"{SUPABASE_URL}/storage/v1/object/sign/"
        f"{SUPABASE_BUCKET}/{storage_path}"
    )

    headers = {
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
        "apikey": SUPABASE_SECRET_KEY,
        "Content-Type": "application/json",
    }

    response = requests.post(
        sign_url,
        headers=headers,
        json={"expiresIn": 300},
        timeout=30,
    )

    if not response.ok:
        print(
            "SUPABASE SIGN ERROR:",
            response.status_code,
            response.text
        )
        return "تعذر فتح المستمسك", 500

    data = response.json()

    signed_path = (
        data.get("signedURL")
        or data.get("signedUrl")
    )

    if not signed_path:
        return "تعذر إنشاء رابط المستمسك", 500

    if signed_path.startswith("http"):
        signed_url = signed_path
    else:
        signed_url = f"{SUPABASE_URL}{signed_path}"

    return redirect(signed_url)
@app.post("/admin/orders/<int:oid>/status")
@login_required
def order_status(oid):
    status = request.form.get("status","جديد")
    allowed = ["جديد","قيد التدقيق","نقص مستمسكات","قيد التنفيذ","مكتمل","مرفوض","ملغي"]
    if status in allowed:
        con = db()
        con.execute("UPDATE orders SET status=%s WHERE id=%s", (status, oid))
        con.commit(); con.close()
    return redirect(url_for("orders"))

@app.route("/admin/companies", methods=["GET","POST"])
@login_required
def companies():
    con = db()
    if request.method == "POST":
        con.execute("""INSERT INTO companies
        (name,phone,balance,credit_limit,markup_type,markup_value,created_at)
        VALUES(%s,%s,%s,%s,%s,%s,%s)""", (
            request.form["name"], request.form.get("phone",""),
            float(request.form.get("balance") or 0), float(request.form.get("credit_limit") or 0),
            request.form.get("markup_type","fixed"), float(request.form.get("markup_value") or 0),
            datetime.now().isoformat(timespec="seconds")
        ))
        con.commit()
        flash("تم إنشاء حساب الشركة")
        con.close()
        return redirect(url_for("companies"))
    rows = con.execute("SELECT * FROM companies ORDER BY id DESC").fetchall()
    con.close()
    return render_template("companies.html", rows=rows)

@app.post("/admin/companies/<int:cid>/transaction")
@login_required
def transaction(cid):
    t = request.form.get("type")
    amount = float(request.form.get("amount") or 0)
    note = request.form.get("note","")
    sign = 1 if t in ("إيداع","استرجاع") else -1
    con = db()
    con.execute("INSERT INTO transactions(company_id,type,amount,note,created_at) VALUES(%s,%s,%s,%s,%s)",
                (cid,t,amount,note,datetime.now().isoformat(timespec="seconds")))
    con.execute("UPDATE companies SET balance=balance+%s WHERE id=%s", (sign*amount,cid))
    con.commit(); con.close()
    return redirect(url_for("companies"))


@app.route("/admin/services", methods=["GET","POST"])
@login_required
def services():
    con = db()
    if request.method == "POST":
        con.execute("""INSERT INTO services
        (name_ar,name_en,category,active,base_price,currency,requirements,created_at)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""", (
            request.form["name_ar"], request.form.get("name_en",""),
            request.form.get("category","general"), 1,
            float(request.form.get("base_price") or 0),
            request.form.get("currency","IQD"),
            request.form.get("requirements",""),
            datetime.now().isoformat(timespec="seconds")
        ))
        con.commit()
        flash("تمت إضافة الخدمة")
    rows = con.execute("SELECT * FROM services ORDER BY id DESC").fetchall()
    con.close()
    return render_template("services.html", rows=rows)

@app.post("/admin/services/<int:sid>/toggle")
@login_required
def toggle_service(sid):
    con = db()
    con.execute("UPDATE services SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=%s", (sid,))
    con.commit(); con.close()
    return redirect(url_for("services"))

@app.get("/api/services")
def public_services():
    con = db()
    rows = con.execute("""SELECT id,name_ar,name_en,category,base_price,currency,requirements
                          FROM services WHERE active=1 ORDER BY id DESC""").fetchall()
    con.close()
    return jsonify([dict(r) for r in rows])
def upload_to_supabase(file, order_no):
    if not file or not file.filename:
        return None

    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
    }

    if file.mimetype not in allowed_types:
        raise ValueError("نوع الملف غير مسموح")

    original_name = file.filename
    ext = os.path.splitext(original_name)[1].lower()

    safe_name = f"{uuid4().hex}{ext}"
    storage_path = f"{order_no}/{safe_name}"

    upload_url = (
        f"{SUPABASE_URL}/storage/v1/object/"
        f"{SUPABASE_BUCKET}/{storage_path}"
    )

    headers = {
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
        "apikey": SUPABASE_SECRET_KEY,
        "Content-Type": file.mimetype,
    }

    response = requests.post(
        upload_url,
        headers=headers,
        data=file.read(),
        timeout=60,
    )

    if not response.ok:
        raise RuntimeError(
            f"Supabase upload failed: {response.status_code} {response.text}"
        )

    return {
        "file_name": original_name,
        "file_url": storage_path,
        "file_type": file.mimetype,
    }
@app.post("/api/orders")
def create_order():
    data = request.form

    name = (data.get("customer_name") or "").strip()
    phone = (data.get("phone") or "").strip()
    service = (data.get("service") or "").strip()
    notes = (data.get("notes") or "").strip()

    if not name or not phone or not service:
        return jsonify({
            "ok": False,
            "error": "customer_name, phone and service are required"
        }), 400

    files = request.files.getlist("documents")

    order_no = "AQT-" + datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
    created_at = datetime.now().isoformat(timespec="seconds")

    con = db()

    try:
        # إنشاء الطلب
        con.execute(
            """INSERT INTO orders
            (order_no, customer_name, phone, service, status, notes, created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (
                order_no,
                name,
                phone,
                service,
                "جديد",
                notes,
                created_at
            )
        )

        # رفع المستمسكات وتسجيلها
        uploaded_files = []

        for file in files:
            if not file or not file.filename:
                continue

            uploaded = upload_to_supabase(file, order_no)

            if uploaded:
                con.execute(
                    """INSERT INTO order_files
                    (order_no, file_name, file_url, file_type, created_at)
                    VALUES (%s,%s,%s,%s,%s)""",
                    (
                        order_no,
                        uploaded["file_name"],
                        uploaded["file_url"],
                        uploaded["file_type"],
                        created_at
                    )
                )

                uploaded_files.append(uploaded)

        con.commit()

        return jsonify({
            "ok": True,
            "order_no": order_no,
            "files_count": len(uploaded_files)
        }), 201

    except Exception as e:
        con.rollback()
        print("CREATE ORDER ERROR:", e)

        return jsonify({
            "ok": False,
            "error": "تعذر تسجيل الطلب أو رفع المستمسكات"
        }), 500

    finally:
        con.close()

@app.get("/health")
def health():
    return {"ok": True, "service": "ALAQTAR Backend"}

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT","5000")), debug=True)
