# 🧠 Smart Customer Management Portal with AI-Driven Insights

A full-stack AI-powered customer management system built for a fictional networking hardware company. This project combines traditional CRM functionality with machine learning and natural language processing to deliver actionable business insights.

---

## 🚀 Overview

This application allows users to:

- Manage customer data (CRUD operations)
- Analyze customer health scores
- Predict churn risk using AI/ML
- Perform natural language queries on customer data
- Generate automated weekly email summaries

The system uses **synthetic data** and simulates real-world enterprise analytics workflows.

---

## 🏗️ Tech Stack

### Backend
- Python (Flask)
- SQLAlchemy (ORM)
- SQLite (Database)
- AI/ML logic (custom scoring + rule-based model)

### Frontend
- Streamlit (interactive dashboard)

### AI Features
- Natural Language Query Interface
- Customer Health Score
- Churn Risk Prediction
- Email Summary Generator

---

## 📊 Features

### 1. Customer Management
- Create, Read, Update, Delete customers
- Store company details, usage, NPS, contracts

### 2. AI-Powered Insights
- 📈 Health Score (based on NPS, usage, tickets)
- ⚠️ Churn Prediction (risk probability + explanation)
- 🤖 Natural Language Query system

### 3. Dashboard
- Interactive UI using Streamlit
- Data tables and visualizations
- Real-time API integration

---

## 🧪 Sample Queries

- `low nps customers`
- `customers in apac`
- `high usage customers`
- `enterprise plan customers`

---

## 📁 Project Structure
-smart-customer-portal/
-│
-├── app.py
-├── models/
-├── routes/
-├── services/
-├── generate_data.py
-│
-frontend/
-├── app.py


---

## ⚙️ Setup Instructions

### 1. Clone Repository

backend Setup

```bash
git clone https://github.com/Ashanbk/Smart-Customer-Management-Portal-with-AI-Driven-Insights.git
cd Smart-Customer-Management-Portal-with-AI-Driven-Insights
```

Load Data

```bash
python generate_data.py
```

Run Frontend

```bash
cd ../frontend
streamlit run app.py
```

# 🌐 Access
-Backend: http://127.0.0.1:5000
-Frontend: http://localhost:8501

# 📦 Deliverables
-✅ Working full-stack application
-✅ 200+ synthetic customer records
-✅ AI-powered analytics features
-✅ Natural language query system
-✅ GitHub repository with source code

#  🎯 Future Improvements
-Deploy to cloud (Streamlit Cloud / Render)
-Add authentication
-Improve ML model accuracy
-Add advanced analytics dashboards

# 👨‍💻 Author

-Ashan Kadadi
-Aashritha Rajendra
