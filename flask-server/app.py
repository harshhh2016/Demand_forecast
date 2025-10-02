from flask import Flask, request, jsonify
from flask_cors import CORS 
import onnxruntime as ort
import numpy as np
import os
import joblib
from datetime import datetime, timedelta
import hashlib
import secrets

# Create a Flask web server instance.
app = Flask(__name__)
CORS(app) # Enable CORS for all origins


# Define a mapping for ALL 7 models and their corresponding files
MODEL_ASSET_MAPPING = {
    "steel": {
        "onnx": "steel_model.onnx",
        "scaler": "scaler_steel.joblib",
        "columns": "model_columns_steel.joblib",
    },
    "conductor": {
        "onnx": "conductor_model.onnx",
        "scaler": "scaler_conductor.joblib",
        "columns": "model_columns_conductor.joblib",
    },
    "transformers": {
        "onnx": "transformers_model.onnx",
        "scaler": "scaler_transformers.joblib",
        "columns": "model_columns_transformers.joblib",
    },
    "earthwire": {
        "onnx": "earthwire_model.onnx",
        "scaler": "scaler_earthwire.joblib",
        "columns": "model_columns_earthwire.joblib",
    },
    "foundation": {
        "onnx": "foundation_model.onnx",
        "scaler": "scaler_foundation.joblib",
        "columns": "model_columns_foundation.joblib",
    },
    "reactors": {
        "onnx": "reactors_model.onnx",
        "scaler": "scaler_reactors.joblib",
        "columns": "model_columns_reactors.joblib",
    },
    "tower": {
        "onnx": "tower_model.onnx",
        "scaler": "scaler_tower.joblib",
        "columns": "model_columns_tower.joblib",
    },
}

# Dictionary to hold the loaded models, scalers, and column names
LOADED_MODELS = {}

# Load all assets once when the app starts.
print("--- Loading All 7 Models ---")
# Resolve assets relative to this file's directory so it works regardless of CWD
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
for model_name, paths in MODEL_ASSET_MAPPING.items():
    try:
        onnx_path = os.path.join(BASE_DIR, paths["onnx"]) 
        scaler_path = os.path.join(BASE_DIR, paths["scaler"]) 
        columns_path = os.path.join(BASE_DIR, paths["columns"]) 

        session = ort.InferenceSession(onnx_path)
        scaler = joblib.load(scaler_path)
        columns = joblib.load(columns_path)
        
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name
        
        LOADED_MODELS[model_name] = {
            "session": session,
            "scaler": scaler,
            "columns": columns,
            "input_name": input_name,
            "output_name": output_name,
        }
        print(f"Successfully loaded assets for: {model_name.upper()}")

    except Exception as e:
        print(f"Error loading assets for {model_name.upper()}. Check files: {e}")

if not LOADED_MODELS:
    print("FATAL: No models were loaded successfully. Exiting.")
    exit(1)
print("--- All necessary models loaded ---")


# --- Feature Mapping and Engineering Function ---
def create_feature_vector(input_data, columns):
    """
    Creates a feature vector for prediction based on client input, 
    using the specific column list for the selected model.
    """
    feature_vector = {col: 0.0 for col in columns}

    try:
        # Numerical Features
        if "budget" in input_data:
            if 'Estimated_Cost_Million' in feature_vector:
                feature_vector['Estimated_Cost_Million'] = float(input_data["budget"]) / 1000000.0
        
        # Handle voltage if it's provided separately or can be extracted
        if "voltage" in input_data:
            if 'Voltage_kV' in feature_vector:
                feature_vector['Voltage_kV'] = float(input_data["voltage"])
        elif "towerType" in input_data:
            # Try to extract voltage from towerType if it contains numbers
            tower_type = str(input_data["towerType"])
            try:
                # Look for numbers in the tower type (e.g., "220 kV Lattice")
                import re
                voltage_match = re.search(r'(\d+)', tower_type)
                if voltage_match and 'Voltage_kV' in feature_vector:
                    feature_vector['Voltage_kV'] = float(voltage_match.group(1))
            except:
                pass  # If voltage extraction fails, just skip it
        
    except (ValueError, IndexError) as e:
        raise ValueError(f"Required numeric data malformed: {e}")
        
    # One-Hot Encoding (OHE) for categorical features with fallback key variants
    def set_ohe(possible_keys):
        for k in possible_keys:
            if k in feature_vector:
                feature_vector[k] = 1.0
                return k
        return None

    matched_keys = []

    if "location" in input_data:
        loc = str(input_data["location"]) 
        candidates = [
            f"Location_{loc}",
            f"Location_ {loc}",
            f"Location_ {loc} ",  # With trailing space
            f"Location_{loc.replace(' ', '_')}",
            f"Location_ {loc.replace(' ', '_')}",
            f"Location_ {loc.replace(' ', '_')} ",  # With trailing space
        ]
        mk = set_ohe(candidates)
        if mk: matched_keys.append(mk)
    
    if "substationType" in input_data:
        sub = str(input_data["substationType"])
        
        # Map new substation types to existing trained types for prediction
        substation_mapping = {
            "Hybrid Substation": "GIS (Gas Insulated Substation)",
            "Mobile Substation": "AIS (Air Insulated Substation)", 
            "Switching Substation": "AIS (Air Insulated Substation)",
            "Transformer Substation": "AIS (Air Insulated Substation)",
            "Converter Substation": "HVDC (High Voltage Direct Current)"
        }
        
        # Use mapped type if available, otherwise use original
        mapped_sub = substation_mapping.get(sub, sub)
        sub_norm = mapped_sub.replace(" (", "_(").replace(" ", "_")
        
        candidates = [
            f"Substation_Type_{mapped_sub}",
            f"Substation_Type_ {mapped_sub}",
            f"Substation_Type_ {mapped_sub} ",  # With trailing space
            f"Substation_Type_{sub_norm}",
            f"Substation_Type_ {sub_norm}",
            f"Substation_Type_ {sub_norm} ",  # With trailing space
        ]
        mk = set_ohe(candidates)
        if mk: matched_keys.append(mk)

    if "towerType" in input_data:
        tower = str(input_data["towerType"]) 
        candidates = [
            f"Circuit_Type_{tower}",
            f"Circuit_Type_ {tower}",
            f"Circuit_Type_ {tower} ",  # With trailing space
            f"Circuit_Type_{tower.replace(' ', '_')}",
            f"Circuit_Type_ {tower.replace(' ', '_')}",
            f"Circuit_Type_ {tower.replace(' ', '_')} ",  # With trailing space
        ]
        mk = set_ohe(candidates)
        if mk: matched_keys.append(mk)

    if "geo" in input_data:
        geo = str(input_data["geo"]) 
        candidates = [
            f"Geographical_Zone_{geo}",
            f"Geographical_Zone_ {geo}",
            f"Geographical_Zone_ {geo} ",  # With trailing space
            f"Geographical_Zone_{geo.replace(' ', '_')}",
            f"Geographical_Zone_ {geo.replace(' ', '_')}",
            f"Geographical_Zone_ {geo.replace(' ', '_')} ",  # With trailing space
        ]
        mk = set_ohe(candidates)
        if mk: matched_keys.append(mk)

    if "taxes" in input_data:
        taxes = str(input_data["taxes"]) 
        candidates = [
            f"Taxes_Applicable_{taxes}",
            f"Taxes_Applicable_ {taxes}",
            f"Taxes_Applicable_ {taxes} ",  # With trailing space
            f"Taxes_Applicable_{taxes.replace(' ', '_')}",
            f"Taxes_Applicable_ {taxes.replace(' ', '_')}",
            f"Taxes_Applicable_ {taxes.replace(' ', '_')} ",  # With trailing space
        ]
        mk = set_ohe(candidates)
        if mk: matched_keys.append(mk)
        
    final_features = [feature_vector[col] for col in columns]
    
    try:
        print("FEATURE_DEBUG | matched_keys=", matched_keys)
    except Exception:
        pass

    return final_features

