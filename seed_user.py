import os
from pymongo import MongoClient
import certifi
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MONGO_URI = os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("DB_NAME", "bi_portal")

if not MONGO_URI:
    print("❌ MONGODB_URI not found in environment")
    exit(1)

try:
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client[DB_NAME]
    
    new_user = {
        "email": "gary8200@test.com",
        "password": "admin123",
        "name": "Gary",
        "role": "admin"
    }

    # Check if user already exists
    existing_user = db.users.find_one({"email": new_user["email"]})
    
    if existing_user:
        print(f"Info: User {new_user['email']} already exists.")
        # Update password just in case
        db.users.update_one({"email": new_user["email"]}, {"$set": {"password": new_user["password"]}})
        print("Success: Password updated.")
    else:
        db.users.insert_one(new_user)
        print(f"Success: User {new_user['email']} created successfully.")

except Exception as e:
    print(f"Error: {e}")
