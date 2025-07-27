from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from src.models.mongo_models import Trip, SubTrip, Truck, Employee
from bson import ObjectId

trips_bp = Blueprint('trips', __name__)

def parse_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default

def build_date_filter(field_name, start_date, end_date):
    date_filter = {}
    if start_date:
        date_filter['$gte'] = datetime.fromisoformat(start_date)
    if end_date:
        date_filter['$lt'] = datetime.fromisoformat(end_date) + timedelta(days=1)
    if date_filter:
        return {field_name: date_filter}
    return {}

def update_trip_revenue(trip_id):
    subtrips = SubTrip.find_all({'trip_id': trip_id})
    total_revenue = sum(float(sub.get('cost', 0) or 0) for sub in subtrips)
    Trip.update_one(trip_id, {'revenue': total_revenue})

# --- DRIVER FILTER ENDPOINT ---
@trips_bp.route('/drivers/filter', methods=['GET'])
def get_active_drivers():
    """Return only active drivers for trip creation/edit (case-insensitive!)."""
    try:
        drivers = Employee.get_collection().find({
            'position': {'$regex': '^driver$', '$options': 'i'},
            'status': {'$regex': '^active$', '$options': 'i'}
        })
        driver_filters = []
        for driver in drivers:
            full_name = f"{driver.get('first_name', '')} {driver.get('last_name', '')}".strip()
            driver_filters.append({'id': str(driver['_id']), 'label': full_name})
        return jsonify({'drivers': driver_filters})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@trips_bp.route('/trips', methods=['GET'])
