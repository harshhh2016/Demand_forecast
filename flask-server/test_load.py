import joblib

print("Attempting to load scaler.pkl...")
scaler = joblib.load('scaler.pkl')
print("scaler.pkl loaded successfully.")

print("Attempting to load model_columns.pkl...")
model_columns = joblib.load('model_columns.pkl')
print("model_columns.pkl loaded successfully.")

print("Attempting to load steel_model.pkl...")
steel_model = joblib.load('steel_model.pkl')
print("steel_model.pkl loaded successfully.")

print("All models loaded successfully!")