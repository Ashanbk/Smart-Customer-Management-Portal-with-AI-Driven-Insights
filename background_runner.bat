@echo off
set PROJECT_DIR=f:\hackathon'\Smart-Customer-Management-Portal-with-AI-Driven-Insights\Smart-Customer-Management-Portal-with-AI-Driven-Insights
set DESKTOP_DIR=%USERPROFILE%\Desktop

cd /d "%PROJECT_DIR%\smart-customer-portal"
start /B python app.py

cd /d "%PROJECT_DIR%\frontend"
set BACKEND_URL=http://127.0.0.1:5000
start /B streamlit run app.py --server.port 8501

:: Wait a few seconds for Streamlit to start
timeout /t 5 >nul

:: Start Serveo and capture URL to Desktop
echo Starting Secure Tunnel... > "%DESKTOP_DIR%\Your_Live_Portal_Link.txt"
ssh -o StrictHostKeyChecking=no -R 80:localhost:8501 serveo.net >> "%DESKTOP_DIR%\Your_Live_Portal_Link.txt" 2>&1
