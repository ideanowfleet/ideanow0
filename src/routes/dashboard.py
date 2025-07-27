from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from src.models.mongo_models import Truck, Employee, Trip, Expense, Alert
from dateutil.parser import parse as dateparse
from bson import ObjectId

dashboard_bp = Blueprint('dashboard', __name__)

def safe_float(val):
    try:
        if val is None or val == "":
            return 0.0
        return float(val)
    except Exception:
        return 0.0

def remove_inactive_employee_alerts():
    inactive_employees = Employee.find_all({'status': 'Inactive'})
    alert_collection = Alert.get_collection()
    for emp in inactive_employees:
        alert_collection.update_many(
            {'employee_id': emp['_id'], 'status': 'Active'},
            {'$set': {'status': 'Inactive'}}
        )

def remove_inactive_truck_alerts():
    inactive_trucks = Truck.find_all({'status': 'Inactive'})
    alert_collection = Alert.get_collection()
    for truck in inactive_trucks:
        alert_collection.update_many(
            {'truck_id': truck['_id'], 'status': 'Active'},
            {'$set': {'status': 'Inactive'}}
        )

def check_and_create_license_expiry_alerts():
    soon = datetime.utcnow() + timedelta(days=30)
    now = datetime.utcnow()
    employees = Employee.find_all({'status': 'Active'})
    alert_collection = Alert.get_collection()
    for emp in employees:
        expiry_date = emp.get('license_expiry')
        if expiry_date and not isinstance(expiry_date, datetime):
            try:
                expiry_date = dateparse(expiry_date)
            except Exception:
                expiry_date = None

        existing = alert_collection.find_one({
            'employee_id': emp['_id'],
            'type': 'license_expiry',
            'status': 'Active'
        })

        if not expiry_date:
            if existing:
                alert_collection.update_one(
                    {'_id': existing['_id']},
                    {'$set': {'status': 'Inactive'}}
                )
            continue

        # Remove old alert if present and expired
        if expiry_date < now:
            if existing:
                alert_collection.update_one(
                    {'_id': existing['_id']},
                    {'$set': {'status': 'Inactive'}}
                )
            expired_existing = alert_collection.find_one({
                'employee_id': emp['_id'],
                'type': 'license_expired',
                'status': 'Active'
            })
            if not expired_existing:
                alert_collection.insert_one({
                    'employee_id': emp['_id'],
                    'employee_number': emp.get('employee_number'),
                    'type': 'license_expired',
                    'severity': 'danger',
                    'title': f"License expired for {emp.get('first_name', '')} {emp.get('last_name', '')}",
                    'message': f"License for {emp.get('first_name', '')} {emp.get('last_name', '')} expired on {expiry_date.strftime('%d/%m/%Y')}.",
                    'status': 'Active',
                    'alert_date': expiry_date
                })
        elif expiry_date <= soon:
            alert_collection.update_many({
                'employee_id': emp['_id'],
                'type': 'license_expired',
                'status': 'Active'
            }, {'$set': {'status': 'Inactive'}})
            if not existing:
                alert_collection.insert_one({
                    'employee_id': emp['_id'],
                    'employee_number': emp.get('employee_number'),
                    'type': 'license_expiry',
                    'severity': 'warning',
                    'title': f"License expiring soon for {emp.get('first_name', '')} {emp.get('last_name', '')}",
                    'message': f"License for {emp.get('first_name', '')} {emp.get('last_name', '')} expires on {expiry_date.strftime('%d/%m/%Y')}. Please renew.",
                    'status': 'Active',
                    'alert_date': expiry_date
                })
        else:
            if existing:
                alert_collection.update_one(
                    {'_id': existing['_id']},
                    {'$set': {'status': 'Inactive'}}
                )
            alert_collection.update_many({
                'employee_id': emp['_id'],
                'type': 'license_expired',
                'status': 'Active'
            }, {'$set': {'status': 'Inactive'}})

