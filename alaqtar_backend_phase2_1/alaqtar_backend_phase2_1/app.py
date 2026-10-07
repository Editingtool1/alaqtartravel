import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL", "")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "")
ADMIN_USER = os.environ.get("ADMIN_USER", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
if not app.secret_key or not ADMIN_USER or not ADMIN_PASSWORD:
    raise RuntimeError("Set SECRET_KEY, ADMIN_USER and ADMIN_PASSWORD environment variables before starting the app.")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

def db():
    con = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return con

def init_db():
    con = db()
    con.execute("""
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
    """)
    con.commit()
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
    rows = con.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    con.close()
    return render_template("orders.html", rows=rows)

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

@app.post("/api/orders")
def create_order():
    data = request.get_json(silent=True) or request.form
    name = (data.get("customer_name") or "").strip()
    phone = (data.get("phone") or "").strip()
    service = (data.get("service") or "").strip()
    if not name or not phone or not service:
        return jsonify({"ok":False,"error":"customer_name, phone and service are required"}), 400
    order_no = "AQT-" + datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
    con = db()
    con.execute("""INSERT INTO orders(order_no,customer_name,phone,service,status,notes,created_at)
                   VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                (order_no,name,phone,service,"جديد",data.get("notes",""),datetime.now().isoformat(timespec="seconds")))
    con.commit(); con.close()
    return jsonify({"ok":True,"order_no":order_no}), 201

@app.get("/health")
def health():
    return {"ok": True, "service": "ALAQTAR Backend"}

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT","5000")), debug=True)
