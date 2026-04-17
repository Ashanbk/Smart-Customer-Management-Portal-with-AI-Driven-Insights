from . import db


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(255), nullable=False)
    region = db.Column(db.String(100), nullable=False)
    plan_tier = db.Column(db.String(50), nullable=False)
    contract_start = db.Column(db.Date, nullable=False)
    contract_end = db.Column(db.Date, nullable=False)
    nps_score = db.Column(db.Integer, nullable=False)
    monthly_usage = db.Column(db.Float, nullable=False)

    tickets = db.relationship(
        "Ticket",
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    devices = db.relationship(
        "Device",
        back_populates="customer",
        cascade="all, delete-orphan",
    )
