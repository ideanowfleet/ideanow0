import os
import sys
# DON'T CHANGE THIS PATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, send_from_directory, render_template
from flask_cors import CORS
from pymongo import MongoClient
from src.routes.user import user_bp
from src.routes.dashboard import dashboard_bp
from src.routes.trucks import trucks_bp
from src.routes.employees import employees_bp
from src.routes.trips import trips_bp
from src.routes.expenses import expenses_bp
from src.routes.reports import reports_bp
from src.routes.clientpayment import clientpayment_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for all routes
CORS(app)

# MongoDB configuration
app.config['MONGO_URI'] = 'mongodb://localhost:27017/fleet_management'
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client.fleet_management

# Make db available to the app
app.db = db

app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(dashboard_bp, url_prefix='/api')
app.register_blueprint(trucks_bp, url_prefix='/api')
app.register_blueprint(employees_bp, url_prefix='/api')
app.register_blueprint(trips_bp, url_prefix='/api')
app.register_blueprint(expenses_bp, url_prefix='/api')
app.register_blueprint(reports_bp, url_prefix='/api')
app.register_blueprint(clientpayment_bp, url_prefix='/api')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)