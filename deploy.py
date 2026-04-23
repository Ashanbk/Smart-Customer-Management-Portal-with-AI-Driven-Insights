import requests
import json
import os

API_KEY = "rnd_AV4aZEB7P6oX1BFTIIkvKaUMEdTI"
OWNER_ID = "tea-d7l41fho3t8c73eklobg"
REPO_URL = "https://github.com/Ashanbk/Smart-Customer-Management-Portal-with-AI-Driven-Insights"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def create_backend():
    url = "https://api.render.com/v1/services"
    payload = {
        "type": "web_service",
        "name": "smart-customer-backend-api",
        "ownerId": OWNER_ID,
        "repo": REPO_URL,
        "branch": "main",
        "rootDir": "smart-customer-portal",
        "serviceDetails": {
            "env": "python",
            "envSpecificDetails": {
                "buildCommand": "pip install -r requirements.txt",
                "startCommand": "gunicorn 'app:create_app()'"
            },
            "envVars": [
                {"key": "PYTHON_VERSION", "value": "3.11.4", "generateValue": False}
            ]
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print("Backend Response:", response.status_code, response.text)
    return response.json() if response.status_code == 201 else None

def create_frontend(backend_url):
    url = "https://api.render.com/v1/services"
    payload = {
        "type": "web_service",
        "name": "smart-customer-frontend-ui",
        "ownerId": OWNER_ID,
        "repo": REPO_URL,
        "branch": "main",
        "rootDir": "frontend",
        "serviceDetails": {
            "env": "python",
            "envSpecificDetails": {
                "buildCommand": "pip install -r requirements.txt",
                "startCommand": "streamlit run app.py --server.port $PORT"
            },
            "envVars": [
                {"key": "PYTHON_VERSION", "value": "3.11.4", "generateValue": False},
                {"key": "BACKEND_URL", "value": backend_url, "generateValue": False}
            ]
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print("Frontend Response:", response.status_code, response.text)
    return response.json()

if __name__ == "__main__":
    print("Deploying backend...")
    backend = create_backend()
    if backend and 'service' in backend:
        backend_url = backend['service']['serviceDetails']['url']
        print(f"Backend deployed at: {backend_url}")
        
        print("Deploying frontend...")
        frontend = create_frontend(backend_url)
        if frontend and 'service' in frontend:
            print(f"Frontend deployed at: {frontend['service']['serviceDetails']['url']}")
    else:
        print("Failed to deploy backend.")