@app.route("/predict_all", methods=["POST"])
def predict_all():
    """
    Handles a single prediction request and returns predictions from all models.
    """
    try:
        if not request.is_json:
            return jsonify({"error": "Request body must be JSON."}), 400

        data = request.get_json()
        input_features = data.get("input_features")
        if not input_features:
            return jsonify({"error": "Missing 'input_features' in JSON payload."}), 400

        all_predictions = {}
        
        for model_name, model_assets in LOADED_MODELS.items():
            try:
                features_ordered = create_feature_vector(input_features, model_assets["columns"])
            
                input_array = np.array(features_ordered, dtype=np.float32).reshape(1, -1)
                scaled_input = model_assets["scaler"].transform(input_array)
                
                prediction = model_assets["session"].run(
                    [model_assets["output_name"]], 
                    {model_assets["input_name"]: scaled_input}
                )
                prediction_result = float(prediction[0].flatten()[0])
                
                all_predictions[model_name] = prediction_result
                try:
                    nonzero = [i for i,v in enumerate(features_ordered) if v != 0.0]
                    print(f"PREDICT_DEBUG | model={model_name} nonzero_count={len(nonzero)}")
                except Exception:
                    pass
            
            except Exception as e:
                print(f"Error predicting for {model_name}: {e}")
                all_predictions[model_name] = "Prediction Error" # Report the error to the user

        return jsonify(all_predictions) 

    except ValueError as e:
        return jsonify({"error": f"Input data error: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route("/alert_restock", methods=["POST"])
def alert_restock():
    try:
        if not request.is_json:
            return jsonify({"error": "Request body must be JSON."}), 400
        data = request.get_json()
        # Stub: Here we would send email using SMTP or a provider
        # For now, log and return OK
        print("RESTOCK ALERT:", data)
        return jsonify({"status": "alert recorded"})
    except Exception as e:
        return jsonify({"error": f"Failed to record alert: {str(e)}"}), 500

# Material lead time defaults for ordering schedule
MATERIAL_DEFAULTS = {
    'steel': 75,
    'conductor': 90,
    'transformers': 75,
    'earthwire': 75,
    'foundation': 75,
    'reactors': 75,
    'tower': 75,
}

# --- Periodic Forecasting Database ---
import sqlite3
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'forecast.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrent access
    conn.execute('PRAGMA journal_mode=WAL;')
    # Set busy timeout to handle locks
    conn.execute('PRAGMA busy_timeout=30000;')
    return conn

def init_periodic_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Users table for authentication
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('admin', 'employee')),
            state TEXT,
            created_at TEXT NOT NULL,
            last_login TEXT
        )
    """)
    
    # Add fullname and state columns if they don't exist (for existing databases)
    try:
        cur.execute("ALTER TABLE users ADD COLUMN fullname TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cur.execute("ALTER TABLE users ADD COLUMN state TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Projects table for role-based project sharing
    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            budget TEXT NOT NULL,
            location TEXT NOT NULL,
            tower_type TEXT NOT NULL,
            substation_type TEXT NOT NULL,
            geo TEXT NOT NULL,
            taxes TEXT NOT NULL,
            created_by_user_id INTEGER NOT NULL,
            created_by_username TEXT NOT NULL,
            created_by_role TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'declined', 'deleted', 'finished', 'rejected')),
            steel_forecast REAL,
            conductor_forecast REAL,
            transformers_forecast REAL,
            earthwire_forecast REAL,
            foundation_forecast REAL,
            reactors_forecast REAL,
            tower_forecast REAL,
            created_at TEXT NOT NULL,
            approved_by INTEGER,
            approval_date TEXT,
            approval_notes TEXT,
            FOREIGN KEY(created_by_user_id) REFERENCES users(id),
            FOREIGN KEY(approved_by) REFERENCES users(id)
        )
    """)
    
    # Add approval columns if they don't exist (for existing databases)
    try:
        cur.execute("ALTER TABLE projects ADD COLUMN approved_by INTEGER")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cur.execute("ALTER TABLE projects ADD COLUMN approval_date TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cur.execute("ALTER TABLE projects ADD COLUMN approval_notes TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Fix CHECK constraint for status column (SQLite workaround)
    # Check if we need to update the constraint by testing if 'rejected' is allowed
    try:
        # Try to insert a test record with 'rejected' status using the same connection
        cur.execute("""
            INSERT INTO projects 
            (budget, location, tower_type, substation_type, geo, taxes, 
             created_by_user_id, created_by_username, created_by_role, status, created_at)
            VALUES ('test', 'test', 'test', 'test', 'test', 'test', 999999, 'test', 'admin', 'rejected', ?)
        """, (datetime.now().isoformat(),))
        # If successful, delete the test record
        cur.execute("DELETE FROM projects WHERE created_by_user_id = 999999")
        conn.commit()
    except sqlite3.IntegrityError as e:
        if "CHECK constraint failed" in str(e):
            # Need to recreate the table with updated constraint
            print("Updating database schema to support 'rejected' status...")
            
            # Rollback the failed transaction
            conn.rollback()
            
            # Create backup table
            cur.execute("""
                CREATE TABLE projects_backup AS 
                SELECT * FROM projects
            """)
            
            # Drop original table
            cur.execute("DROP TABLE projects")
            
            # Recreate with updated constraint
            cur.execute("""
                CREATE TABLE projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    budget TEXT NOT NULL,
                    location TEXT NOT NULL,
                    tower_type TEXT NOT NULL,
                    substation_type TEXT NOT NULL,
                    geo TEXT NOT NULL,
                    taxes TEXT NOT NULL,
                    created_by_user_id INTEGER NOT NULL,
                    created_by_username TEXT NOT NULL,
                    created_by_role TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'declined', 'deleted', 'finished', 'rejected')),
                    steel_forecast REAL,
                    conductor_forecast REAL,
                    transformers_forecast REAL,
                    earthwire_forecast REAL,
                    foundation_forecast REAL,
                    reactors_forecast REAL,
                    tower_forecast REAL,
                    created_at TEXT NOT NULL,
                    approved_by INTEGER,
                    approval_date TEXT,
                    approval_notes TEXT,
                    FOREIGN KEY(created_by_user_id) REFERENCES users(id),
                    FOREIGN KEY(approved_by) REFERENCES users(id)
                )
            """)
            
            # Restore data
            cur.execute("""
                INSERT INTO projects 
                SELECT * FROM projects_backup
            """)
            
            # Drop backup table
            cur.execute("DROP TABLE projects_backup")
            
            print("Database schema updated successfully!")
    except Exception as e:
        # Other error, rollback
        conn.rollback()
    
    # Project phases table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS project_phases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            phase_name TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
    """)
    
    # Forecast schedules table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS forecast_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            frequency TEXT NOT NULL, -- 'weekly', 'monthly', 'quarterly'
            is_active BOOLEAN DEFAULT 1,
            next_run TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    
    # Forecast history table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS forecast_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            forecast_date TEXT NOT NULL,
            phase_id INTEGER,
            steel_forecast REAL,
            conductor_forecast REAL,
            transformers_forecast REAL,
            earthwire_forecast REAL,
            foundation_forecast REAL,
            reactors_forecast REAL,
            tower_forecast REAL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(phase_id) REFERENCES project_phases(id)
        )
    """)
    
    # Project timeline table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS project_timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            milestone TEXT NOT NULL,
            target_date TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()