def get_trips():
    try:
        truck_id = request.args.get('truck_id', '')
        driver_id = request.args.get('driver_id', '')
        status = request.args.get('status', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')

        filter_dict = {}
        if truck_id:
            filter_dict['truck_id'] = truck_id
        if driver_id:
            filter_dict['driver_id'] = driver_id
        if status:
            filter_dict['status'] = status

        filter_dict.update(build_date_filter('start_date', start_date, end_date))

        trips = Trip.find_all(filter_dict)
        trip_list = []
        for trip in trips:
            trip_dict = Trip.to_dict_populated(trip)
            truck = None
            try:
                truck = Truck.find_by_id(trip.get('truck_id'))
            except Exception:
                truck = None
            trip_dict['license_plate'] = truck.get('license_plate', '') if truck else ''
            trip_list.append(trip_dict)

        return jsonify({'trips': trip_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@trips_bp.route('/trips/<trip_id>', methods=['GET'])
def get_trip(trip_id):
    try:
        trip = Trip.find_by_id(trip_id)
        if trip:
            trip_dict = Trip.to_dict_populated(trip)
            truck = None
            try:
                truck = Truck.find_by_id(trip.get('truck_id'))
            except Exception:
                truck = None
            trip_dict['license_plate'] = truck.get('license_plate', '') if truck else ''
            subtrips = SubTrip.find_all({'trip_id': trip_id})
            trip_dict['subtrips'] = [SubTrip.to_dict(sub) for sub in subtrips]
            return jsonify({'trip': trip_dict})
        return jsonify({'error': 'Trip not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@trips_bp.route('/trips', methods=['POST'])
def create_trip():
    try:
        data = request.get_json()
        required_fields = ['trip_number', 'truck_id', 'driver_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        collection = Trip.get_collection()
        if collection.find_one({'trip_number': data['trip_number']}):
            return jsonify({'error': 'Trip number already exists'}), 400

        truck_id = data['truck_id']
        driver_id = data['driver_id']
        start_date = datetime.fromisoformat(data['start_date'])
        end_date = datetime.fromisoformat(data['end_date']) if data.get('end_date') else None

        # Ensure driver is Active before assignment (case-insensitive)
        driver = Employee.find_by_id(driver_id)
        if not driver or driver.get('status', '').lower() != 'active' or driver.get('position', '').lower() != 'driver':
            return jsonify({'error': 'Driver is not active or not a driver'}), 400

        # Prevent driver double-booking on any truck for overlapping dates (not cancelled)
        driver_conflict_query = {
            'driver_id': driver_id,
            'status': {'$ne': 'Cancelled'},
            '$or': [
                {'start_date': {'$lte': start_date}, 'end_date': {'$gte': start_date}},
                {'start_date': {'$lte': end_date}, 'end_date': {'$gte': end_date}},
                {'start_date': {'$gte': start_date}, 'end_date': {'$lte': end_date}}
            ]
        }
        if collection.find_one(driver_conflict_query):
            return jsonify({'error': 'Driver is already assigned to another trip during these dates'}), 400

        other_expenses = (
            parse_float(data.get('toll', 0)) +
            parse_float(data.get('rto', 0)) +
            parse_float(data.get('driver_salary', 0)) +
            parse_float(data.get('labour_charges', 0)) +
            parse_float(data.get('adblue', 0)) +
            parse_float(data.get('extra_expense', 0))
        )

        trip_doc = {
            'trip_number': data['trip_number'],
            'truck_id': truck_id,
            'driver_id': driver_id,
            'start_date': start_date,
            'end_date': end_date,
            'distance_km': parse_float(data.get('distance_km', 0)),
            'mileage': parse_float(data.get('mileage', 0)),
            'revenue': parse_float(data.get('revenue', 0)),
            'fuel_consumed': parse_float(data.get('fuel_consumed', 0)),
            'fuel_cost': parse_float(data.get('fuel_cost', 0)),
            'toll': parse_float(data.get('toll', 0)),
            'rto': parse_float(data.get('rto', 0)),
            'adblue': parse_float(data.get('adblue', 0)),
            'driver_salary': parse_float(data.get('driver_salary', 0)),
            'labour_charges': parse_float(data.get('labour_charges', 0)),
            'extra_expense': parse_float(data.get('extra_expense', 0)),
            'other_expenses': other_expenses,
            'profit': parse_float(data.get('profit', 0)),
            'status': data.get('status', 'Planned'),
            'notes': data.get('notes', ''),
        }

        trip_id = Trip.insert_one(trip_doc)
        trip = Trip.find_by_id(trip_id)
        truck = Truck.find_by_id(trip.get('truck_id')) if trip.get('truck_id') else None
        trip_dict = Trip.to_dict_populated(trip)
        trip_dict['license_plate'] = truck.get('license_plate', '') if truck else ''
        return jsonify({
            'message': 'Trip created successfully',
            'trip': trip_dict
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@trips_bp.route('/trips/<trip_id>', methods=['PUT'])
def update_trip(trip_id):
    try:
        trip = Trip.find_by_id(trip_id)
        if not trip:
            return jsonify({'error': 'Trip not found'}), 404

        data = request.get_json()
        collection = Trip.get_collection()

        if 'trip_number' in data and data['trip_number'] != trip.get('trip_number'):
            if collection.find_one({'trip_number': data['trip_number'], '_id': {'$ne': ObjectId(trip_id)}}):
                return jsonify({'error': 'Trip number already exists'}), 400

        truck_id = data.get('truck_id', trip.get('truck_id'))
        driver_id = data.get('driver_id', trip.get('driver_id'))
        start_date = datetime.fromisoformat(data.get('start_date')) if data.get('start_date') else trip.get('start_date')
        end_date = datetime.fromisoformat(data.get('end_date')) if data.get('end_date') else trip.get('end_date')

        # Ensure driver is Active before assignment (case-insensitive)
        driver = Employee.find_by_id(driver_id)
        if not driver or driver.get('status', '').lower() != 'active' or driver.get('position', '').lower() != 'driver':
            return jsonify({'error': 'Driver is not active or not a driver'}), 400

        # Prevent driver double-booking on any truck for overlapping dates (not cancelled, not this trip)
        driver_conflict_query = {
            'driver_id': driver_id,
            'status': {'$ne': 'Cancelled'},
            '_id': {'$ne': ObjectId(trip_id)},
            '$or': [
                {'start_date': {'$lte': start_date}, 'end_date': {'$gte': start_date}},
                {'start_date': {'$lte': end_date}, 'end_date': {'$gte': end_date}},
                {'start_date': {'$gte': start_date}, 'end_date': {'$lte': end_date}}
            ]
        }
        if collection.find_one(driver_conflict_query):
            return jsonify({'error': 'Driver is already assigned to another trip during these dates'}), 400

        updatable_fields = [
            'trip_number', 'truck_id', 'driver_id', 'distance_km', 'mileage', 'revenue', 'fuel_consumed', 'fuel_cost',
            'toll', 'rto', 'adblue', 'driver_salary', 'labour_charges', 'extra_expense',
            'profit', 'status', 'notes'
        ]
        update_doc = {}
        for field in updatable_fields:
            if field in data:
                if field in [
                    'distance_km', 'mileage', 'revenue', 'fuel_consumed', 'fuel_cost',
                    'toll', 'rto', 'adblue', 'driver_salary', 'labour_charges', 'extra_expense', 'profit'
                ]:
                    update_doc[field] = parse_float(data[field], 0)
                else:
                    update_doc[field] = data[field]

        if 'start_date' in data and data['start_date']:
            update_doc['start_date'] = datetime.fromisoformat(data['start_date'])
        if 'end_date' in data and data['end_date']:
            update_doc['end_date'] = datetime.fromisoformat(data['end_date'])

        update_doc['other_expenses'] = (
            parse_float(data.get('toll', trip.get('toll', 0))) +
            parse_float(data.get('rto', trip.get('rto', 0))) +
            parse_float(data.get('driver_salary', trip.get('driver_salary', 0))) +
            parse_float(data.get('labour_charges', trip.get('labour_charges', 0))) +
            parse_float(data.get('adblue', trip.get('adblue', 0))) +
            parse_float(data.get('extra_expense', trip.get('extra_expense', 0)))
        )

        Trip.update_one(trip_id, update_doc)
        updated_trip = Trip.find_by_id(trip_id)
        truck = Truck.find_by_id(updated_trip.get('truck_id')) if updated_trip.get('truck_id') else None
        trip_dict = Trip.to_dict_populated(updated_trip)
        trip_dict['license_plate'] = truck.get('license_plate', '') if truck else ''
        return jsonify({
            'message': 'Trip updated successfully',
            'trip': trip_dict
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@trips_bp.route('/trips/<trip_id>', methods=['DELETE'])
def delete_trip(trip_id):
    try:
        trip = Trip.find_by_id(trip_id)
        if not trip:
            return jsonify({'error': 'Trip not found'}), 404

        Trip.update_one(trip_id, {'status': 'Cancelled'})
        return jsonify({'message': 'Trip cancelled successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---- SUB TRIP ENDPOINTS ----

@trips_bp.route('/trips/<trip_id>/subtrips', methods=['GET'])
def get_subtrips(trip_id):
    try:
        subtrips = SubTrip.find_all({'trip_id': trip_id})
        subtrip_list = [SubTrip.to_dict(sub) for sub in subtrips]
        return jsonify({'subtrips': subtrip_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@trips_bp.route('/trips/<trip_id>/subtrips', methods=['POST'])
def create_subtrip(trip_id):
    try:
        data = request.get_json()
        required_fields = ['date', 'end_date', 'origin', 'destination', 'client_name', 'cargo_weight', 'cost']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        date_val = datetime.fromisoformat(data['date'])
        end_date_val = datetime.fromisoformat(data['end_date'])
        if date_val > end_date_val:
            return jsonify({'error': 'Date cannot be after End Date'}), 400     

        trip = Trip.find_by_id(trip_id)
        if not trip:
            return jsonify({'error': 'Trip not found'}), 404

        subtrip_doc = {
            'trip_id': trip_id,
            'trip_code': trip.get('trip_number'),
            'date': date_val,
            'end_date': end_date_val,
            'origin': data['origin'],
            'destination': data['destination'],
            'client_name': data['client_name'],
            'cargo_weight': parse_float(data.get('cargo_weight', 0)),
            'cost': parse_float(data.get('cost', 0))
        }
        subtrip_id = SubTrip.insert_one(subtrip_doc)
        update_trip_revenue(trip_id)
        subtrip = SubTrip.find_by_id(subtrip_id)
        return jsonify({'message': 'Sub Trip added', 'subtrip': SubTrip.to_dict(subtrip)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@trips_bp.route('/trips/<trip_id>/subtrips/<subtrip_id>', methods=['PUT'])
def update_subtrip(trip_id, subtrip_id):
    try:
        subtrip = SubTrip.find_by_id(subtrip_id)
        if not subtrip or subtrip.get('trip_id') != trip_id:
            return jsonify({'error': 'Sub Trip not found'}), 404

        data = request.get_json()
        updatable_fields = ['date', 'end_date', 'origin', 'destination', 'client_name', 'cargo_weight', 'cost']
        update_doc = {}
        for field in updatable_fields:
            if field in data:
                if field in ['cargo_weight', 'cost']:
                    parsed = parse_float(data[field], 0)
                    if parsed < 0:
                        return jsonify({'error': f'{field.replace("_", " ").title()} must be ≥ 0'}), 400
                    update_doc[field] = parsed
                elif field in ['date', 'end_date']:
                    update_doc[field] = datetime.fromisoformat(data[field])
                else:
                    update_doc[field] = data[field]
        if 'date' in update_doc and 'end_date' in update_doc:
            if update_doc['date'] > update_doc['end_date']:
                return jsonify({'error': 'Date cannot be after End Date'}), 400

        SubTrip.update_one(subtrip_id, update_doc)
        update_trip_revenue(trip_id)
        updated = SubTrip.find_by_id(subtrip_id)
        return jsonify({'message': 'Sub Trip updated', 'subtrip': SubTrip.to_dict(updated)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@trips_bp.route('/trips/<trip_id>/subtrips/<subtrip_id>', methods=['DELETE'])
def delete_subtrip(trip_id, subtrip_id):
    try:
        subtrip = SubTrip.find_by_id(subtrip_id)
        if not subtrip or subtrip.get('trip_id') != trip_id:
            return jsonify({'error': 'Sub Trip not found'}), 404
        SubTrip.delete_one(subtrip_id)
        update_trip_revenue(trip_id)
        return jsonify({'message': 'Sub Trip deleted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500