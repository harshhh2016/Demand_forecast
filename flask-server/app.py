from flask import Flask, request, jsonify
from flask_cors import CORS 
import onnxruntime as ort
import numpy as np
import os
import joblib
from datetime import datetime, timedelta
import hashlib
import secrets
import sqlite3
import threading
import time

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

# --- Dynamic threshold helpers (per project/material) ---
def compute_project_threshold(cur, material_id: int, project_id: int, lookback_days: int = 30, safety_buffer_ratio: float = 0.10) -> float:
    """Compute dynamic threshold = avgDaily(on days with entries) * (leadDays + 3) * (1 + buffer)."""
    if not project_id:
        return 0.0

    try:
        # Average of per-day totals over days that actually have usage entries
        cur.execute(
            """
                SELECT AVG(daily_used) FROM (
                    SELECT DATE(usage_date) as usage_day, SUM(CASE WHEN quantity_used > 0 THEN quantity_used ELSE 0 END) as daily_used
                    FROM material_usage 
                    WHERE material_id = ? AND project_id = ?
                    GROUP BY DATE(usage_date)
                )
            """,
            (material_id, project_id)
        )
        avg_daily = float(cur.fetchone()[0] or 0)

        # Resolve lead time days from defaults
        # Map material_id -> material name to look up defaults by name key
        cur.execute("SELECT name FROM materials WHERE id = ?", (material_id,))
        name_row = cur.fetchone()
        material_name = str(name_row[0]).lower() if name_row and name_row[0] else ''
        lead_days = int(MATERIAL_DEFAULTS.get(material_name, 90))

        # Add 3-day safety in lead time as discussed, then multiply by 1 + buffer
        effective_days = max(lead_days + 3, 0)
        threshold = avg_daily * float(effective_days)
        threshold *= (1.0 + float(safety_buffer_ratio))
        return float(threshold)
    except Exception:
        return 0.0