def check_and_create_insurance_expiry_alerts():
    soon = datetime.utcnow() + timedelta(days=30)
    now = datetime.utcnow()
    trucks = Truck.find_all({'status': 'Active'})
    alert_collection = Alert.get_collection()
    for truck in trucks:
        expiry_date = truck.get('insurance_expiry')
        if expiry_date and not isinstance(expiry_date, datetime):
            try:
                expiry_date = dateparse(expiry_date)
            except Exception:
                expiry_date = None

        existing = alert_collection.find_one({
            'truck_id': truck['_id'],
            'type': 'insurance_expiry',
            'status': 'Active'
        })

        if not expiry_date:
            if existing:
                alert_collection.update_one(
                    {'_id': existing['_id']},
                    {'$set': {'status': 'Inactive'}}
                )
            continue

        if expiry_date < now:
            if existing:
                alert_collection.update_one(
                    {'_id': existing['_id']},
                    {'$set': {'status': 'Inactive'}}
                )
            expired_existing = alert_collection.find_one({
                'truck_id': truck['_id'],
                'type': 'insurance_expired',
                'status': 'Active'
            })
            if not expired_existing:
                alert_collection.insert_one({
                    'truck_id': truck['_id'],
                    'truck_number': truck.get('truck_number'),
                    'type': 'insurance_expired',
                    'severity': 'danger',
                    'title': f"Insurance expired for {truck.get('truck_number', '')}",
                    'message': f"Insurance for {truck.get('truck_number', '')} expired on {expiry_date.strftime('%d/%m/%Y')}.",
                    'status': 'Active',
                    'alert_date': expiry_date
                })
        elif expiry_date <= soon:
            alert_collection.update_many({
                'truck_id': truck['_id'],
                'type': 'insurance_expired',
                'status': 'Active'
            }, {'$set': {'status': 'Inactive'}})
            if not existing:
                alert_collection.insert_one({
                    'truck_id': truck['_id'],
                    'truck_number': truck.get('truck_number'),
                    'type': 'insurance_expiry',
                    'severity': 'warning',
                    'title': f"Insurance expiring soon for {truck.get('truck_number', '')}",
                    'message': f"Insurance for {truck.get('truck_number', '')} expires on {expiry_date.strftime('%d/%m/%Y')}. Please renew.",
                    'status': 'Active',
                    'alert_date': expiry_date
                })
        else:
            if existing:
                alert_collection.update_one(
                    {'_id': existing['_id']},
                    {'$set': {'status': 'Inactive'}}
                )
            alert_collection.update_many({
                'truck_id': truck['_id'],
                'type': 'insurance_expired',
                'status': 'Active'
            }, {'$set': {'status': 'Inactive'}})

def check_and_create_fc_expiry_alerts():
    soon = datetime.utcnow() + timedelta(days=30)
    now = datetime.utcnow()
    trucks = Truck.find_all({'status': 'Active'})
    alert_collection = Alert.get_collection()
    for truck in trucks:
        expiry_date = truck.get('fc_expiry')
        if expiry_date and not isinstance(expiry_date, datetime):
            try:
                expiry_date = dateparse(expiry_date)
            except Exception:
                expiry_date = None

        existing = alert_collection.find_one({
            'truck_id': truck['_id'],
            'type': 'fc_expiry',
            'status': 'Active'
        })

        if not expiry_date:
            if existing:
                alert_collection.update_one(
                    {'_id': existing['_id']},
                    {'$set': {'status': 'Inactive'}}
                )
            continue

        if expiry_date < now:
            if existing:
                alert_collection.update_one(
                    {'_id': existing['_id']},
                    {'$set': {'status': 'Inactive'}}
                )
            expired_existing = alert_collection.find_one({
                'truck_id': truck['_id'],
                'type': 'fc_expired',
                'status': 'Active'
            })
            if not expired_existing:
                alert_collection.insert_one({
                    'truck_id': truck['_id'],
                    'truck_number': truck.get('truck_number'),
                    'type': 'fc_expired',
                    'severity': 'danger',
                    'title': f"FC expired for {truck.get('truck_number', '')}",
                    'message': f"Fitness Certificate for {truck.get('truck_number', '')} expired on {expiry_date.strftime('%d/%m/%Y')}.",
                    'status': 'Active',
                    'alert_date': expiry_date
                })
        elif expiry_date <= soon:
            alert_collection.update_many({
                'truck_id': truck['_id'],
                'type': 'fc_expired',
                'status': 'Active'
            }, {'$set': {'status': 'Inactive'}})
            if not existing:
                alert_collection.insert_one({
                    'truck_id': truck['_id'],
                    'truck_number': truck.get('truck_number'),
                    'type': 'fc_expiry',
                    'severity': 'warning',
                    'title': f"FC expiring soon for {truck.get('truck_number', '')}",
                    'message': f"Fitness Certificate for {truck.get('truck_number', '')} expires on {expiry_date.strftime('%d/%m/%Y')}. Please renew.",
                    'status': 'Active',
                    'alert_date': expiry_date
                })
        else:
            if existing:
                alert_collection.update_one(
                    {'_id': existing['_id']},
                    {'$set': {'status': 'Inactive'}}
                )
            alert_collection.update_many({
                'truck_id': truck['_id'],
                'type': 'fc_expired',
                'status': 'Active'
            }, {'$set': {'status': 'Inactive'}})

