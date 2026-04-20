# 🧠 Smart Customer Management Portal with AI-Driven Insights

A lightweight AI-powered customer management web application for a fictional networking hardware company. This project combines traditional CRM features with machine learning and LLM-based intelligence to provide actionable customer insights.

---

# 🚀 Overview

This portal enables users to manage customer data while leveraging AI to:

* Perform natural language queries on customer data
* Predict customer churn risk
* Generate account health scores
* Automate weekly customer summary reports

The system uses synthetic data and simulates real-world enterprise analytics workflows.

---

# 🛠️ Tech Stack

* **Backend:** Flask
* **Database:** SQLite
* **ORM:** SQLAlchemy
* **ML:** scikit-learn
* **AI Integration:** OpenAI API
* **Data Generation:** Faker

---

# 📁 Project Structure

```
smart-customer-portal/
│
├── models/                # Database models
├── routes/                # API routes (customers, tickets, devices, NL queries)
├── services/              # Business logic (health score, churn, email summary)
├── app.py                 # Flask app entry point
├── generate_data.py       # Script to generate synthetic data
├── train_churn_model.py   # ML model training script
├── requirements.txt
```

---

# ✅ Progress (Day 1)

### 🔹 Backend Setup

* Created Flask application structure
* Configured SQLite database
* Initialized SQLAlchemy

### 🔹 API Development

* Implemented Customer APIs:

  * `GET /customers`
  * `POST /customers`
  * `PUT /customers/<id>`
  * `DELETE /customers/<id>`

### 🔹 Advanced Features APIs

* `GET /customers/<id>/health-score` → AI-based health score
* `GET /customers/<id>/churn-risk` → ML churn prediction
* `GET /customers/<id>/email-summary` → AI-generated report

### 🔹 Routing Architecture

* Used Flask Blueprints for modular structure
* Centralized routing via `main_bp`

---

# ⚙️ How to Run

```bash
pip install -r requirements.txt
python app.py
```

Open in browser:

```
http://127.0.0.1:5000/
```

---

# 🧪 API Testing

Example endpoint:

```
http://127.0.0.1:5000/customers
```

Use tools like Postman or browser for testing.

---

# 🔜 Next Steps

* Generate 200+ synthetic customer records
* Train churn prediction model
* Implement natural language query interface
* Build frontend dashboard (Streamlit/React)
* Add data visualizations

---

# 📌 Notes

* Ensure all route modules are imported in `routes/main.py`
* Restart server after making changes
* Use `.env` for API keys (future integration)

---

---

* Clearing and checking fakers/generating fake customer IDs to test
* Entering frontend 
# 👨‍💻 Author

Ashan Kadadi
Aashritha Rajendra

---