def compute_project_avg_daily(cur, material_id: int, project_id: int, lookback_days: int = 30) -> float:
    """Compute average usage per entry (not per day): total_used / number_of_entries over full history."""
    try:
        if not project_id:
            return 0.0
        cur.execute(
            """
                SELECT COALESCE(SUM(CASE WHEN quantity_used > 0 THEN quantity_used ELSE 0 END), 0),
                       COALESCE(COUNT(CASE WHEN quantity_used > 0 THEN 1 END), 0)
                FROM material_usage
                WHERE material_id = ? AND project_id = ?
            """,
            (material_id, project_id)
        )
        total_used, num_entries = cur.fetchone() or (0, 0)
        total_used = float(total_used or 0)
        num_entries = int(num_entries or 0)
        return (total_used / num_entries) if num_entries > 0 else 0.0
    except Exception:
        return 0.0

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
            admin_level TEXT, -- 'state' or 'central' when role is admin
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

    # Add admin_level column for differentiating state vs central admin
    try:
        cur.execute("ALTER TABLE users ADD COLUMN admin_level TEXT")
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

    # --- INVENTORY MANAGEMENT TABLES ---
    
    # Materials master table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL,
            unit TEXT NOT NULL,
            unit_cost DECIMAL(10,2),
            description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Suppliers table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_person TEXT,
            email TEXT,
            phone TEXT,
            address TEXT,
            lead_time_days INTEGER NOT NULL DEFAULT 7,
            reliability_rating DECIMAL(3,2) DEFAULT 5.0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Material suppliers relationship
    cur.execute("""
        CREATE TABLE IF NOT EXISTS material_suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER NOT NULL,
            supplier_id INTEGER NOT NULL,
            supplier_unit_cost DECIMAL(10,2),
            minimum_order_quantity DECIMAL(10,2),
            is_primary BOOLEAN DEFAULT FALSE,
            FOREIGN KEY(material_id) REFERENCES materials(id),
            FOREIGN KEY(supplier_id) REFERENCES suppliers(id),
            UNIQUE(material_id, supplier_id)
        )
    """)

    # Current inventory levels
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER NOT NULL UNIQUE,
            current_stock DECIMAL(10,2) NOT NULL DEFAULT 0,
            reserved_stock DECIMAL(10,2) NOT NULL DEFAULT 0,
            reorder_point DECIMAL(10,2) NOT NULL DEFAULT 0,
            max_stock DECIMAL(10,2) NOT NULL DEFAULT 1000,
            location TEXT,
            last_updated TEXT NOT NULL,
            FOREIGN KEY(material_id) REFERENCES materials(id)
        )
    """)

    # Material usage logs (consumption tracking)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS material_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            material_id INTEGER NOT NULL,
            quantity_used DECIMAL(10,2) NOT NULL,
            unit_cost DECIMAL(10,2),
            total_cost DECIMAL(10,2),
            usage_date TEXT NOT NULL,
            logged_by INTEGER NOT NULL,
            notes TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(material_id) REFERENCES materials(id),
            FOREIGN KEY(logged_by) REFERENCES users(id)
        )
    """)

    # Delivery logs (incoming material tracking)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS material_deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER NOT NULL,
            project_id INTEGER,
            supplier_id INTEGER,
            quantity_delivered DECIMAL(10,2) NOT NULL,
            unit_cost DECIMAL(10,2),
            total_cost DECIMAL(10,2),
            delivery_date TEXT NOT NULL,
            received_by INTEGER NOT NULL,
            purchase_order_number TEXT,
            invoice_number TEXT,
            quality_check_status TEXT DEFAULT 'pending',
            notes TEXT,
            FOREIGN KEY(material_id) REFERENCES materials(id),
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(supplier_id) REFERENCES suppliers(id),
            FOREIGN KEY(received_by) REFERENCES users(id)
        )
    """)

    # Add project_id column to material_deliveries if missing (migration)
    try:
        cur.execute("ALTER TABLE material_deliveries ADD COLUMN project_id INTEGER")
    except sqlite3.OperationalError:
        pass  # Column exists

    # Reorder alerts table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reorder_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER NOT NULL,
            project_id INTEGER,
            alert_type TEXT NOT NULL CHECK (alert_type IN ('low_stock', 'stockout', 'overstock')),
            current_stock DECIMAL(10,2),
            reorder_point DECIMAL(10,2),
            suggested_order_quantity DECIMAL(10,2),
            priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
            status TEXT DEFAULT 'active' CHECK (status IN ('active', 'acknowledged', 'resolved')),
            created_at TEXT NOT NULL,
            acknowledged_by INTEGER,
            acknowledged_at TEXT,
            resolved_at TEXT,
            FOREIGN KEY(material_id) REFERENCES materials(id),
            FOREIGN KEY(acknowledged_by) REFERENCES users(id),
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    """)

    # Add project_id column to reorder_alerts if missing (migration)
    try:
        cur.execute("ALTER TABLE reorder_alerts ADD COLUMN project_id INTEGER")
    except sqlite3.OperationalError:
        pass  # Column exists

    # Purchase orders table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS purchase_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER NOT NULL,
            order_number TEXT UNIQUE NOT NULL,
            total_amount DECIMAL(12,2),
            status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'sent', 'confirmed', 'partial_delivered', 'delivered', 'cancelled')),
            order_date TEXT NOT NULL,
            expected_delivery_date TEXT,
            actual_delivery_date TEXT,
            created_by INTEGER NOT NULL,
            notes TEXT,
            FOREIGN KEY(supplier_id) REFERENCES suppliers(id),
            FOREIGN KEY(created_by) REFERENCES users(id)
        )
    """)

    # Purchase order items
    cur.execute("""
        CREATE TABLE IF NOT EXISTS purchase_order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_order_id INTEGER NOT NULL,
            material_id INTEGER NOT NULL,
            quantity DECIMAL(10,2) NOT NULL,
            unit_cost DECIMAL(10,2) NOT NULL,
            total_cost DECIMAL(10,2) NOT NULL,
            delivered_quantity DECIMAL(10,2) DEFAULT 0,
            FOREIGN KEY(purchase_order_id) REFERENCES purchase_orders(id),
            FOREIGN KEY(material_id) REFERENCES materials(id)
        )
    """)

    # Initialize default materials based on our forecasting models
    current_time = datetime.now().isoformat()
    try:
        cur.execute("""
            INSERT OR IGNORE INTO materials (name, category, unit, unit_cost, description, created_at, updated_at)
            VALUES 
            ('Steel', 'Structural', 'Tons', 850.0, 'Construction steel for towers and structures', ?, ?),
            ('Conductor', 'Electrical', 'Meters', 12.50, 'Electrical conductors for power transmission', ?, ?),
            ('Transformers', 'Electrical', 'Units', 25000.0, 'Power transformers for substations', ?, ?),
            ('Earthwire', 'Electrical', 'Meters', 8.75, 'Grounding wire for electrical safety', ?, ?),
            ('Foundation', 'Civil', 'Cubic Meters', 120.0, 'Concrete foundation materials', ?, ?),
            ('Reactors', 'Electrical', 'Units', 15000.0, 'Electrical reactors for power systems', ?, ?),
            ('Tower', 'Structural', 'Units', 5500.0, 'Pre-fabricated transmission towers', ?, ?)
        """, (current_time, current_time, current_time, current_time, current_time, current_time, 
              current_time, current_time, current_time, current_time, current_time, current_time,
              current_time, current_time))

        # Initialize inventory for default materials
        cur.execute("""
            INSERT OR IGNORE INTO inventory (material_id, current_stock, reorder_point, max_stock, location, last_updated)
            SELECT id, 0.0, 0.0, 500.0, 'Main Warehouse', ? FROM materials
        """, (current_time,))
    except Exception as e:
        print(f"Warning: Could not initialize default materials: {e}")
    
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
        admin_level = data.get('admin_level', '').lower()
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
        
        # Validation rules:
        # - employee: state required
        # - admin + state: state required
        # - admin + central: state must be empty
        if role == 'employee' and not state:
            return jsonify({"error": "State is required for employees."}), 400
        if role == 'admin':
            if admin_level not in ['state', 'central']:
                return jsonify({"error": "Admin level must be 'state' or 'central'."}), 400
            if admin_level == 'state' and not state:
                return jsonify({"error": "State is required for state admins."}), 400
            if admin_level == 'central' and state:
                return jsonify({"error": "Central admins should not select a state."}), 400
        
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
                'INSERT INTO users (fullname, username, password_hash, salt, role, state, admin_level, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (fullname or username, username, password_hash, salt, role, state if role != 'admin' or admin_level == 'state' else None, admin_level if role == 'admin' else None, datetime.now().isoformat())
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
                "admin_level": user['admin_level'] if 'admin_level' in user.keys() else None,
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
        # Central admin cannot create projects
        creator_user = get_user_by_id(created_by_user_id)
        if creator_user and creator_user['role'] == 'admin' and (creator_user['admin_level'] or '').lower() == 'central':
            return jsonify({"error": "Central admins cannot create projects."}), 403
        
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
        
        # AUTO-RESERVE MATERIALS based on forecast
        try:
            # Get material IDs for forecasted materials
            material_mapping = {
                'steel': 'Steel',
                'conductor': 'Conductor', 
                'transformers': 'Transformers',
                'earthwire': 'Earthwire',
                'foundation': 'Foundation',
                'reactors': 'Reactors',
                'tower': 'Tower'
            }
            
            for forecast_key, material_name in material_mapping.items():
                forecast_value = forecasts.get(forecast_key, 0)
                if forecast_value > 0:
                    # Get material ID
                    cur.execute('SELECT id FROM materials WHERE name = ?', (material_name,))
                    material_row = cur.fetchone()
                    
                    if material_row:
                        material_id = material_row[0]
                        
                        # Update reserved stock in inventory
                        cur.execute("""
                            UPDATE inventory 
                            SET reserved_stock = reserved_stock + ?,
                                last_updated = ?
                            WHERE material_id = ?
                        """, (forecast_value, datetime.now().isoformat(), material_id))
                        
                        # Log the reservation in material_usage with negative quantity to indicate reservation
                        cur.execute("""
                            INSERT INTO material_usage 
                            (project_id, material_id, quantity_used, unit_cost, total_cost, usage_date, logged_by, notes)
                            VALUES (?, ?, ?, 0, 0, ?, ?, ?)
                        """, (project_id, material_id, -forecast_value, datetime.now().isoformat(), 
                              created_by_user_id, f'Auto-reserved based on AI forecast for project creation'))
                        
                        print(f"Reserved {forecast_value} units of {material_name} for project {project_id}")
        
        except Exception as e:
            print(f"Warning: Failed to auto-reserve materials: {e}")
            # Continue without failing the project creation
        
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
            # If central admin: can only approve/decline (see frontend), show all pending projects
            if (user['admin_level'] or '').lower() == 'central':
                cur.execute("""
                    SELECT * FROM projects 
                    WHERE status IN ('pending','approved','declined','finished','deleted')
                    ORDER BY created_at DESC
                """)
            else:
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

# --- INVENTORY MANAGEMENT ENDPOINTS ---

@app.route('/inventory/materials', methods=['GET'])
def get_materials():
    """Get all materials with current inventory levels"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Optional project filter for delivery_count
        project_id_filter = request.args.get('project_id', type=int)
        if project_id_filter:
            cur.execute("""
                SELECT 
                    m.id, m.name, m.category, m.unit, m.unit_cost, m.description,
                    i.current_stock, i.reserved_stock, 
                    (i.current_stock - i.reserved_stock) as available_stock,
                    i.reorder_point, i.max_stock, i.location, i.last_updated,
                    COALESCE((SELECT COUNT(1) FROM material_deliveries d WHERE d.material_id = m.id AND d.project_id = ?), 0) as delivery_count,
                    COALESCE((SELECT SUM(d.quantity_delivered) FROM material_deliveries d WHERE d.material_id = m.id AND d.project_id = ?), 0) as project_delivered,
                    COALESCE((SELECT SUM(mu.quantity_used) FROM material_usage mu WHERE mu.material_id = m.id AND mu.project_id = ?), 0) as project_used
                FROM materials m
                LEFT JOIN inventory i ON m.id = i.material_id
                ORDER BY m.category, m.name
            """, (project_id_filter, project_id_filter, project_id_filter))
        else:
            cur.execute("""
                SELECT 
                    m.id, m.name, m.category, m.unit, m.unit_cost, m.description,
                    i.current_stock, i.reserved_stock, 
                    (i.current_stock - i.reserved_stock) as available_stock,
                    i.reorder_point, i.max_stock, i.location, i.last_updated,
                    COALESCE((SELECT COUNT(1) FROM material_deliveries d WHERE d.material_id = m.id), 0) as delivery_count
                FROM materials m
                LEFT JOIN inventory i ON m.id = i.material_id
                ORDER BY m.category, m.name
            """)
        
        materials = []
        for row in cur.fetchall():
            materials.append({
                'id': row[0],
                'name': row[1],
                'category': row[2],
                'unit': row[3],
                'unit_cost': row[4],
                'description': row[5],
                'current_stock': row[6] or 0,
                'reserved_stock': row[7] or 0,
                'available_stock': row[8] or 0,
                'reorder_point': row[9] or 0,
                'max_stock': row[10] or 1000,
                'location': row[11] or 'Unknown',
                'last_updated': row[12],
                'delivery_count': row[13],
                'project_delivered': row[14] if len(row) > 14 else None,
                'project_used': row[15] if len(row) > 15 else None
            })
        
        conn.close()
        return jsonify(materials)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/inventory/usage', methods=['POST'])