def check_and_create_permit_expiry_alerts():
    soon = datetime.utcnow() + timedelta(days=30)
    now = datetime.utcnow()
    trucks = Truck.find_all({'status': 'Active'})
    alert_collection = Alert.get_collection()
    for truck in trucks:
        expiry_date = truck.get('permit_expiry')
        if expiry_date and not isinstance(expiry_date, datetime):
            try:
                expiry_date = dateparse(expiry_date)
            except Exception:
                expiry_date = None

        existing = alert_collection.find_one({
            'truck_id': truck['_id'],
            'type': 'permit_expiry',
            'status': 'Active'
        })

        if not expiry_date:
            if existing:
                alert_collection.update_one(
                    {'_id': existing['_id']},
                    {'$set': {'status': 'Inactive'}}
                )
            continue

        if expiry_date < now:
            if existing:
                alert_collection.update_one(
                    {'_id': existing['_id']},
                    {'$set': {'status': 'Inactive'}}
                )
            expired_existing = alert_collection.find_one({
                'truck_id': truck['_id'],
                'type': 'permit_expired',
                'status': 'Active'
            })
            if not expired_existing:
                alert_collection.insert_one({
                    'truck_id': truck['_id'],
                    'truck_number': truck.get('truck_number'),
                    'type': 'permit_expired',
                    'severity': 'danger',
                    'title': f"Permit expired for {truck.get('truck_number', '')}",
                    'message': f"Permit for {truck.get('truck_number', '')} expired on {expiry_date.strftime('%d/%m/%Y')}.",
                    'status': 'Active',
                    'alert_date': expiry_date
                })
        elif expiry_date <= soon:
            alert_collection.update_many({
                'truck_id': truck['_id'],
                'type': 'permit_expired',
                'status': 'Active'
            }, {'$set': {'status': 'Inactive'}})
            if not existing:
                alert_collection.insert_one({
                    'truck_id': truck['_id'],
                    'truck_number': truck.get('truck_number'),
                    'type': 'permit_expiry',
                    'severity': 'warning',
                    'title': f"Permit expiring soon for {truck.get('truck_number', '')}",
                    'message': f"Permit for {truck.get('truck_number', '')} expires on {expiry_date.strftime('%d/%m/%Y')}. Please renew.",
                    'status': 'Active',
                    'alert_date': expiry_date
                })
        else:
            if existing:
                alert_collection.update_one(
                    {'_id': existing['_id']},
                    {'$set': {'status': 'Inactive'}}
                )
            alert_collection.update_many({
                'truck_id': truck['_id'],
                'type': 'permit_expired',
                'status': 'Active'
            }, {'$set': {'status': 'Inactive'}})

