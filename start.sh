#!/bin/bash
echo "Setting up Python environment..."
if [ ! -d ".venv" ]; then
  python -m venv .venv
fi
source .venv/bin/activate

echo "Starting Backend..."
cd smart-customer-portal
pip install -r requirements.txt
python app.py &
BACKEND_PID=$!
cd ..

echo "Starting Frontend..."
cd frontend
pip install -r requirements.txt
export BACKEND_URL="http://127.0.0.1:5000"
streamlit run app.py --server.port 8080 --server.address 0.0.0.0
