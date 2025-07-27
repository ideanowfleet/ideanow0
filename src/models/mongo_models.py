from datetime import datetime
from bson import ObjectId
from flask import current_app
from pymongo import MongoClient

def get_db():
    return current_app.db

def bson_to_str(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: bson_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [bson_to_str(i) for i in obj]
    else:
        return obj

class BaseModel:
    @classmethod
    def get_collection(cls):
        db = get_db()
        return db[cls.collection_name]

    @classmethod
    def find_all(cls, filter_dict=None):
        collection = cls.get_collection()
        if filter_dict:
            return list(collection.find(filter_dict))
        return list(collection.find())

    @classmethod
    def find_by_id(cls, doc_id):
        collection = cls.get_collection()
        if isinstance(doc_id, ObjectId):
            return collection.find_one({"_id": doc_id})
        try:
            return collection.find_one({"_id": ObjectId(doc_id)})
        except Exception:
            return None

    @classmethod
    def insert_one(cls, document):
        collection = cls.get_collection()
        if 'created_at' not in document:
            document['created_at'] = datetime.utcnow()
        document['updated_at'] = datetime.utcnow()
        result = collection.insert_one(document)
        return result.inserted_id

    @classmethod
    def update_one(cls, doc_id, update_dict):
        collection = cls.get_collection()
        if isinstance(doc_id, str):
            doc_id = ObjectId(doc_id)
        update_dict['updated_at'] = datetime.utcnow()
        return collection.update_one({"_id": doc_id}, {"$set": update_dict})

    @classmethod
    def delete_one(cls, doc_id):
        collection = cls.get_collection()
        if isinstance(doc_id, str):
            doc_id = ObjectId(doc_id)
        return collection.delete_one({"_id": doc_id})

class Truck(BaseModel):
    collection_name = 'trucks'

    @staticmethod
    def to_dict(truck_doc):
        if not truck_doc:
            return None
        truck_doc = truck_doc.copy()
        truck_doc['id'] = str(truck_doc['_id'])
        del truck_doc['_id']
        return bson_to_str(truck_doc)

class Employee(BaseModel):
    collection_name = 'employees'

    @staticmethod
    def to_dict(employee_doc):
        if not employee_doc:
            return None
        employee_doc = employee_doc.copy()
        employee_doc['id'] = str(employee_doc['_id'])
        del employee_doc['_id']
        return bson_to_str(employee_doc)

class Trip(BaseModel):
    collection_name = 'trips'

    @staticmethod
    def to_dict(trip_doc):
        if not trip_doc:
            return None
        trip_doc = trip_doc.copy()
        trip_doc['id'] = str(trip_doc['_id'])
        del trip_doc['_id']
        return bson_to_str(trip_doc)

    @staticmethod
    def to_dict_populated(trip_doc):
        from src.models.mongo_models import Truck, Employee
        trip_dict = Trip.to_dict(trip_doc)

        # Ensure all expense fields exist in the output (always present, even if 0)
        for field in [
            "toll", "rto", "adblue", "driver_salary", "labour_charges", "extra_expense",
            "fuel_cost", "fuel_consumed", "other_expenses", "profit", "revenue"
        ]:
            if field not in trip_dict:
                trip_dict[field] = 0

        # Truck
        truck = Truck.find_by_id(trip_dict.get('truck_id'))
        trip_dict['truck_number'] = truck.get('truck_number') if truck else ''
        # Driver by _id (stored in driver_id as a string)
        driver_id = trip_dict.get('driver_id')
        driver = None
        if driver_id:
            try:
                driver = Employee.find_by_id(driver_id)
            except Exception:
                driver = None
        if driver:
            first = driver.get('first_name', '')
            last = driver.get('last_name', '')
            trip_dict['driver_name'] = (first + " " + last).strip()
        else:
            trip_dict['driver_name'] = ''
        return trip_dict

class Expense(BaseModel):
    collection_name = 'expenses'

    @staticmethod
    def to_dict(expense_doc):
        if not expense_doc:
            return None
        expense_doc = expense_doc.copy()
        expense_doc['id'] = str(expense_doc['_id'])
        del expense_doc['_id']
        return bson_to_str(expense_doc)

    @staticmethod
    def to_dict_populated(expense_doc):
        from src.models.mongo_models import Truck
        data = Expense.to_dict(expense_doc)
        truck_id = data.get('truck_id')
        truck_number = ''
        if truck_id:
            truck = Truck.find_by_id(truck_id)
            if truck:
                truck_number = truck.get('truck_number', '')
        data['truck_number'] = truck_number
        return data

class Alert(BaseModel):
    collection_name = 'alerts'

    @staticmethod
    def to_dict(alert_doc):
        if not alert_doc:
            return None
        alert_doc = alert_doc.copy()
        alert_doc['id'] = str(alert_doc['_id'])
        del alert_doc['_id']
        return bson_to_str(alert_doc)

class User(BaseModel):
    collection_name = 'users'

    @staticmethod
    def to_dict(user_doc):
        if not user_doc:
            return None
        user_doc = user_doc.copy()
        user_doc['id'] = str(user_doc['_id'])
        del user_doc['_id']
        return bson_to_str(user_doc)

class SubTrip(BaseModel):
    collection_name = 'subtrips'

    @staticmethod
    def to_dict(subtrip_doc):
        if not subtrip_doc:
            return None
        subtrip_doc = subtrip_doc.copy()
        subtrip_doc['id'] = str(subtrip_doc['_id'])
        del subtrip_doc['_id']
        return bson_to_str(subtrip_doc)

class ClientPayment(BaseModel):
    collection_name = 'clientpayments'

    @staticmethod
    def to_dict(clientpayment_doc):
        if not clientpayment_doc:
            return None
        clientpayment_doc = clientpayment_doc.copy()
        clientpayment_doc['id'] = str(clientpayment_doc['_id'])
        del clientpayment_doc['_id']
        return bson_to_str(clientpayment_doc)