def log_material_usage():
    """Log material usage for a project"""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        material_id = data.get('material_id')
        quantity_used = data.get('quantity_used')
        logged_by = data.get('logged_by')
        notes = data.get('notes', '')
        
        if not all([project_id, material_id, quantity_used, logged_by]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get material unit cost
        cur.execute('SELECT unit_cost FROM materials WHERE id = ?', (material_id,))
        material = cur.fetchone()
        if not material:
            return jsonify({'error': 'Material not found'}), 404
        
        unit_cost = material[0] or 0
        total_cost = float(quantity_used) * float(unit_cost)
        
        # Log the usage
        cur.execute("""
            INSERT INTO material_usage 
            (project_id, material_id, quantity_used, unit_cost, total_cost, usage_date, logged_by, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (project_id, material_id, quantity_used, unit_cost, total_cost, 
              datetime.now().isoformat(), logged_by, notes))

        # If no deliveries yet for this material, keep current_stock at zero
        cur.execute("SELECT COUNT(1) FROM material_deliveries WHERE material_id = ?", (material_id,))
        deliveries_before_usage_row = cur.fetchone()
        deliveries_before_usage = deliveries_before_usage_row[0] if deliveries_before_usage_row else 0

        if deliveries_before_usage > 0:
            # Update inventory only if at least one delivery has happened
            cur.execute("""
                UPDATE inventory 
                SET current_stock = current_stock - ?,
                    last_updated = ?
                WHERE material_id = ?
            """, (quantity_used, datetime.now().isoformat(), material_id))
        
        conn.commit()
        
        # After logging usage, compute dynamic threshold and create alert only if needed
        # Has at least one delivery (first stocking)?
        cur.execute("""
            SELECT COUNT(1) FROM material_deliveries WHERE material_id = ? AND project_id = ?
        """, (material_id, project_id))
        deliveries_count_row = cur.fetchone()
        deliveries_count = deliveries_count_row[0] if deliveries_count_row else 0

        if deliveries_count > 0:
            # Compute per-project current stock = deliveries - usage for this project
            cur.execute("""
                SELECT COALESCE(SUM(quantity_delivered),0) FROM material_deliveries 
                WHERE material_id = ? AND project_id = ?
            """, (material_id, project_id))
            delivered_sum = cur.fetchone()[0] or 0
            cur.execute("""
                SELECT COALESCE(SUM(quantity_used),0) FROM material_usage 
                WHERE material_id = ? AND project_id = ?
            """, (material_id, project_id))
            used_sum = cur.fetchone()[0] or 0
            project_current_stock = float(delivered_sum) - float(used_sum)

            # Dynamic threshold based on last 30 days and 10% buffer
            threshold = compute_project_threshold(cur, int(material_id), int(project_id), lookback_days=30, safety_buffer_ratio=0.10)

            if project_current_stock < threshold and threshold > 0:
                # Suggested order should suffice next lead-time days (not the threshold window)
                name_key = ''
                try:
                    cur.execute("SELECT name FROM materials WHERE id = ?", (material_id,))
                    nrow = cur.fetchone()
                    name_key = str(nrow[0]).lower() if nrow and nrow[0] else ''
                except Exception:
                    name_key = ''
                lead_days = int(MATERIAL_DEFAULTS.get(name_key, 90))
                buffer_days = 4
                avg_daily = compute_project_avg_daily(cur, int(material_id), int(project_id), lookback_days=30)
                target_for_lead = float(avg_daily) * float(max(lead_days + buffer_days, 0))
                suggested_qty = max(target_for_lead, 0)

                # Create or update alert with dynamic threshold and lead-days suggestion
                cur.execute("""
                    INSERT OR REPLACE INTO reorder_alerts 
                    (id, material_id, project_id, alert_type, current_stock, reorder_point, 
                     suggested_order_quantity, priority, status, created_at)
                    VALUES (
                        (
                            SELECT id FROM reorder_alerts 
                            WHERE material_id = ? AND project_id = ? AND status = 'active'
                            LIMIT 1
                        ),
                        ?, ?, ?, ?, ?, ?, ?, 'active', ?
                    )
                """, (
                    material_id, project_id,
                    material_id, project_id, 'low_stock', project_current_stock, threshold,
                    suggested_qty,
                    'high' if project_current_stock <= 0 else 'medium',
                    datetime.now().isoformat()
                ))
                conn.commit()
            # Email notifications removed per requirement
        
        conn.close()
        
        return jsonify({
            'message': 'Material usage logged successfully',
            'usage_id': cur.lastrowid,
            'total_cost': total_cost
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/inventory/delivery', methods=['POST'])
def log_material_delivery():
    """Log material delivery/receipt"""
    try:
        data = request.get_json()
        material_id = data.get('material_id')
        project_id = data.get('project_id')
        quantity_delivered = data.get('quantity_delivered')
        received_by = data.get('received_by')
        supplier_id = data.get('supplier_id')
        unit_cost = data.get('unit_cost')
        purchase_order_number = data.get('purchase_order_number', '')
        invoice_number = data.get('invoice_number', '')
        notes = data.get('notes', '')
        
        if not all([material_id, quantity_delivered, received_by]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get material default cost if not provided
        if not unit_cost:
            cur.execute('SELECT unit_cost FROM materials WHERE id = ?', (material_id,))
            material = cur.fetchone()
            unit_cost = material[0] if material else 0
        
        total_cost = float(quantity_delivered) * float(unit_cost)
        
        # Log the delivery
        cur.execute("""
            INSERT INTO material_deliveries 
            (material_id, project_id, supplier_id, quantity_delivered, unit_cost, total_cost, 
             delivery_date, received_by, purchase_order_number, invoice_number, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (material_id, project_id, supplier_id, quantity_delivered, unit_cost, total_cost,
              datetime.now().isoformat(), received_by, purchase_order_number, 
              invoice_number, notes))
        
        # Update inventory
        cur.execute("""
            UPDATE inventory 
            SET current_stock = current_stock + ?,
                last_updated = ?
            WHERE material_id = ?
        """, (quantity_delivered, datetime.now().isoformat(), material_id))
        
        # If no inventory record exists, create one
        if cur.rowcount == 0:
            cur.execute("""
                INSERT INTO inventory (material_id, current_stock, reorder_point, max_stock, location, last_updated)
                VALUES (?, ?, 0.0, 500.0, 'Main Warehouse', ?)
            """, (material_id, quantity_delivered, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Material delivery logged successfully',
            'delivery_id': cur.lastrowid,
            'total_cost': total_cost
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/inventory/alerts', methods=['GET'])
def get_reorder_alerts():
    """Get all active reorder alerts"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Optional project_id filter
        project_id = request.args.get('project_id', type=int)
        if project_id:
            cur.execute("""
                SELECT 
                    ra.id, ra.alert_type, ra.current_stock, ra.reorder_point,
                    ra.suggested_order_quantity, ra.priority, ra.created_at,
                    m.name, m.unit, m.category, m.unit_cost, ra.project_id
                FROM reorder_alerts ra
                JOIN materials m ON ra.material_id = m.id
                WHERE ra.status = 'active' AND ra.project_id = ?
                ORDER BY 
                    CASE ra.priority 
                        WHEN 'critical' THEN 1 
                        WHEN 'high' THEN 2 
                        WHEN 'medium' THEN 3 
                        ELSE 4 
                    END,
                    ra.created_at DESC
            """, (project_id,))
        else:
            cur.execute("""
                SELECT 
                    ra.id, ra.alert_type, ra.current_stock, ra.reorder_point,
                    ra.suggested_order_quantity, ra.priority, ra.created_at,
                    m.name, m.unit, m.category, m.unit_cost, ra.project_id
                FROM reorder_alerts ra
                JOIN materials m ON ra.material_id = m.id
                WHERE ra.status = 'active'
                ORDER BY 
                    CASE ra.priority 
                        WHEN 'critical' THEN 1 
                        WHEN 'high' THEN 2 
                        WHEN 'medium' THEN 3 
                        ELSE 4 
                    END,
                    ra.created_at DESC
            """)
        
        base_rows = cur.fetchall()

        alerts = []
        for row in base_rows:
            alert = {
                'id': row[0],
                'alert_type': row[1],
                'current_stock': row[2],
                'reorder_point': row[3],
                'suggested_order_quantity': row[4],
                'priority': row[5],
                'created_at': row[6],
                'material_name': row[7],
                'unit': row[8],
                'category': row[9],
                'unit_cost': row[10],
                'project_id': row[11]
            }

            # Recompute suggested order using coverage = lead time days (+4 buffer) only
            if alert['project_id']:
                # Look up material_id via alert id
                cur.execute("SELECT material_id FROM reorder_alerts WHERE id = ?", (alert['id'],))
                row_mid = cur.fetchone()
                if row_mid:
                    material_id = int(row_mid[0])
                    avg_daily = compute_project_avg_daily(cur, material_id, int(alert['project_id']), lookback_days=30)
                    name_key = str(alert['material_name']).lower() if alert['material_name'] else ''
                    cov_days = int(MATERIAL_DEFAULTS.get(name_key, 90))
                    buffer_days = 4
                    target_qty = float(avg_daily) * float(max(cov_days + buffer_days, 0))
                    recomputed = max(target_qty, 0)
                    alert['suggested_order_quantity'] = recomputed
            alerts.append(alert)
        
        conn.close()
        return jsonify(alerts)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/inventory/alerts/<alert_id>/acknowledge', methods=['PUT'])
def acknowledge_alert(alert_id):
    """Acknowledge a reorder alert"""
    try:
        data = request.get_json()
        acknowledged_by = data.get('acknowledged_by')
        
        if not acknowledged_by:
            return jsonify({'error': 'acknowledged_by is required'}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE reorder_alerts 
            SET status = 'acknowledged',
                acknowledged_by = ?,
                acknowledged_at = ?
            WHERE id = ?
        """, (acknowledged_by, datetime.now().isoformat(), alert_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Alert acknowledged successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/inventory/dashboard', methods=['GET'])
def get_inventory_dashboard():
    """Get inventory dashboard data"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get inventory summary
        cur.execute("""
            SELECT 
                COUNT(*) as total_materials,
                SUM(CASE WHEN i.current_stock <= i.reorder_point THEN 1 ELSE 0 END) as low_stock_count,
                SUM(CASE WHEN i.current_stock <= 0 THEN 1 ELSE 0 END) as stockout_count,
                SUM(i.current_stock * m.unit_cost) as total_inventory_value
            FROM materials m
            LEFT JOIN inventory i ON m.id = i.material_id
        """)
        summary = cur.fetchone()
        
        # Get recent usage
        cur.execute("""
            SELECT 
                mu.usage_date, mu.quantity_used, mu.total_cost,
                m.name, m.unit, p.location
            FROM material_usage mu
            JOIN materials m ON mu.material_id = m.id
            JOIN projects p ON mu.project_id = p.id
            ORDER BY mu.usage_date DESC
            LIMIT 10
        """)
        recent_usage = cur.fetchall()
        
        # Get recent deliveries
        cur.execute("""
            SELECT 
                md.delivery_date, md.quantity_delivered, md.total_cost,
                m.name, m.unit, s.name as supplier_name
            FROM material_deliveries md
            JOIN materials m ON md.material_id = m.id
            LEFT JOIN suppliers s ON md.supplier_id = s.id
            ORDER BY md.delivery_date DESC
            LIMIT 10
        """)
        recent_deliveries = cur.fetchall()
        
        # Get top consuming materials (last 30 days)
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        cur.execute("""
            SELECT 
                m.name, m.unit, SUM(mu.quantity_used) as total_used,
                SUM(mu.total_cost) as total_cost
            FROM material_usage mu
            JOIN materials m ON mu.material_id = m.id
            WHERE mu.usage_date >= ?
            GROUP BY m.id, m.name, m.unit
            ORDER BY total_used DESC
            LIMIT 5
        """, (thirty_days_ago,))
        top_consuming = cur.fetchall()
        
        conn.close()
        
        return jsonify({
            'summary': {
                'total_materials': summary[0] or 0,
                'low_stock_count': summary[1] or 0,
                'stockout_count': summary[2] or 0,
                'total_inventory_value': summary[3] or 0
            },
            'recent_usage': [
                {
                    'date': row[0],
                    'quantity': row[1],
                    'cost': row[2],
                    'material': row[3],
                    'unit': row[4],
                    'project_location': row[5]
                }
                for row in recent_usage
            ],
            'recent_deliveries': [
                {
                    'date': row[0],
                    'quantity': row[1],
                    'cost': row[2],
                    'material': row[3],
                    'unit': row[4],
                    'supplier': row[5] or 'Unknown'
                }
                for row in recent_deliveries
            ],
            'top_consuming': [
                {
                    'material': row[0],
                    'unit': row[1],
                    'total_used': row[2],
                    'total_cost': row[3]
                }
                for row in top_consuming
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/inventory/project-usage/<project_id>', methods=['GET'])
def get_project_material_usage(project_id):
    """Get material usage for a specific project"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                mu.id, mu.quantity_used, mu.unit_cost, mu.total_cost, 
                mu.usage_date, mu.notes,
                m.name, m.unit, m.category,
                u.fullname as logged_by_name
            FROM material_usage mu
            JOIN materials m ON mu.material_id = m.id
            JOIN users u ON mu.logged_by = u.id
            WHERE mu.project_id = ?
            ORDER BY mu.usage_date DESC
        """, (project_id,))
        
        usage_records = []
        for row in cur.fetchall():
            usage_records.append({
                'id': row[0],
                'quantity_used': row[1],
                'unit_cost': row[2],
                'total_cost': row[3],
                'usage_date': row[4],
                'notes': row[5],
                'material_name': row[6],
                'unit': row[7],
                'category': row[8],
                'logged_by': row[9]
            })
        
        conn.close()
        return jsonify(usage_records)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- BACKGROUND TASKS FOR INVENTORY MONITORING ---

def calculate_reorder_points():
    """Calculate dynamic reorder points based on usage patterns"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get all materials
        cur.execute('SELECT id FROM materials')
        materials = cur.fetchall()
        
        for material in materials:
            material_id = material[0]
            
            # Calculate average daily usage (last 30 days)
            thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
            cur.execute("""
                SELECT AVG(daily_usage) FROM (
                    SELECT DATE(usage_date) as usage_day, SUM(quantity_used) as daily_usage
                    FROM material_usage 
                    WHERE material_id = ? AND usage_date >= ?
                    GROUP BY DATE(usage_date)
                )
            """, (material_id, thirty_days_ago))
            
            result = cur.fetchone()
            avg_daily_usage = result[0] if result[0] else 0
            
            if avg_daily_usage > 0:
                # Get primary supplier lead time
                cur.execute("""
                    SELECT s.lead_time_days FROM suppliers s
                    JOIN material_suppliers ms ON s.id = ms.supplier_id
                    WHERE ms.material_id = ? AND ms.is_primary = 1
                    LIMIT 1
                """, (material_id,))
                
                supplier = cur.fetchone()
                lead_time = supplier[0] if supplier else 7  # Default 7 days
                
                # Calculate reorder point: (avg_daily_usage * lead_time) + safety_stock
                safety_stock = avg_daily_usage * 3  # 3 days safety stock
                new_reorder_point = (avg_daily_usage * lead_time) + safety_stock
                
                # Update reorder point
                cur.execute("""
                    UPDATE inventory 
                    SET reorder_point = ?, last_updated = ?
                    WHERE material_id = ?
                """, (new_reorder_point, datetime.now().isoformat(), material_id))
        
        conn.commit()
        conn.close()
        print(f"Reorder points recalculated at {datetime.now()}")
        
    except Exception as e:
        print(f"Error calculating reorder points: {e}")

def check_inventory_alerts():
    """Check for low stock and create alerts using dynamic per-project threshold"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Iterate materials and projects; evaluate dynamic thresholds and upsert alerts
        cur.execute("SELECT id, name FROM materials")
        materials = cur.fetchall()
        sixty_days_ago = (datetime.now() - timedelta(days=60)).isoformat()

        for m in materials:
            material_id = m['id'] if isinstance(m, sqlite3.Row) else m[0]
            material_name = m['name'] if isinstance(m, sqlite3.Row) else m[1]

            # Projects that have any usage or deliveries for this material
            cur.execute(
                """
                    SELECT DISTINCT p.id
                    FROM projects p
                    LEFT JOIN material_deliveries md ON md.project_id = p.id AND md.material_id = ?
                    LEFT JOIN material_usage mu ON mu.project_id = p.id AND mu.material_id = ?
                    WHERE md.id IS NOT NULL OR mu.id IS NOT NULL
                """,
                (material_id, material_id)
            )
            project_rows = cur.fetchall()

            for pr in project_rows:
                project_id = pr['id'] if isinstance(pr, sqlite3.Row) else pr[0]

                # Require at least one delivery for this project/material
                cur.execute("SELECT COUNT(1) FROM material_deliveries WHERE material_id = ? AND project_id = ?", (material_id, project_id))
                deliveries_count = cur.fetchone()[0] or 0
                if deliveries_count == 0:
                    continue

                # Project current stock = deliveries - usage
                cur.execute("SELECT COALESCE(SUM(quantity_delivered),0) FROM material_deliveries WHERE material_id = ? AND project_id = ?", (material_id, project_id))
                delivered_sum = cur.fetchone()[0] or 0
                cur.execute("SELECT COALESCE(SUM(quantity_used),0) FROM material_usage WHERE material_id = ? AND project_id = ?", (material_id, project_id))
                used_sum = cur.fetchone()[0] or 0
                project_current_stock = float(delivered_sum) - float(used_sum)

                # Require recent usage activity (last 60 days) or any reservations
                cur.execute("""
                    SELECT COUNT(1) FROM material_usage 
                    WHERE material_id = ? AND project_id = ? AND usage_date >= ? AND quantity_used > 0
                """, (material_id, project_id, sixty_days_ago))
                recent_usage_count = cur.fetchone()[0] or 0
                if recent_usage_count == 0:
                    cur.execute("SELECT reserved_stock FROM inventory WHERE material_id = ?", (material_id,))
                    rr = cur.fetchone()
                    reserved_stock = rr[0] if rr and rr[0] is not None else 0
                    if reserved_stock <= 0:
                        continue

                # Dynamic threshold per project/material
                threshold = compute_project_threshold(cur, int(material_id), int(project_id), lookback_days=30, safety_buffer_ratio=0.10)
                if threshold <= 0:
                    continue

                if project_current_stock < threshold:
                    alert_type = 'stockout' if project_current_stock <= 0 else 'low_stock'
                    priority = 'critical' if project_current_stock <= 0 else 'high'

                    # Suggest enough to cover next lead-time days
                    cur.execute("SELECT name FROM materials WHERE id = ?", (material_id,))
                    nrow = cur.fetchone()
                    name_key = str(nrow[0]).lower() if nrow and nrow[0] else ''
                    lead_days = int(MATERIAL_DEFAULTS.get(name_key, 75))
                    buffer_days = 4
                    avg_daily = compute_project_avg_daily(cur, int(material_id), int(project_id), lookback_days=30)
                    target_for_lead = float(avg_daily) * float(max(lead_days + buffer_days, 0))
                    suggested_qty = max(target_for_lead, 0)

                    cur.execute(
                        """
                            INSERT OR REPLACE INTO reorder_alerts 
                            (id, material_id, project_id, alert_type, current_stock, reorder_point,
                             suggested_order_quantity, priority, status, created_at)
                            VALUES (
                                (
                                    SELECT id FROM reorder_alerts 
                                    WHERE material_id = ? AND project_id = ? AND status = 'active'
                                    LIMIT 1
                                ),
                                ?, ?, ?, ?, ?, ?, ?, 'active', ?
                            )
                        """,
                        (
                            material_id, project_id,
                            material_id, project_id, alert_type, project_current_stock, threshold,
                            suggested_qty,
                            priority,
                            datetime.now().isoformat()
                        )
                    )
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error checking inventory alerts: {e}")

def inventory_monitoring_task():
    """Background task for inventory monitoring"""
    while True:
        try:
            # Run every hour
            time.sleep(3600)
            calculate_reorder_points()
            check_inventory_alerts()
        except Exception as e:
            print(f"Error in inventory monitoring task: {e}")
            time.sleep(300)  # Wait 5 minutes before retrying

# Start inventory monitoring in background
def start_inventory_monitoring():
    monitoring_thread = threading.Thread(target=inventory_monitoring_task, daemon=True)
    monitoring_thread.start()
    print("Inventory monitoring started")

if __name__ == "__main__":
    init_periodic_db()
    if LOADED_MODELS:
        start_inventory_monitoring()
        app.run(debug=True, host="0.0.0.0", port=5002)
    else:
        print("Application startup failed due to model loading error.")

# Email notification code removed per requirement