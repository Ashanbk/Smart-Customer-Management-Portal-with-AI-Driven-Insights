from flask import Flask

from models import db
from routes import main_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///smart_customer_portal.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    app.register_blueprint(main_bp)

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(debug=True)

@app.route("/")
def home():
    return "Backend is running 🚀"