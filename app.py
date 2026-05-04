from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from pymongo import MongoClient
import os
import certifi
import re
from bson import ObjectId
from dotenv import load_dotenv
from services.ai_insights import generate_insights, ask_ai_question

# Load environment variables
load_dotenv()

app = Flask(
    __name__,
    template_folder="frontend",
    static_folder="frontend",
    static_url_path=""
)

CORS(app)

# MongoDB Configuration
MONGO_URI = os.environ.get("MONGODB_URI", "mongodb+srv://officialabhi730_db_user:OVbc4OuLQfeLyCmL@cluster442.nfzrr6j.mongodb.net/")
DB_NAME = os.environ.get("DB_NAME", "bi_portal")

try:
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client[DB_NAME]
    print(f"✅ Connected to MongoDB Atlas: {DB_NAME}")
except Exception as e:
    print(f"❌ MongoDB Connection Error: {e}")

# Helper to serialize Mongo docs
def serialize(doc):
    if not doc: return None
    doc["id"] = str(doc.get("_id", ""))
    if "_id" in doc: del doc["_id"]
    return doc

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

@app.route("/ai-insights")
def ai_insights_page():
    return render_template("ai_insights.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    try:
        data = request.get_json() or {}
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", "")).strip()

        user = db.users.find_one({"email": email, "password": password})

        if user:
            return jsonify({
                "status": "success",
                "user": {
                    "id": str(user["_id"]),
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
        search = request.args.get("q", "").strip()
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 10))
        skip = (page - 1) * limit

        query = {}
        if search:
            regex = re.compile(search, re.IGNORECASE)
            query = {"$or": [
                {"product_name": regex},
                {"category": regex},
                {"sub_category": regex},
                {"region": regex},
                {"city": regex},
                {"customer_name": regex}
            ]}

        total = db.sales.count_documents(query)
        cursor = db.sales.find(query).sort("_id", -1).skip(skip).limit(limit)
        
        data = [serialize(d) for d in cursor]

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
        # Simple auto-increment replacement (Mongo uses ObjectIds normally)
        # If the user specifically wants numeric IDs, we can manage a counter,
        # but standard Mongo practice is ObjectId.
        result = db.sales.insert_one(data)
        return jsonify({"message": "Added Successfully", "id": str(result.inserted_id)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/update_sales/<id>", methods=["PUT"])
def update_sales(id):
    try:
        data = request.get_json() or {}
        if "_id" in data: del data["_id"]
        if "id" in data: del data["id"]

        result = db.sales.update_one({"_id": ObjectId(id)}, {"$set": data})
        
        if result.matched_count == 0:
            # Fallback for old numeric IDs if they exist
            result = db.sales.update_one({"id": int(id)}, {"$set": data})

        if result.matched_count == 0:
            return jsonify({"error": "Record not found"}), 404
            
        return jsonify({"message": "Updated"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/delete_sales/<id>", methods=["DELETE"])
def delete_sales(id):
    try:
        result = db.sales.delete_one({"_id": ObjectId(id)})
        if result.deleted_count == 0:
            result = db.sales.delete_one({"id": int(id)})

        return jsonify({"message": "Deleted"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/kpi", methods=["GET"])
def get_kpi():
    try:
        # Aggregation for Basic stats
        pipeline_basic = [
            {"$group": {
                "_id": None,
                "total_sales": {"$sum": "$sales_amount"},
                "total_profit": {"$sum": "$profit"},
                "count": {"$sum": 1}
            }}
        ]
        basic_stats = list(db.sales.aggregate(pipeline_basic))
        stats = basic_stats[0] if basic_stats else {"total_sales":0, "total_profit":0, "count":0}

        total_sales = stats["total_sales"]
        total_profit = stats["total_profit"]
        total_orders = stats["count"]
        
        aov = total_sales / total_orders if total_orders > 0 else 0
        margin = (total_profit / total_sales) * 100 if total_sales > 0 else 0
        
        # Helper for Top Performers
        def get_top(field):
            agg = list(db.sales.aggregate([
                {"$group": {"_id": f"${field}", "total": {"$sum": "$sales_amount"}}},
                {"$sort": {"total": -1}},
                {"$limit": 1}
            ]))
            return agg[0]["_id"] if agg else "N/A"

        # Chart Data: Region
        regions = list(db.sales.aggregate([
            {"$group": {"_id": "$region", "value": {"$sum": "$sales_amount"}}},
            {"$sort": {"value": -1}}
        ]))
        region_data = [{"name": r["_id"], "value": round(r["value"], 2)} for r in regions]

        # Chart Data: Category
        categories = list(db.sales.aggregate([
            {"$group": {"_id": "$category", "value": {"$sum": "$sales_amount"}}},
            {"$sort": {"value": -1}}
        ]))
        category_data = [{"name": r["_id"], "value": round(r["value"], 2)} for r in categories]

        # Chart Data: Trend (Monthly)
        # Note: Date in Mongo should be stored as Date objects or YYYY-MM-DD strings
        trend = list(db.sales.aggregate([
            {"$project": {"month": {"$substr": ["$date", 0, 7]}, "sales_amount": 1}},
            {"$group": {"_id": "$month", "value": {"$sum": "$sales_amount"}}},
            {"$sort": {"_id": 1}},
            {"$limit": 12}
        ]))
        trend_data = [{"name": r["_id"], "value": round(r["value"], 2)} for r in trend]

        # Top 5 Customers
        customers = list(db.sales.aggregate([
            {"$group": {"_id": "$customer_name", "value": {"$sum": "$sales_amount"}}},
            {"$sort": {"value": -1}},
            {"$limit": 5}
        ]))
        customer_data = [{"name": r["_id"], "value": round(r["value"], 2)} for r in customers]
        
        # Recent 5 Transactions
        recent = list(db.sales.find({}, {"product_name":1, "sales_amount":1, "date":1, "customer_name":1}).sort([("date", -1), ("_id", -1)]).limit(5))
        recent_data = [serialize(r) for r in recent]

        return jsonify({
            "total_sales": round(total_sales, 2),
            "total_profit": round(total_profit, 2),
            "total_orders": total_orders,
            "aov": round(aov, 2),
            "margin": round(margin, 2),
            "top_category": get_top("category"),
            "top_region": get_top("region"),
            "top_product": get_top("product_name"),
            "charts": {
                "region": region_data,
                "category": category_data,
                "trend": trend_data,
                "customers": customer_data
            },
            "recent_data": recent_data,
            "metadata": {
                "db_engine": "MongoDB Atlas",
                "db_status": "Operational",
                "sync_status": "Real-time",
                "source": "Dataset (Cloud Synced)"
            }
        })

    except Exception as e:
        print(f"KPI Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai-insights", methods=["GET"])
def get_ai_insights():
    try:
        # Fetch last 100 records for context
        cursor = db.sales.find().sort("_id", -1).limit(100)
        data = [serialize(d) for d in cursor]
        
        insights = generate_insights(data)
        return jsonify({"insights": insights})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ask-ai", methods=["POST"])
def ask_ai():
    try:
        req_data = request.get_json()
        question = req_data.get("question")
        
        # Fetch last 100 records for context
        cursor = db.sales.find().sort("_id", -1).limit(100)
        data = [serialize(d) for d in cursor]
        
        answer = ask_ai_question(question, data)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
