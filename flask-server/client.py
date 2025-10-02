
import requests
import json

# Define the URL of your Flask server's new endpoint
# 🚨 CHANGE 1: The URL is now for the '/predict_all' endpoint
FLASK_SERVER_URL = "http://localhost:5000/predict_all"

def get_all_predictions(project_data):
    """
    Sends a JSON payload to the Flask server's new endpoint
    and prints the received predictions for all 7 models.
    
    Args:
        project_data (dict): A dictionary containing project features.
    """
    # The JSON payload structure must match what app.py expects.
    # The 'input_features' key contains all the data required by the models.
    payload = {
        "input_features": {
            "budget": project_data["budget"],
            "location": project_data["location"],
            "towerType": project_data["towerType"],
            "substationType": project_data["substationType"],
            "geo": project_data["geo"],
            "taxes": project_data["taxes"],
        }
    }
    
    try:
        # The requests.post() function sends a POST request.
        response = requests.post(FLASK_SERVER_URL, json=payload)
        
        # Raise an HTTPError for bad responses (4xx or 5xx)
        response.raise_for_status()
        
        # 🚨 CHANGE 2: The response is now a dictionary of predictions
        all_predictions = response.json()
        
        # Print the results
        print("Success! Predictions for all 7 models received:")
        # Use json.dumps to pretty-print the dictionary for readability
        print(json.dumps(all_predictions, indent=4))
        
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to the Flask server: {e}")
    except json.JSONDecodeError:
        print("Error decoding JSON from the server response.")

if __name__ == "__main__":
    # Example project data from your application.
    new_project_data = {
        "budget": "10000000",
        "towerType": "400 kV", 
        "taxes": "18% GST",
        "location": "Bengaluru",
        "substationType": "AIS (Air Insulated Substation)",
        "geo": "Urban",
    }
    
    get_all_predictions(new_project_data)