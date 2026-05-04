import os
import csv
from pymongo import MongoClient
import certifi
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MONGO_URI = os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("DB_NAME", "bi_portal")

if not MONGO_URI:
    print("Error: MONGODB_URI not found in environment")
    exit(1)

def seed_all():
    try:
        client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        db = client[DB_NAME]
        
        # 1. Seed Sales
        print("Processing sales data...")
        sales_path = "Dataset/clean_sales.csv"
        if os.path.exists(sales_path):
            db.sales.delete_many({}) # Clear existing
            with open(sales_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                batch = []
                count = 0
                for row in reader:
                    try:
                        # Convert types
                        row['sales_amount'] = float(row['sales_amount']) if row['sales_amount'] else 0.0
                        row['profit'] = float(row['profit']) if row['profit'] else 0.0
                        row['quantity'] = int(row['quantity']) if row['quantity'] else 0
                        row['discount'] = float(row['discount']) if row['discount'] else 0.0
                        if 'user_id' in row and row['user_id']:
                            row['user_id'] = int(row['user_id'])
                        batch.append(row)
                        count += 1
                        
                        if len(batch) >= 1000:
                            db.sales.insert_many(batch)
                            batch = []
                            print(f"Inserted {count} sales records...")
                    except Exception as e:
                        print(f"Skipping row due to error: {e}")
                
                if batch:
                    db.sales.insert_many(batch)
            print(f"Successfully seeded sales. Total records: {db.sales.count_documents({})}")
        else:
            print("Warning: clean_sales.csv not found")

        # 2. Seed Users
        print("\nProcessing users data...")
        users_path = "Dataset/clean_users.csv"
        if os.path.exists(users_path):
            db.users.delete_many({})
            with open(users_path, mode='r', encoding='utf-8') as f:
                reader = csv.reader(f)
                batch = []
                for row in reader:
                    if len(row) < 5: continue
                    try:
                        user = {
                            "email": row[2].strip().lower(),
                            "name": row[1],
                            "role": row[3],
                            "password": row[4],
                            "city": row[5] if len(row) > 5 else ""
                        }
                        batch.append(user)
                    except Exception as e:
                        print(f"Skipping user row: {e}")
                
                if batch:
                    db.users.insert_many(batch)
            print(f"Successfully seeded users. Total: {db.users.count_documents({})}")
        else:
            print("Warning: clean_users.csv not found")

        # 3. Seed KPI (Optional but good for completeness)
        print("\nProcessing KPI data...")
        kpi_path = "Dataset/clean_kpi.csv"
        if os.path.exists(kpi_path):
            db.kpi.delete_many({})
            with open(kpi_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                batch = list(reader)
                for row in batch:
                    for key in ['total_sales', 'average_sales', 'monthly_growth_percent']:
                        if key in row and row[key]:
                            row[key] = float(row[key])
                if batch:
                    db.kpi.insert_many(batch)
            print(f"Successfully seeded KPI table. Total: {db.kpi.count_documents({})}")

        print("\nAll data seeded successfully!")

    except Exception as e:
        print(f"Critical Error during seeding: {e}")

if __name__ == "__main__":
    seed_all()
