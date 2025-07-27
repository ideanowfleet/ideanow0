from flask import Blueprint, jsonify, request, make_response
from datetime import datetime, timedelta
from src.models.mongo_models import Truck, Employee, Trip, Expense, SubTrip
import csv
import io
from bson import ObjectId

reports_bp = Blueprint('reports', __name__)

def build_date_filter(field_name, start_date, end_date):
    """Helper to construct a MongoDB date filter for a given field."""
    date_filter = {}
    if start_date:
        date_filter['$gte'] = datetime.fromisoformat(start_date)
    if end_date:
        date_filter['$lt'] = datetime.fromisoformat(end_date) + timedelta(days=1)
    if date_filter:
        return {field_name: date_filter}
    return {}

def format_date_ddmmyyyy(dt):
    if isinstance(dt, datetime):
        return dt.strftime('%d/%m/%Y')
    elif isinstance(dt, str):
        try:
            return datetime.fromisoformat(dt).strftime('%d/%m/%Y')
        except Exception:
            return dt
    return ''

def export_to_csv(data, filename, columns):
    """Helper function to export data to CSV with DD/MM/YYYY date formatting."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for row in data:
        csv_row = {}
        for col in columns:
            value = row.get(col, '')
            if isinstance(value, ObjectId):
                csv_row[col] = str(value)
            elif isinstance(value, datetime):
                csv_row[col] = format_date_ddmmyyyy(value)
            elif 'date' in col and value:  # Handles date strings
                csv_row[col] = format_date_ddmmyyyy(value)
            else:
                csv_row[col] = value
        writer.writerow(csv_row)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@reports_bp.route('/reports/types', methods=['GET'])
def get_report_types():
    report_types = [
        {
            'id': 'trip_summary',
            'name': 'Trip Summary Report',
            'description': 'Comprehensive overview of all trips with performance metrics',
            'parameters': ['date_range', 'truck_id', 'driver_id', 'region']
        },
        {
            'id': 'expense_summary',
            'name': 'Expense Summary Report',
            'description': 'Detailed breakdown of expenses by category and time period',
            'parameters': ['date_range', 'truck_id', 'category', 'approval_status']
        },
        {
            'id': 'truck_performance',
            'name': 'Truck Performance Report',
            'description': 'Performance analysis for each truck including efficiency and costs',
            'parameters': ['date_range', 'truck_id', 'region']
        },
        {
            'id': 'employee_performance',
            'name': 'Employee Performance Report',
            'description': 'Driver performance metrics and statistics',
            'parameters': ['date_range', 'employee_id', 'position', 'region']
        },
        {
            'id': 'financial_summary',
            'name': 'Financial Summary Report',
            'description': 'Revenue, expenses, and profit analysis',
            'parameters': ['date_range', 'truck_id', 'region']
        }
    ]
    return jsonify({'report_types': report_types})

@reports_bp.route('/reports/trip_summary', methods=['GET'])
def trip_summary_report():
    """Generate trip summary report with working region and driver filters."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        truck_id = request.args.get('truck_id')
        driver_id = request.args.get('driver_id')
        region = request.args.get('region')
        export_format = request.args.get('format')

        filter_dict = {}
        filter_dict.update(build_date_filter('start_date', start_date, end_date))

        # --- Region filter ---
        if region:
            # Find all trucks in that region
            trucks_in_region = Truck.find_all({'region': region})
            truck_ids_in_region = [str(truck['_id']) for truck in trucks_in_region]
            if truck_id:
                # If both region and truck_id are supplied, filter by their intersection
                if truck_id in truck_ids_in_region:
                    filter_dict['truck_id'] = truck_id
                else:
                    # No trucks match both region and truck_id, so no data should be returned
                    filter_dict['truck_id'] = "__NO_MATCH__"
            else:
                filter_dict['truck_id'] = {"$in": truck_ids_in_region}
        elif truck_id:
            filter_dict['truck_id'] = truck_id

        # --- Driver filter ---
        if driver_id:
            filter_dict['driver_id'] = driver_id

        # Debug: print filter and returned trips
        print("TRIP REPORT FILTER DICT:", filter_dict)

        trips = Trip.find_all(filter_dict)
        print("TRIPS RETURNED:", [t.get('start_date') for t in trips])

        trip_data = []
        for trip in trips:
            truck = Truck.find_by_id(trip.get('truck_id')) if trip.get('truck_id') else None
            Driver = Employee.find_by_id(trip.get('driver_id')) if trip.get('driver_id') else None
            distance = float(trip.get('distance_km', 0) or 0)
            fuel_cost = float(trip.get('fuel_cost', 0) or 0)
            other_expenses = float(trip.get('other_expenses', 0) or 0)
            fuel_consumed = float(trip.get('fuel_consumed', 0) or 0)
            subtrips = SubTrip.find_all({'trip_id': str(trip.get('_id'))})
            revenue = sum(float(st.get('cost', 0) or 0) for st in subtrips)
            profit = revenue - other_expenses - fuel_cost
            fuel_efficiency = float(trip.get('mileage', 0) or 0)
            trip_info = {
                'trip_number': trip.get('trip_number'),
                'truck_number': truck.get('truck_number') if truck else 'N/A',
                'driver_name': f"{Driver.get('first_name', '')} {Driver.get('last_name', '')}".strip() if Driver else 'N/A',
                'start_date': trip.get('start_date'),
                'end_date': trip.get('end_date'),
                'distance': distance,
                'revenue': revenue,
                'fuel_consumed': fuel_consumed,
                'fuel_cost': fuel_cost,
                'fuel_efficiency': fuel_efficiency,
                'other_expenses': other_expenses,
                'profit': profit
            }
            trip_data.append(trip_info)
        total_trips = len(trip_data)
        total_distance = sum(trip['distance'] for trip in trip_data)
        total_revenue = sum(trip['revenue'] for trip in trip_data)
        total_fuel_cost = sum(trip['fuel_cost'] for trip in trip_data)
        total_other_expenses = sum(trip['other_expenses'] for trip in trip_data)
        total_profit = total_revenue - total_other_expenses - total_fuel_cost
        avg_distance = total_distance / total_trips if total_trips > 0 else 0
        avg_revenue = total_revenue / total_trips if total_trips > 0 else 0
        profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
        report_data = {
            'report_type': 'Trip Summary Report',
            'generated_at': datetime.utcnow().isoformat(),
            'summary': {
                'total_trips': total_trips,
                'average_distance': avg_distance,
                'average_revenue': avg_revenue,
                'profit_margin': profit_margin,
                'total_distance': total_distance,
                'total_fuel_cost': total_fuel_cost,
                'total_other_expenses': total_other_expenses,
                'total_profit': total_profit,
                'total_revenue': total_revenue
            },
            'trips': trip_data
        }
        if export_format == 'csv':
            # Format dates for CSV output
            for trip in trip_data:
                trip['start_date'] = format_date_ddmmyyyy(trip['start_date'])
                trip['end_date'] = format_date_ddmmyyyy(trip['end_date'])
            return export_to_csv(trip_data, 'trip_summary_report.csv', [
                'trip_number', 'truck_number', 'driver_name',
                'start_date', 'end_date', 'distance', 'revenue', 'fuel_consumed', 'fuel_cost', 'fuel_efficiency', 'other_expenses', 'profit'
            ])
        return jsonify(report_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/reports/expense_summary', methods=['GET'])
def expense_summary_report():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        truck_id = request.args.get('truck_id')
        category = request.args.get('category')
        approval_status = request.args.get('approval_status')
        export_format = request.args.get('format')

        filter_dict = {}
        filter_dict.update(build_date_filter('expense_date', start_date, end_date))
        if truck_id:
            filter_dict['truck_id'] = truck_id
        if category:
            filter_dict['category'] = category
        if approval_status:
            filter_dict['status'] = approval_status

        expenses = Expense.find_all(filter_dict)
        category_summary = {}
        total_amount = 0.0
        for expense in expenses:
            cat = expense.get('category', 'Other')
            amount = float(expense.get('amount', 0) or 0)
            if cat not in category_summary:
                category_summary[cat] = {'count': 0, 'total': 0.0}
            category_summary[cat]['count'] += 1
            category_summary[cat]['total'] += amount
            total_amount += amount
        expense_data = []
        for expense in expenses:
            truck = Truck.find_by_id(expense.get('truck_id')) if expense.get('truck_id') else None
            amount = float(expense.get('amount', 0) or 0)
            expense_info = {
                'expense_number': expense.get('expense_number'),
                'truck_number': truck.get('truck_number') if truck else 'N/A',
                'category': expense.get('category'),
                'amount': amount,
                'expense_date': expense.get('expense_date'),
                'vendor_name': expense.get('vendor_name'),
                'receipt_number': expense.get('receipt_number'),
                'location': expense.get('location'),
                'description': expense.get('description'),
                'status': expense.get('status'),
            }
            expense_data.append(expense_info)
        report_data = {
            'report_type': 'Expense Summary Report',
            'generated_at': datetime.utcnow().isoformat(),
            'summary': {
                'total_expenses': len(expenses),
                'total_amount': total_amount,
                'category_breakdown': category_summary
            },
            'expenses': expense_data
        }
        if export_format == 'csv':
            for expense in expense_data:
                expense['expense_date'] = format_date_ddmmyyyy(expense['expense_date'])
            return export_to_csv(expense_data, 'expense_summary_report.csv', [
                'expense_number', 'truck_number', 'category', 'amount', 'expense_date',
                'vendor_name', 'receipt_number', 'location', 'description', 'status'
            ])
        return jsonify(report_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/reports/truck_performance', methods=['GET'])
def truck_performance_report():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        truck_id = request.args.get('truck_id')
        region = request.args.get('region')
        export_format = request.args.get('format')

        truck_filter = {}
        if truck_id:
            truck_filter['_id'] = ObjectId(truck_id)
        if region:
            truck_filter['region'] = region
        trucks = Truck.find_all(truck_filter)

        trip_date_filter = build_date_filter('start_date', start_date, end_date).get('start_date', {})
        truck_performance = []
        for truck in trucks:
            truck_id_str = str(truck['_id'])
            trip_filter = {'truck_id': truck_id_str}
            if trip_date_filter:
                trip_filter['start_date'] = trip_date_filter
            truck_trips = Trip.find_all(trip_filter)
            truck_trip_data = []
            for trip in truck_trips:
                distance = float(trip.get('distance_km', 0) or 0)
                fuel_cost = float(trip.get('fuel_cost', 0) or 0)
                other_expenses = float(trip.get('other_expenses', 0) or 0)
                fuel_consumed = float(trip.get('fuel_consumed', 0) or 0)
                subtrips = SubTrip.find_all({'trip_id': str(trip.get('_id'))})
                revenue = sum(float(st.get('cost', 0) or 0) for st in subtrips)
                profit = revenue - other_expenses
                fuel_efficiency = float(trip.get('mileage', 0) or 0)
                truck_trip_data.append({
                    'distance': distance,
                    'revenue': revenue,
                    'fuel_cost': fuel_cost,
                    'other_expenses': other_expenses,
                    'profit': profit,
                    'fuel_consumed': fuel_consumed,
                    'fuel_efficiency': fuel_efficiency
                })
            total_trips = len(truck_trip_data)
            total_distance = sum(t['distance'] for t in truck_trip_data)
            total_revenue = sum(t['revenue'] for t in truck_trip_data)
            total_fuel_cost = sum(t['fuel_cost'] for t in truck_trip_data)
            total_other_expenses = sum(t['other_expenses'] for t in truck_trip_data)
            total_profit = total_revenue - total_other_expenses
            fuel_efficiency = (sum(t['fuel_efficiency'] for t in truck_trip_data) / total_trips) if total_trips else 0
            revenue_per_km = total_revenue / total_distance if total_distance else 0
            cost_per_km = total_other_expenses / total_distance if total_distance else 0
            profit_per_km = revenue_per_km - cost_per_km
            truck_performance.append({
                'truck_number': truck.get('truck_number'),
                'make_model': f"{truck.get('make', '')} {truck.get('model', '')}".strip(),
                'total_trips': total_trips,
                'total_distance': total_distance,
                'total_revenue': total_revenue,
                'total_fuel_cost': total_fuel_cost,
                'total_expenses': total_other_expenses,
                'fuel_efficiency': fuel_efficiency,
                'revenue_per_km': revenue_per_km,
                'cost_per_km': cost_per_km,
                'profit_per_km': profit_per_km,
                'utilization_rate': (total_trips / 30) * 100 if total_trips else 0  # Assuming 30 days period
            })
        report_data = {
            'report_type': 'Truck Performance Report',
            'generated_at': datetime.utcnow().isoformat(),
            'trucks': truck_performance
        }
        if export_format == 'csv':
            return export_to_csv(truck_performance, 'truck_performance_report.csv', [
                'truck_number', 'make_model', 'total_trips', 'total_distance', 'total_revenue',
                'total_fuel_cost', 'total_expenses', 'fuel_efficiency', 'revenue_per_km',
                'cost_per_km', 'profit_per_km', 'utilization_rate'
            ])
        return jsonify(report_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/reports/employee_performance', methods=['GET'])
def employee_performance_report():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        employee_id = request.args.get('employee_id')
        position = request.args.get('position')
        region = request.args.get('region')
        export_format = request.args.get('format')

        employee_filter = {}
        if employee_id:
            employee_filter['_id'] = ObjectId(employee_id)
        if position:
            employee_filter['position'] = position
        if region:
            employee_filter['region'] = region
        employees = Employee.find_all(employee_filter)

        trip_date_filter = build_date_filter('start_date', start_date, end_date).get('start_date', {})
        employee_performance = []
        for employee in employees:
            employee_id_str = str(employee['_id'])
            trip_filter = {'driver_id': employee_id_str}
            if trip_date_filter:
                trip_filter['start_date'] = trip_date_filter
            employee_trips = Trip.find_all(trip_filter)
            trip_data = []
            for trip in employee_trips:
                distance = float(trip.get('distance_km', 0) or 0)
                fuel_cost = float(trip.get('fuel_cost', 0) or 0)
                other_expenses = float(trip.get('other_expenses', 0) or 0)
                fuel_consumed = float(trip.get('fuel_consumed', 0) or 0)
                subtrips = SubTrip.find_all({'trip_id': str(trip.get('_id'))})
                revenue = sum(float(st.get('cost', 0) or 0) for st in subtrips)
                profit = revenue - other_expenses
                trip_data.append({
                    'distance': distance,
                    'revenue': revenue,
                    'fuel_cost': fuel_cost,
                    'other_expenses': other_expenses,
                    'profit': profit,
                    'fuel_consumed': fuel_consumed
                })
            total_trips = len(trip_data)
            total_distance = sum(t['distance'] for t in trip_data)
            total_revenue = sum(t['revenue'] for t in trip_data)
            total_profit = total_revenue - sum(t['other_expenses'] for t in trip_data)
            avg_revenue_per_trip = total_revenue / total_trips if total_trips > 0 else 0
            avg_distance_per_trip = total_distance / total_trips if total_trips > 0 else 0
            employee_performance.append({
                'employee_number': employee.get('employee_number'),
                'full_name': f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
                'position': employee.get('position'),
                'total_trips': total_trips,
                'total_distance': total_distance,
                'total_revenue': total_revenue,
                'total_profit': total_profit,
                'avg_revenue_per_trip': avg_revenue_per_trip,
                'avg_distance_per_trip': avg_distance_per_trip,
                'productivity_score': (total_trips * 10 + total_distance * 0.1) if total_trips > 0 else 0
            })
        report_data = {
            'report_type': 'Employee Performance Report',
            'generated_at': datetime.utcnow().isoformat(),
            'employees': employee_performance
        }
        if export_format == 'csv':
            return export_to_csv(employee_performance, 'employee_performance_report.csv', [
                'employee_number', 'full_name', 'position', 'total_trips', 'total_distance',
                'total_revenue', 'total_profit', 'avg_revenue_per_trip', 'avg_distance_per_trip',
                'productivity_score'
            ])
        return jsonify(report_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/reports/financial_summary', methods=['GET'])
def financial_summary_report():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        truck_id = request.args.get('truck_id')
        region = request.args.get('region')
        export_format = request.args.get('format')

        date_filter = build_date_filter('start_date', start_date, end_date).get('start_date', {})
        trip_filter = {}
        if date_filter:
            trip_filter['start_date'] = date_filter
        if truck_id:
            trip_filter['truck_id'] = truck_id
        if region:
            trip_filter['region'] = region
        expense_date_filter = build_date_filter('expense_date', start_date, end_date).get('expense_date', {})
        expense_filter = {}
        if expense_date_filter:
            expense_filter['expense_date'] = expense_date_filter
        if truck_id:
            expense_filter['truck_id'] = truck_id
        if region:
            expense_filter['region'] = region
        trips = Trip.find_all(trip_filter)
        expenses = Expense.find_all(expense_filter)
        total_revenue = 0.0
        for trip in trips:
            subtrips = SubTrip.find_all({'trip_id': str(trip.get('_id'))})
            total_revenue += sum(float(st.get('cost', 0) or 0) for st in subtrips)
        total_trip_expenses = sum(float(trip.get('other_expenses', 0) or 0) for trip in trips)
        total_other_expenses = sum(float(expense.get('amount', 0) or 0) for expense in expenses)
        total_expenses = total_trip_expenses + total_other_expenses
        total_profit = total_revenue - total_expenses
        profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
        monthly_data = {}
        for trip in trips:
            if trip.get('start_date'):
                month_key = trip['start_date'].strftime('%Y-%m')
                if month_key not in monthly_data:
                    monthly_data[month_key] = {'revenue': 0.0, 'expenses': 0.0, 'profit': 0.0}
                subtrips = SubTrip.find_all({'trip_id': str(trip.get('_id'))})
                trip_revenue = sum(float(st.get('cost', 0) or 0) for st in subtrips)
                monthly_data[month_key]['revenue'] += trip_revenue
                monthly_data[month_key]['expenses'] += float(trip.get('other_expenses', 0) or 0)
        for expense in expenses:
            if expense.get('expense_date'):
                month_key = expense['expense_date'].strftime('%Y-%m')
                if month_key not in monthly_data:
                    monthly_data[month_key] = {'revenue': 0.0, 'expenses': 0.0, 'profit': 0.0}
                monthly_data[month_key]['expenses'] += float(expense.get('amount', 0) or 0)
        for month in monthly_data:
            monthly_data[month]['profit'] = monthly_data[month]['revenue'] - monthly_data[month]['expenses']
        report_data = {
            'report_type': 'Financial Summary Report',
            'generated_at': datetime.utcnow().isoformat(),
            'summary': {
                'total_revenue': total_revenue,
                'total_expenses': total_expenses,
                'total_profit': total_profit,
                'profit_margin': profit_margin
            },
            'monthly_breakdown': monthly_data
        }
        if export_format == 'csv':
            monthly_csv = []
            for month, data in monthly_data.items():
                monthly_csv.append({
                    'month': month,
                    'revenue': data['revenue'],
                    'expenses': data['expenses'],
                    'profit': data['profit']
                })
            return export_to_csv(monthly_csv, 'financial_summary_report.csv', [
                'month', 'revenue', 'expenses', 'profit'
            ])
        return jsonify(report_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500