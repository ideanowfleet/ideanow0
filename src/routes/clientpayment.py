from flask import Blueprint, jsonify, request
from datetime import datetime
from src.models.mongo_models import ClientPayment, SubTrip, Trip
from bson import ObjectId

clientpayment_bp = Blueprint('clientpayment', __name__)

def parse_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default

def to_proper_case(s):
    if not isinstance(s, str):
        return s
    return s.capitalize()

@clientpayment_bp.route('/client-payments', methods=['GET'])
def get_client_payments():
    try:
        payments = ClientPayment.find_all({})
        payment_list = []
        for pmt in payments:
            doc = dict(pmt)
            doc['id'] = str(doc.get('_id'))
            doc.pop('_id', None)
            payment_list.append(doc)
        return jsonify({'payments': payment_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@clientpayment_bp.route('/client-payments', methods=['POST'])
def create_client_payment():
    try:
        data = request.get_json()
        required_fields = ['trip_code', 'client_name', 'cost', 'advance_payment', 'balance', 'status']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        collection = ClientPayment.get_collection()
        # Ensure only one payment per trip_code and client_name
        if collection.find_one({'trip_code': data['trip_code'], 'client_name': data['client_name']}):
            return jsonify({'error': 'Payment for this client and trip already exists'}), 400

        payment_doc = {
            'trip_code': data['trip_code'],
            'client_name': data['client_name'],
            'cost': parse_float(data['cost']),
            'advance_payment': parse_float(data['advance_payment']),
            'balance': parse_float(data['balance']),
            'status': to_proper_case(data['status']),
            'created_at': datetime.utcnow()
        }
        payment_id = ClientPayment.insert_one(payment_doc)
        payment = ClientPayment.find_by_id(payment_id)
        doc = dict(payment)
        doc['id'] = str(doc.get('_id'))
        doc.pop('_id', None)
        return jsonify({'message': 'Client payment saved', 'payment': doc}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@clientpayment_bp.route('/client-payments/<payment_id>', methods=['GET'])
def get_client_payment(payment_id):
    try:
        payment = ClientPayment.find_by_id(payment_id)
        if not payment:
            return jsonify({'error': 'Client payment not found'}), 404
        doc = dict(payment)
        doc['id'] = str(doc.get('_id'))
        doc.pop('_id', None)
        return jsonify({'payment': doc})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@clientpayment_bp.route('/client-payments/<payment_id>', methods=['PUT'])
def update_client_payment(payment_id):
    try:
        payment = ClientPayment.find_by_id(payment_id)
        if not payment:
            return jsonify({'error': 'Client payment not found'}), 404
        data = request.get_json()
        update_doc = {}
        # If status is being updated and set to 'Received', force balance to 0 only if full payment made
        if 'status' in data and data['status'].strip().lower() == 'received':
            update_doc['status'] = to_proper_case(data['status'])
            cost = parse_float(payment.get('cost', 0))
            advance_payment = parse_float(data.get('advance_payment', payment.get('advance_payment', 0)))
            balance = parse_float(data.get('balance', payment.get('balance', 0)))
            total_paid = advance_payment + balance
            # Set balance to 0 ONLY if payment covers the cost
            if total_paid >= cost:
                update_doc['balance'] = 0.0
            else:
                update_doc['balance'] = cost - advance_payment
            # Optionally update advance_payment field if present
            if 'advance_payment' in data:
                update_doc['advance_payment'] = parse_float(data['advance_payment'])
        else:
            for field in ['advance_payment', 'balance', 'status']:
                if field in data:
                    if field in ['advance_payment', 'balance']:
                        update_doc[field] = parse_float(data[field])
                    elif field == 'status':
                        update_doc[field] = to_proper_case(data[field])
        ClientPayment.update_one(payment_id, update_doc)
        updated = ClientPayment.find_by_id(payment_id)
        doc = dict(updated)
        doc['id'] = str(doc.get('_id'))
        doc.pop('_id', None)
        return jsonify({'message': 'Client payment updated', 'payment': doc})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@clientpayment_bp.route('/client-payments/<payment_id>', methods=['DELETE'])
def delete_client_payment(payment_id):
    try:
        payment = ClientPayment.find_by_id(payment_id)
        if not payment:
            return jsonify({'error': 'Client payment not found'}), 404
        ClientPayment.delete_one(payment_id)
        return jsonify({'message': 'Client payment deleted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Endpoint: Get all unique trip codes for dropdown
@clientpayment_bp.route('/trip-codes', methods=['GET'])
def get_trip_codes():
    try:
        codes = Trip.get_collection().distinct('trip_number')
        return jsonify({'trip_codes': codes})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Endpoint: Get all unique client names for a trip code
@clientpayment_bp.route('/trip-clients', methods=['GET'])
def get_trip_clients():
    try:
        trip_code = request.args.get('trip_code')
        if not trip_code:
            return jsonify({'error': 'Missing trip code'}), 400
        names = SubTrip.get_collection().distinct('client_name', {'trip_code': trip_code})
        return jsonify({'client_names': names})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Endpoint: Get all subtrips, filter by trip_code and client_name
@clientpayment_bp.route('/subtrips', methods=['GET'])
def get_all_subtrips():
    try:
        trip_code = request.args.get('trip_code')
        client_name = request.args.get('client_name')
        filter_dict = {}
        if trip_code:
            filter_dict['trip_code'] = trip_code
        if client_name:
            filter_dict['client_name'] = client_name
        subtrips = SubTrip.find_all(filter_dict)
        subtrip_list = []
        for sub in subtrips:
            doc = dict(sub)
            doc['id'] = str(doc.get('_id'))
            doc.pop('_id', None)
            subtrip_list.append(doc)
        return jsonify({'subtrips': subtrip_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500