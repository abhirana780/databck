from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import sqlite3
import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(
    __name__,
    template_folder="../frontend",
    static_folder="../frontend",
    static_url_path=""
)

CORS(app)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/powerbi")
def powerbi():
    return render_template("powerbi.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    try:
        data = request.get_json() or {}
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", "")).strip()

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE LOWER(TRIM(email)) = ? AND TRIM(password) = ?",
            (email, password)
        ).fetchone()
        conn.close()

        if user:
            return jsonify({
                "status": "success",
                "user": {
                    "id": user["user_id"],
                    "name": user["name"],
                    "email": user["email"],
                    "role": user["role"]
                }
            })

        return jsonify({"status": "fail"}), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/sales", methods=["GET"])
def get_sales():
    try:
        search = request.args.get("q", "").lower()
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 10))
        offset = (page - 1) * limit

        conn = get_db_connection()
        
        query = "SELECT * FROM sales"
        params = []
        
        if search:
            query += " WHERE LOWER(product_name) LIKE ? OR LOWER(category) LIKE ? OR LOWER(sub_category) LIKE ? OR LOWER(region) LIKE ? OR LOWER(city) LIKE ? OR LOWER(customer_name) LIKE ?"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"])
            
        # Count total
        count_query = f"SELECT COUNT(*) FROM ({query}) AS t"
        total_row = conn.execute(count_query, params).fetchone()
        total = total_row[0] if total_row else 0
        
        # Paginate and Sort
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        rows = conn.execute(query, params).fetchall()
        conn.close()

        data = [dict(row) for row in rows]

        return jsonify({
            "data": data,
            "total": total
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/add_sales", methods=["POST"])
def add_sales():
    try:
        data = request.get_json() or {}
        
        conn = get_db_connection()
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO sales ({columns}) VALUES ({placeholders})"
        
        conn.execute(query, list(data.values()))
        conn.commit()
        conn.close()

        return jsonify({"message": "Added Successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/update_sales/<int:id>", methods=["PUT"])
def update_sales(id):
    try:
        data = request.get_json() or {}
        
        conn = get_db_connection()
        set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
        query = f"UPDATE sales SET {set_clause} WHERE id = ?"
        
        params = list(data.values()) + [id]
        
        cursor = conn.execute(query, params)
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "Record not found"}), 404
            
        conn.close()
        return jsonify({"message": "Updated"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/delete_sales/<int:id>", methods=["DELETE"])
def delete_sales(id):
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM sales WHERE id = ?", (id,))
        conn.commit()
        conn.close()

        return jsonify({"message": "Deleted"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/users", methods=["GET"])
def get_users():
    try:
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM users").fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/kpi", methods=["GET"])
def get_kpi():
    try:
        conn = get_db_connection()
        # Basic stats
        stats = conn.execute("SELECT SUM(sales_amount), SUM(profit), COUNT(*) FROM sales").fetchone()
        
        total_sales = stats[0] or 0
        total_profit = stats[1] or 0
        total_orders = stats[2] or 0
        
        # Advanced calculations
        aov = total_sales / total_orders if total_orders > 0 else 0
        margin = (total_profit / total_sales) * 100 if total_sales > 0 else 0
        
        # Category Breakdown for Top Performer
        top_cat = conn.execute("SELECT category, SUM(sales_amount) as s FROM sales GROUP BY category ORDER BY s DESC LIMIT 1").fetchone()
        
        # Regional Top Performer
        top_reg = conn.execute("SELECT region, SUM(sales_amount) as s FROM sales GROUP BY region ORDER BY s DESC LIMIT 1").fetchone()

        # Product Top Performer
        top_prod = conn.execute("SELECT product_name, SUM(sales_amount) as s FROM sales GROUP BY product_name ORDER BY s DESC LIMIT 1").fetchone()

        # Region Breakdown
        regions = conn.execute("SELECT region, SUM(sales_amount) as s FROM sales GROUP BY region ORDER BY s DESC").fetchall()
        region_data = [{"name": r["region"], "value": round(r["s"], 2)} for r in regions]
        
        # Category Breakdown
        categories = conn.execute("SELECT category, SUM(sales_amount) as s FROM sales GROUP BY category").fetchall()
        category_data = [{"name": r["category"], "value": round(r["s"], 2)} for r in categories]
        
        # Monthly Trend (Last 6 Months roughly or all)
        # Using strftime to group by month
        trend = conn.execute("SELECT strftime('%Y-%m', date) as m, SUM(sales_amount) as s FROM sales GROUP BY m ORDER BY m ASC LIMIT 12").fetchall()
        trend_data = [{"name": r["m"], "value": round(r["s"], 2)} for r in trend]

        # Top 5 Customers
        customers = conn.execute("SELECT customer_name, SUM(sales_amount) as s FROM sales GROUP BY customer_name ORDER BY s DESC LIMIT 5").fetchall()
        customer_data = [{"name": r["customer_name"], "value": round(r["s"], 2)} for r in customers]
        
        # Recent 5 Transactions
        recent = conn.execute("SELECT product_name, sales_amount, date, customer_name FROM sales ORDER BY date DESC, id DESC LIMIT 5").fetchall()
        recent_data = [dict(r) for r in recent]

        conn.close()

        return jsonify({
            "total_sales": total_sales,
            "total_profit": total_profit,
            "total_orders": total_orders,
            "aov": round(aov, 2),
            "margin": round(margin, 2),
            "top_category": top_cat["category"] if top_cat else "N/A",
            "top_region": top_reg["region"] if top_reg else "N/A",
            "top_product": top_prod["product_name"] if top_prod else "N/A",
            "charts": {
                "region": region_data,
                "category": category_data,
                "trend": trend_data,
                "customers": customer_data
            },
            "recent_data": recent_data
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