@dashboard_bp.route('/dashboard/filters', methods=['GET'])
def get_filters():
    try:
        trucks = Truck.find_all({'status': 'Active'})
        truck_filters = [{'id': str(truck['_id']), 'label': truck['truck_number']} for truck in trucks]
        drivers = Employee.find_all({'position': 'Driver', 'status': 'Active'})
        driver_filters = []
        for driver in drivers:
            full_name = f"{driver.get('first_name', '')} {driver.get('last_name', '')}".strip()
            driver_filters.append({'id': str(driver['_id']), 'label': full_name})
        truck_collection = Truck.get_collection()
        regions = truck_collection.distinct('region', {'region': {'$ne': None, '$exists': True}})
        region_filters = [{'id': region, 'label': region} for region in regions if region]
        return jsonify({
            'filters': {
                'trucks': truck_filters,
                'drivers': driver_filters,
                'regions': region_filters
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/dashboard/alerts', methods=['GET'])
def get_alerts():
    try:
        remove_inactive_employee_alerts()
        remove_inactive_truck_alerts()
        check_and_create_license_expiry_alerts()
        check_and_create_insurance_expiry_alerts()
        check_and_create_fc_expiry_alerts()
        check_and_create_permit_expiry_alerts()
        alert_collection = Alert.get_collection()
        # Get active trucks and employees for filtering
        active_truck_ids = set(truck['_id'] for truck in Truck.find_all({'status': 'Active'}))
        active_employee_ids = set(emp['_id'] for emp in Employee.find_all({'status': 'Active'}))
        alerts = list(alert_collection.find({'status': 'Active'}).sort('alert_date', 1).limit(100))
        alert_data = []
        for alert in alerts:
            # Filter out alerts for inactive trucks/employees
            if (
                ('truck_id' in alert and alert['truck_id'] not in active_truck_ids)
                or ('employee_id' in alert and alert['employee_id'] not in active_employee_ids)
            ):
                continue
            alert_dict = Alert.to_dict(alert)
            alert_date_val = alert_dict.get('alert_date')
            if alert_date_val:
                if isinstance(alert_date_val, datetime):
                    alert_dict['alert_date'] = alert_date_val.strftime('%d/%m/%Y')
                else:
                    try:
                        alert_dict['alert_date'] = dateparse(str(alert_date_val)).strftime('%d/%m/%Y')
                    except Exception:
                        alert_dict['alert_date'] = str(alert_date_val)
            alert_data.append(alert_dict)
        return jsonify({
            'alerts': alert_data[:10]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/dashboard/analytics', methods=['GET'])
def get_analytics():
    try:
        days = int(request.args.get('days', 30))
        truck_id = request.args.get('truck_id', '')
        driver_id = request.args.get('driver_id', '')
        region = request.args.get('region', '')

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        trip_filter = { 'start_date': {'$gte': start_date, '$lte': end_date} }
        if truck_id:
            trip_filter['truck_id'] = ObjectId(truck_id) if ObjectId.is_valid(truck_id) else truck_id
        if driver_id:
            trip_filter['driver_id'] = ObjectId(driver_id) if ObjectId.is_valid(driver_id) else driver_id

        trips = Trip.find_all(trip_filter)

        # Parse start_date to datetime if needed
        for trip in trips:
            if 'start_date' in trip and not isinstance(trip['start_date'], datetime):
                try:
                    trip['start_date'] = dateparse(trip['start_date'])
                except Exception:
                    trip['start_date'] = None

        # Only consider completed trips for analytics!
        completed_trips = [trip for trip in trips if trip.get('status') == "Completed"]

        # If region filter is provided, filter completed_trips by region (if trips have region field)
        if region:
            completed_trips = [trip for trip in completed_trips if trip.get('region') == region]

        total_trips = len(completed_trips)
        total_distance = sum(safe_float(trip.get('distance_km')) for trip in completed_trips)
        total_revenue = sum(safe_float(trip.get('revenue')) for trip in completed_trips)
        total_fuel_cost = sum(safe_float(trip.get('fuel_cost')) for trip in completed_trips)
        total_fuel_consumed = sum(safe_float(trip.get('fuel_consumed')) for trip in completed_trips)
        total_other_expenses = sum(safe_float(trip.get('other_expenses')) for trip in completed_trips)
        total_profit = total_revenue - total_fuel_cost - total_other_expenses
        avg_fuel_efficiency = total_distance / total_fuel_consumed if total_fuel_consumed > 0 else 0

        profit_trends = []
        for i in reversed(range(days)):
            day = start_date + timedelta(days=i)
            next_day = day + timedelta(days=1)
            day_trips = [trip for trip in completed_trips if trip.get('start_date') and day <= trip['start_date'] < next_day]
            day_revenue = sum(safe_float(trip.get('revenue')) for trip in day_trips)
            day_fuel_cost = sum(safe_float(trip.get('fuel_cost')) for trip in day_trips)
            day_other_expenses = sum(safe_float(trip.get('other_expenses')) for trip in day_trips)
            day_profit = day_revenue - day_fuel_cost - day_other_expenses
            day_expenses = day_fuel_cost + day_other_expenses
            profit_trends.append({
                'date': day.strftime('%Y-%m-%d'),
                'profit': day_profit,
                'revenue': day_revenue,
                'expenses': day_expenses
            })

        truck_collection = Truck.get_collection()
        trucks = list(truck_collection.find({'status': 'Active'}))
        fuel_usage = []
        for truck in trucks:
            truck_trips = [trip for trip in completed_trips if str(trip.get('truck_id')) == str(truck['_id'])]
            truck_fuel = sum(safe_float(trip.get('fuel_consumed')) for trip in truck_trips)
            fuel_usage.append({
                'truck_number': truck.get('truck_number', 'Unknown'),
                'fuel_consumed': truck_fuel
            })

        fuel_efficiency = []
        for i in reversed(range(days)):
            day = start_date + timedelta(days=i)
            next_day = day + timedelta(days=1)
            day_trips = [trip for trip in completed_trips if trip.get('start_date') and day <= trip['start_date'] < next_day]
            day_distance = sum(safe_float(trip.get('distance_km')) for trip in day_trips)
            day_fuel = sum(safe_float(trip.get('fuel_consumed')) for trip in day_trips)
            efficiency = day_distance / day_fuel if day_fuel > 0 else 0
            fuel_efficiency.append({
                'date': day.strftime('%Y-%m-%d'),
                'efficiency': efficiency
            })

        truck_stats = []
        for truck in trucks:
            truck_trips = [trip for trip in completed_trips if str(trip.get('truck_id')) == str(truck['_id'])]
            truck_revenue = sum(safe_float(trip.get('revenue')) for trip in truck_trips)
            truck_fuel_cost = sum(safe_float(trip.get('fuel_cost')) for trip in truck_trips)
            truck_other_expenses = sum(safe_float(trip.get('other_expenses')) for trip in truck_trips)
            truck_profit = truck_revenue - truck_fuel_cost - truck_other_expenses
            truck_distance = sum(safe_float(trip.get('distance_km')) for trip in truck_trips)
            trips_count = len(truck_trips)
            avg_profit_per_trip = truck_profit / trips_count if trips_count > 0 else 0
            truck_stats.append({
                'truck_number': truck.get('truck_number', 'Unknown'),
                'trips': trips_count,
                'revenue': truck_revenue,
                'profit': truck_profit,
                'distance': truck_distance,
                'avg_profit_per_trip': avg_profit_per_trip
            })
        truck_stats = sorted(truck_stats, key=lambda x: x['profit'], reverse=True)[:5]

        return jsonify({
            "analytics": {
                "summary": {
                    "total_trips": total_trips,
                    "total_revenue": total_revenue,
                    "total_distance": total_distance,
                    "avg_fuel_efficiency": round(avg_fuel_efficiency, 2)
                },
                "profit_trends": profit_trends,
                "fuel_usage": fuel_usage,
                "fuel_efficiency": fuel_efficiency,
                "high_performing_trucks": truck_stats
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500