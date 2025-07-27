from pymongo import MongoClient
from datetime import datetime, timedelta
import dateutil.parser

# --- CONFIGURE THIS ---
MONGO_URI = "mongodb://localhost:27017/fleet_management"  # <-- Your DB name
COLLECTIONS_FIELDS = {
    "trips": ["start_date", "end_date"],
    "expenses": ["expense_date", "submitted_date", "approved_date"],
    "subtrips": ["date", "end_date"]
    # Add other collections/fields as needed
}
# ----------------------

def try_parse_date(value):
    """Try to parse value (string) to datetime, else return original value."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except Exception:
            try:
                return dateutil.parser.parse(value)
            except Exception:
                return value
    return value

def fix_collection_dates(db, collection_name, date_fields):
    collection = db[collection_name]
    count = 0
    for doc in collection.find():
        update = {}
        for field in date_fields:
            val = doc.get(field)
            # If the field exists and is a string, try to parse it.
            if val and isinstance(val, str):
                parsed = try_parse_date(val)
                if isinstance(parsed, datetime):
                    update[field] = parsed
        if update:
            print(f"Updating {collection_name} {doc['_id']}: {update}")
            collection.update_one({"_id": doc["_id"]}, {"$set": update})
            count += 1
    print(f"Updated {count} documents in {collection_name}")

def main():
    client = MongoClient(MONGO_URI)
    db = client.get_default_database()
    if db is None:
        # fallback if get_default_database() fails
        db = client["fleet_management"]
    for coll, fields in COLLECTIONS_FIELDS.items():
        print(f"Processing {coll}...")
        fix_collection_dates(db, coll, fields)
    print("Done.")

if __name__ == "__main__":
    main()