# --- User Authentication Helper Functions ---
def hash_password(password):
    """Generate a salt and hash for the password"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return password_hash, salt

def verify_password(password, password_hash, salt):
    """Verify a password against its hash and salt"""
    return hashlib.sha256((password + salt).encode()).hexdigest() == password_hash

def get_user_by_username(username):
    """Get user from database by username"""
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM users WHERE username = ?', (username,)
    ).fetchone()
    conn.close()
    return user

# --- User Authentication Endpoints ---
@app.route('/auth/signup', methods=['POST'])
def signup():
    """User signup endpoint"""
    try:
        if not request.is_json:
            return jsonify({"error": "Request body must be JSON."}), 400
        
        data = request.get_json()
        fullname = data.get('fullname', '').strip()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        role = data.get('role', 'employee').lower()
        state = data.get('state', '').strip()
        
        # Validation
        if not username or not password:
            return jsonify({"error": "Username and password are required."}), 400
        
        if len(username) < 3:
            return jsonify({"error": "Username must be at least 3 characters long."}), 400
        
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters long."}), 400
        
        if role not in ['admin', 'employee']:
            return jsonify({"error": "Role must be either 'admin' or 'employee'."}), 400
        
        if not state:
            return jsonify({"error": "State is required."}), 400
        
        # Check if user already exists
        existing_user = get_user_by_username(username)
        if existing_user:
            return jsonify({"error": "Username already exists. Please use a different username."}), 409
        
        # Hash password
        password_hash, salt = hash_password(password)
        
        # Save user to database
        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO users (fullname, username, password_hash, salt, role, state, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (fullname or username, username, password_hash, salt, role, state, datetime.now().isoformat())
            )
            conn.commit()
            
            return jsonify({
                "message": "User created successfully.",
                "fullname": fullname,
                "username": username,
                "role": role,
                "state": state
            }), 201
        
        except sqlite3.IntegrityError:
            return jsonify({"error": "Username already exists. Please use a different username."}), 409
        finally:
            conn.close()
    
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/auth/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        if not request.is_json:
            return jsonify({"error": "Request body must be JSON."}), 400
        
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Validation
        if not username or not password:
            return jsonify({"error": "Username and password are required."}), 400
        
        # Get user from database
        user = get_user_by_username(username)
        if not user:
            return jsonify({"error": "Username and password not found."}), 401
        
        # Verify password
        if not verify_password(password, user['password_hash'], user['salt']):
            return jsonify({"error": "Username and password not found."}), 401
        
        # Update last login
        conn = get_db_connection()
        conn.execute(
            'UPDATE users SET last_login = ? WHERE id = ?',
            (datetime.now().isoformat(), user['id'])
        )
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": "Login successful.",
            "user": {
                "id": user['id'],
                "fullname": user['fullname'] if user['fullname'] else user['username'],  # Fallback to username if fullname is NULL
                "username": user['username'],
                "role": user['role'],
                "state": user['state'] if user['state'] else '',  # Fallback to empty string if state is NULL
                "created_at": user['created_at'],
                "last_login": datetime.now().isoformat()
            }
        }), 200
    
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# --- Project Management API ---
@app.route('/projects', methods=['POST'])
def create_project():
    """Create a new project"""
    try:
        if not request.is_json:
            return jsonify({"error": "Request body must be JSON."}), 400
        
        data = request.get_json()
        
        # Extract project data
        budget = data.get('budget', '')
        location = data.get('location', '')
        tower_type = data.get('towerType', '')
        substation_type = data.get('substationType', '')
        geo = data.get('geo', '')
        taxes = data.get('taxes', '')
        created_by_user_id = data.get('created_by_user_id')
        created_by_username = data.get('created_by_username', '')
        created_by_role = data.get('created_by_role', '')
        
        # Validation
        if not all([budget, location, tower_type, substation_type, geo, taxes, created_by_user_id, created_by_username, created_by_role]):
            return jsonify({"error": "All project fields are required."}), 400
        
        # Set status based on role
        status = "approved" if created_by_role == "admin" else "pending"
        
        # Get forecasts from prediction API
        prediction_data = {
            'budget': budget,
            'location': location,
            'towerType': tower_type,
            'substationType': substation_type,
            'geo': geo,
            'taxes': taxes
        }
        
        # Generate forecasts using internal prediction logic
        try:
            forecasts = {}
            for model_name, model_data in LOADED_MODELS.items():
                try:
                    feature_vector = create_feature_vector(prediction_data, model_data["columns"])
                    final_features = np.array([feature_vector], dtype=np.float32)
                    scaled_features = model_data["scaler"].transform(final_features)
                    
                    prediction = model_data["session"].run(
                        [model_data["output_name"]], 
                        {model_data["input_name"]: scaled_features}
                    )[0]
                    
                    forecasts[model_name] = float(prediction[0][0]) if prediction.size > 0 else 0.0
                except Exception as model_error:
                    print(f"Error predicting {model_name}: {model_error}")
                    forecasts[model_name] = 0.0
                    
        except Exception as pred_error:
            return jsonify({"error": f"Prediction failed: {str(pred_error)}"}), 500
        
        # Save project to database
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO projects 
            (budget, location, tower_type, substation_type, geo, taxes, 
             created_by_user_id, created_by_username, created_by_role, status,
             steel_forecast, conductor_forecast, transformers_forecast, 
             earthwire_forecast, foundation_forecast, reactors_forecast, tower_forecast, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            budget, location, tower_type, substation_type, geo, taxes,
            created_by_user_id, created_by_username, created_by_role, status,
            forecasts.get('steel', 0), forecasts.get('conductor', 0), forecasts.get('transformers', 0),
            forecasts.get('earthwire', 0), forecasts.get('foundation', 0), forecasts.get('reactors', 0), 
            forecasts.get('tower', 0), datetime.now().isoformat()
        ))
        
        project_id = cur.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": "Project created successfully.",
            "project_id": project_id,
            "status": status,
            "forecasts": forecasts
        }), 201
        
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/projects/<int:user_id>', methods=['GET'])
def get_user_projects(user_id):
    """Get projects for a specific user based on their role"""
    try:
        # Get user info
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found."}), 404
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        if user['role'] == 'admin':
            # Admin sees all projects from their state
            # First get the user's state based on a project they created (if any)
            # For now, we'll get all projects and filter by state in the response
            cur.execute("""
                SELECT * FROM projects 
                ORDER BY created_at DESC
            """)
        else:
            # Employee sees only their own projects
            cur.execute("""
                SELECT * FROM projects 
                WHERE created_by_user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
        
        projects = []
        for row in cur.fetchall():
            project = {
                'id': row['id'],
                'budget': row['budget'],
                'location': row['location'],
                'towerType': row['tower_type'],
                'substationType': row['substation_type'],
                'geo': row['geo'],
                'taxes': row['taxes'],
                'createdBy': row['created_by_username'],
                'createdByRole': row['created_by_role'],
                'status': row['status'],
                'createdAt': row['created_at'],
                # Individual forecast fields for Dashboard component
                'steel_forecast': row['steel_forecast'],
                'conductor_forecast': row['conductor_forecast'],
                'transformers_forecast': row['transformers_forecast'],
                'earthwire_forecast': row['earthwire_forecast'],
                'foundation_forecast': row['foundation_forecast'],
                'reactors_forecast': row['reactors_forecast'],
                'tower_forecast': row['tower_forecast'],
                # Grouped forecasts for other components
                'allForecasts': {
                    'steel': row['steel_forecast'],
                    'conductor': row['conductor_forecast'],
                    'transformers': row['transformers_forecast'],
                    'earthwire': row['earthwire_forecast'],
                    'foundation': row['foundation_forecast'],
                    'reactors': row['reactors_forecast'],
                    'tower': row['tower_forecast']
                }
            }
            projects.append(project)
        
        conn.close()
        
        # Filter projects by state for admin users
        if user['role'] == 'admin':
            # State mapping (same as frontend)
            state_mapping = {
                "Uttar Pradesh": ["Lucknow", "Kanpur", "Meerut", "Agra", "Varanasi"],
                "Maharashtra": ["Mumbai", "Pune", "Nagpur"],
                "Karnataka": ["Bengaluru", "Mysore"],
                "Tamil Nadu": ["Chennai", "Coimbatore"],
                "West Bengal": ["Kolkata", "Siliguri"],
                "Rajasthan": ["Jaipur", "Jodhpur"],
                "Gujarat": ["Ahmedabad", "Surat"],
                "Telangana": ["Hyderabad", "Warangal"],
                "Delhi": ["Delhi"],
            }
            
            # Get admin's state (we'll need to determine this somehow)
            # For now, let's assume we can get it from their first project or set a default
            admin_state = None
            for state, cities in state_mapping.items():
                if any(project['location'] in cities for project in projects if project['createdByRole'] == 'admin' and project['createdBy'] == user['username']):
                    admin_state = state
                    break
            
            if admin_state:
                # Filter projects to only show those from the admin's state
                filtered_projects = []
                for project in projects:
                    project_state = None
                    for state, cities in state_mapping.items():
                        if project['location'] in cities:
                            project_state = state
                            break
                    
                    if project_state == admin_state:
                        filtered_projects.append(project)
                
                projects = filtered_projects
        
        return jsonify({"projects": projects}), 200
        
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/projects/<int:project_id>/status', methods=['PUT'])
def update_project_status(project_id):
    """Update project status (for admin approval/rejection)"""
    try:
        if not request.is_json:
            return jsonify({"error": "Request body must be JSON."}), 400
        
        data = request.get_json()
        new_status = data.get('status', '')
        user_id = data.get('user_id')
        
        if new_status not in ['pending', 'approved', 'declined', 'deleted', 'finished']:
            return jsonify({"error": "Invalid status."}), 400
        
        # Verify user is admin (optional - could be done with proper auth middleware)
        user = get_user_by_id(user_id) if user_id else None
        if user and user['role'] != 'admin':
            return jsonify({"error": "Only admins can update project status."}), 403
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE projects 
            SET status = ?
            WHERE id = ?
        """, (new_status, project_id))
        
        if cur.rowcount == 0:
            conn.close()
            return jsonify({"error": "Project not found."}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Project status updated successfully."}), 200
        
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

def get_user_by_id(user_id):
    """Helper function to get user by ID"""
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM users WHERE id = ?', (user_id,)
    ).fetchone()
    conn.close()
    return user

# --- Optimal Ordering Schedule ---
@app.route('/ordering/schedule', methods=['POST'])
def ordering_schedule():
    """
    Calculate optimal order dates per material.

    Request JSON formats supported:
    1) Single need-by date for many materials (default = all known materials):
       {
         "need_by_date": "YYYY-MM-DD",
         "materials": ["steel", "conductor", ...],           # optional
         "lead_time_overrides": {"steel": 80, ...}            # optional
       }

    2) Per-material need-by dates:
       {
         "need_by_dates": { "steel": "YYYY-MM-DD", ... },
         "lead_time_overrides": {"steel": 80, ...}            # optional
       }

    Lead time is resolved in this order: overrides -> DB materials table -> MATERIAL_DEFAULTS.
    Response: { "schedule": [ { material, need_by_date, lead_time_days, order_date }, ... ] }
    """
    try:
        payload = request.get_json(force=True)
        if not isinstance(payload, dict):
            return jsonify({ 'error': 'Invalid JSON payload' }), 400

        lead_time_overrides = payload.get('lead_time_overrides') or {}
        if lead_time_overrides and not isinstance(lead_time_overrides, dict):
            return jsonify({ 'error': 'lead_time_overrides must be an object' }), 400

        schedule_items = []

        # Helper to get lead time for a material (override -> default)
        def resolve_lead_time_days(material_name: str) -> int:
            name_key = str(material_name).lower()
            if name_key in lead_time_overrides:
                try:
                    lt = int(lead_time_overrides[name_key])
                    if lt > 0:
                        return lt
                except Exception:
                    pass
            # Fallback default
            return int(MATERIAL_DEFAULTS.get(name_key, 75))

        # Case 1: single need_by_date for many materials
        if 'need_by_date' in payload:
            need_by_str = str(payload['need_by_date'])
            try:
                need_by_dt = datetime.strptime(need_by_str, '%Y-%m-%d')
            except ValueError:
                return jsonify({ 'error': 'need_by_date must be YYYY-MM-DD' }), 400

            materials = payload.get('materials')
            if materials is None:
                materials = list(MATERIAL_DEFAULTS.keys())
            if not isinstance(materials, list) or not materials:
                return jsonify({ 'error': 'materials must be a non-empty list when provided' }), 400

            for m in materials:
                lt_days = resolve_lead_time_days(m)
                order_dt = need_by_dt - timedelta(days=int(lt_days))
                schedule_items.append({
                    'material': m,
                    'need_by_date': need_by_dt.strftime('%Y-%m-%d'),
                    'lead_time_days': int(lt_days),
                    'order_date': order_dt.strftime('%Y-%m-%d'),
                })

        # Case 2: per-material need_by_dates map
        elif 'need_by_dates' in payload:
            nb_map = payload.get('need_by_dates') or {}
            if not isinstance(nb_map, dict) or not nb_map:
                return jsonify({ 'error': 'need_by_dates must be a non-empty object' }), 400
            for m, date_str in nb_map.items():
                try:
                    need_by_dt = datetime.strptime(str(date_str), '%Y-%m-%d')
                except ValueError:
                    return jsonify({ 'error': f'Invalid date for {m}: must be YYYY-MM-DD' }), 400
                lt_days = resolve_lead_time_days(m)
                order_dt = need_by_dt - timedelta(days=int(lt_days))
                schedule_items.append({
                    'material': m,
                    'need_by_date': need_by_dt.strftime('%Y-%m-%d'),
                    'lead_time_days': int(lt_days),
                    'order_date': order_dt.strftime('%Y-%m-%d'),
                })

        else:
            return jsonify({ 'error': 'Provide either need_by_date or need_by_dates' }), 400

        # Sort by order_date ascending for readability
        schedule_items.sort(key=lambda x: x['order_date'])
        return jsonify({ 'schedule': schedule_items })

    except Exception as e:
        return jsonify({ 'error': str(e) }), 500

# --- Periodic Forecasting Endpoints ---
@app.route('/forecast/schedule', methods=['POST'])
def create_forecast_schedule():
    """Create a periodic forecast schedule for a project"""
    try:
        data = request.get_json(force=True)
        project_id = data.get('project_id')
        frequency = data.get('frequency', 'monthly')  # weekly, monthly, quarterly
        
        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400
        
        if frequency not in ['weekly', 'monthly', 'quarterly']:
            return jsonify({'error': 'frequency must be weekly, monthly, or quarterly'}), 400
        
        # Calculate next run date
        now = datetime.now()
        if frequency == 'weekly':
            next_run = now + timedelta(weeks=1)
        elif frequency == 'monthly':
            next_run = now + timedelta(days=30)
        else:  # quarterly
            next_run = now + timedelta(days=90)
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if schedule already exists
        cur.execute("SELECT id FROM forecast_schedules WHERE project_id = ? AND is_active = 1", (project_id,))
        if cur.fetchone():
            return jsonify({'error': 'Active schedule already exists for this project'}), 400
        
        # Create new schedule
        cur.execute("""
            INSERT INTO forecast_schedules (project_id, frequency, next_run, created_at)
            VALUES (?, ?, ?, ?)
        """, (project_id, frequency, next_run.strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d %H:%M:%S')))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': f'Periodic forecast schedule created ({frequency})',
            'next_run': next_run.strftime('%Y-%m-%d')
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/forecast/history/<project_id>', methods=['GET'])
def get_forecast_history(project_id):
    """Get forecast history for a project"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT * FROM forecast_history 
            WHERE project_id = ? 
            ORDER BY forecast_date DESC
        """, (project_id,))
        
        history = []
        for row in cur.fetchall():
            history.append({
                'id': row['id'],
                'forecast_date': row['forecast_date'],
                'phase_id': row['phase_id'],
                'forecasts': {
                    'steel': row['steel_forecast'],
                    'conductor': row['conductor_forecast'],
                    'transformers': row['transformers_forecast'],
                    'earthwire': row['earthwire_forecast'],
                    'foundation': row['foundation_forecast'],
                    'reactors': row['reactors_forecast'],
                    'tower': row['tower_forecast']
                },
                'created_at': row['created_at']
            })
        
        conn.close()
        return jsonify({'history': history})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/forecast/run_periodic', methods=['POST'])
def run_periodic_forecast():
    """Run periodic forecasts for all active schedules"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get all active schedules that are due
        today = datetime.now().strftime('%Y-%m-%d')
        cur.execute("""
            SELECT * FROM forecast_schedules 
            WHERE is_active = 1 AND next_run <= ?
        """, (today,))
        
        schedules = cur.fetchall()
        results = []
        
        for schedule in schedules:
            project_id = schedule['project_id']
            frequency = schedule['frequency']
            
            # Get project data (you'll need to implement this based on your project storage)
            # For now, we'll use a mock project data
            project_data = {
                'budget': '1000000',
                'location': 'Mumbai',
                'towerType': '220 kV',
                'substationType': 'Indoor',
                'geo': 'Urban',
                'taxes': 'Yes'
            }
            
            # Generate forecast
            try:
                features_ordered = create_feature_vector(project_data, LOADED_MODELS['steel']['columns'])
                input_array = np.array(features_ordered, dtype=np.float32).reshape(1, -1)
                
                forecasts = {}
                for model_name, model_assets in LOADED_MODELS.items():
                    scaled_input = model_assets['scaler'].transform(input_array)
                    prediction = model_assets['session'].run(
                        [model_assets['output_name']], 
                        {model_assets['input_name']: scaled_input}
                    )
                    forecasts[f'{model_name}_forecast'] = float(prediction[0].flatten()[0])
                
                # Store forecast in history
                cur.execute("""
                    INSERT INTO forecast_history 
                    (project_id, forecast_date, steel_forecast, conductor_forecast, 
                     transformers_forecast, earthwire_forecast, foundation_forecast, 
                     reactors_forecast, tower_forecast, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    project_id, today,
                    forecasts['steel_forecast'], forecasts['conductor_forecast'],
                    forecasts['transformers_forecast'], forecasts['earthwire_forecast'],
                    forecasts['foundation_forecast'], forecasts['reactors_forecast'],
                    forecasts['tower_forecast'], datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
                
                # Update next run date
                if frequency == 'weekly':
                    next_run = datetime.now() + timedelta(weeks=1)
                elif frequency == 'monthly':
                    next_run = datetime.now() + timedelta(days=30)
                else:  # quarterly
                    next_run = datetime.now() + timedelta(days=90)
                
                cur.execute("""
                    UPDATE forecast_schedules 
                    SET next_run = ? 
                    WHERE id = ?
                """, (next_run.strftime('%Y-%m-%d'), schedule['id']))
                
                results.append({
                    'project_id': project_id,
                    'status': 'success',
                    'forecasts': forecasts
                })
                
            except Exception as e:
                results.append({
                    'project_id': project_id,
                    'status': 'error',
                    'error': str(e)
                })
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'processed': len(results),
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/project/phases', methods=['POST'])
def create_project_phases():
    """Create project phases for timeline tracking"""
    try:
        data = request.get_json(force=True)
        project_id = data.get('project_id')
        phases = data.get('phases', [])
        
        if not project_id or not phases:
            return jsonify({'error': 'project_id and phases are required'}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Clear existing phases
        cur.execute("DELETE FROM project_phases WHERE project_id = ?", (project_id,))
        
        # Insert new phases
        for phase in phases:
            cur.execute("""
                INSERT INTO project_phases 
                (project_id, phase_name, start_date, end_date, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                project_id, phase['name'], phase['start_date'], 
                phase['end_date'], datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'success', 'message': 'Project phases created'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/project/phases/<project_id>', methods=['GET'])
def get_project_phases(project_id):
    """Get project phases"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT * FROM project_phases 
            WHERE project_id = ? 
            ORDER BY start_date
        """, (project_id,))
        
        phases = []
        for row in cur.fetchall():
            phases.append({
                'id': row['id'],
                'phase_name': row['phase_name'],
                'start_date': row['start_date'],
                'end_date': row['end_date'],
                'status': row['status']
            })
        
        conn.close()
        return jsonify({'phases': phases})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Project Approval Workflow Endpoints ---

@app.route('/projects/pending/<state>', methods=['GET'])
def get_pending_projects_by_state(state):
    """Get pending projects for admin approval by state"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get pending projects created by employees from the same state
        cur.execute("""
            SELECT p.*, u.state as creator_state, u.fullname as creator_fullname
            FROM projects p
            JOIN users u ON p.created_by_user_id = u.id
            WHERE p.status = 'pending' AND u.state = ?
            ORDER BY p.created_at DESC
        """, (state,))
        
        projects = []
        for row in cur.fetchall():
            projects.append({
                'id': row['id'],
                'budget': row['budget'],
                'location': row['location'],
                'tower_type': row['tower_type'],
                'substation_type': row['substation_type'],
                'geo': row['geo'],
                'taxes': row['taxes'],
                'status': row['status'],
                'created_by_user_id': row['created_by_user_id'],
                'created_by_username': row['created_by_username'],
                'created_by_role': row['created_by_role'],
                'creator_fullname': row['creator_fullname'],
                'creator_state': row['creator_state'],
                'created_at': row['created_at'],
                'steel_forecast': row['steel_forecast'],
                'conductor_forecast': row['conductor_forecast'],
                'transformers_forecast': row['transformers_forecast'],
                'earthwire_forecast': row['earthwire_forecast'],
                'foundation_forecast': row['foundation_forecast'],
                'reactors_forecast': row['reactors_forecast'],
                'tower_forecast': row['tower_forecast']
            })
        
        conn.close()
        return jsonify({'projects': projects})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/projects/all/<state>', methods=['GET'])
def get_all_projects_by_state(state):
    """Get ALL projects (approved, rejected, pending) for admin view by state"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get all projects created by users from the same state
        cur.execute("""
            SELECT p.*, u.state as creator_state, u.fullname as creator_fullname
            FROM projects p
            JOIN users u ON p.created_by_user_id = u.id
            WHERE u.state = ?
            ORDER BY p.created_at DESC
        """, (state,))
        
        projects = []
        for row in cur.fetchall():
            projects.append({
                'id': row['id'],
                'budget': row['budget'],
                'location': row['location'],
                'tower_type': row['tower_type'],
                'substation_type': row['substation_type'],
                'geo': row['geo'],
                'taxes': row['taxes'],
                'status': row['status'],
                'created_by_user_id': row['created_by_user_id'],
                'created_by_username': row['created_by_username'],
                'created_by_role': row['created_by_role'],
                'creator_fullname': row['creator_fullname'],
                'creator_state': row['creator_state'],
                'created_at': row['created_at'],
                'steel_forecast': row['steel_forecast'],
                'conductor_forecast': row['conductor_forecast'],
                'transformers_forecast': row['transformers_forecast'],
                'earthwire_forecast': row['earthwire_forecast'],
                'foundation_forecast': row['foundation_forecast'],
                'reactors_forecast': row['reactors_forecast'],
                'tower_forecast': row['tower_forecast'],
                'approved_by': row['approved_by'],
                'approved_at': row['approval_date'],
                'approval_notes': row['approval_notes'],
                'rejected_by': row['approved_by'] if row['status'] == 'rejected' else None,
                'rejected_at': row['approval_date'] if row['status'] == 'rejected' else None,
                'rejection_notes': row['approval_notes'] if row['status'] == 'rejected' else None
            })
        
        conn.close()
        return jsonify({'projects': projects})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/projects/<project_id>/approve', methods=['POST'])
def approve_project(project_id):
    """Approve a project"""
    conn = None
    try:
        data = request.get_json()
        admin_user_id = data.get('admin_user_id')
        approval_notes = data.get('approval_notes', '')
        
        if not admin_user_id:
            return jsonify({'error': 'Admin user ID is required'}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verify the admin user exists and is an admin
        cur.execute('SELECT role, state FROM users WHERE id = ?', (admin_user_id,))
        admin_user = cur.fetchone()
        
        if not admin_user:
            conn.close()
            return jsonify({'error': 'Admin user not found'}), 404
        
        if admin_user['role'] != 'admin':
            conn.close()
            return jsonify({'error': 'Only admins can approve projects'}), 403
        
        # Get project details to verify state match
        cur.execute("""
            SELECT p.*, u.state as creator_state 
            FROM projects p 
            JOIN users u ON p.created_by_user_id = u.id 
            WHERE p.id = ?
        """, (project_id,))
        
        project = cur.fetchone()
        if not project:
            conn.close()
            return jsonify({'error': 'Project not found'}), 404
        
        if project['status'] != 'pending':
            conn.close()
            return jsonify({'error': 'Project is not pending approval'}), 400
        
        # Verify admin is from the same state as project creator
        if admin_user['state'] != project['creator_state']:
            conn.close()
            return jsonify({'error': 'Admin can only approve projects from their own state'}), 403
        
        # Update project status to approved
        approval_date = datetime.now().isoformat()
        cur.execute("""
            UPDATE projects 
            SET status = 'approved', 
                approved_by = ?, 
                approval_date = ?, 
                approval_notes = ?
            WHERE id = ?
        """, (admin_user_id, approval_date, approval_notes, project_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Project approved successfully',
            'project_id': project_id,
            'approved_by': admin_user_id,
            'approval_date': approval_date
        }), 200
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/projects/<project_id>/reject', methods=['POST'])
def reject_project(project_id):
    """Reject a project"""
    conn = None
    try:
        data = request.get_json()
        admin_user_id = data.get('admin_user_id')
        rejection_notes = data.get('rejection_notes', '')
        
        if not admin_user_id:
            return jsonify({'error': 'Admin user ID is required'}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verify the admin user exists and is an admin
        cur.execute('SELECT role, state FROM users WHERE id = ?', (admin_user_id,))
        admin_user = cur.fetchone()
        
        if not admin_user:
            conn.close()
            return jsonify({'error': 'Admin user not found'}), 404
        
        if admin_user['role'] != 'admin':
            conn.close()
            return jsonify({'error': 'Only admins can reject projects'}), 403
        
        # Get project details to verify state match
        cur.execute("""
            SELECT p.*, u.state as creator_state 
            FROM projects p 
            JOIN users u ON p.created_by_user_id = u.id 
            WHERE p.id = ?
        """, (project_id,))
        
        project = cur.fetchone()
        if not project:
            conn.close()
            return jsonify({'error': 'Project not found'}), 404
        
        if project['status'] != 'pending':
            conn.close()
            return jsonify({'error': 'Project is not pending approval'}), 400
        
        # Verify admin is from the same state as project creator
        if admin_user['state'] != project['creator_state']:
            conn.close()
            return jsonify({'error': 'Admin can only reject projects from their own state'}), 403
        
        # Update project status to rejected
        rejection_date = datetime.now().isoformat()
        cur.execute("""
            UPDATE projects 
            SET status = 'rejected', 
                approved_by = ?, 
                approval_date = ?, 
                approval_notes = ?
            WHERE id = ?
        """, (admin_user_id, rejection_date, rejection_notes, project_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Project rejected successfully',
            'project_id': project_id,
            'rejected_by': admin_user_id,
            'rejection_date': rejection_date
        }), 200
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/projects/<project_id>/finish', methods=['PUT'])
def finish_project(project_id):
    """Mark a project as finished"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if project exists
        cur.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
        project = cur.fetchone()
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Update project status to finished
        cur.execute("""
            UPDATE projects 
            SET status = 'finished'
            WHERE id = ?
        """, (project_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Project marked as finished successfully',
            'project_id': project_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/projects/<project_id>/delete', methods=['DELETE'])
def delete_project(project_id):
    """Delete a project"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if project exists
        cur.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
        project = cur.fetchone()
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Delete related data first (if any)
        cur.execute('DELETE FROM project_phases WHERE project_id = ?', (project_id,))
        cur.execute('DELETE FROM forecast_schedules WHERE project_id = ?', (project_id,))
        cur.execute('DELETE FROM forecast_history WHERE project_id = ?', (project_id,))
        
        # Delete the project
        cur.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Project deleted successfully',
            'project_id': project_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    init_periodic_db()
    if LOADED_MODELS:
        app.run(debug=True, host="0.0.0.0", port=5002)
    else:
        print("Application startup failed due to model loading error.")