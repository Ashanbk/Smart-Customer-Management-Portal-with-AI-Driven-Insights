from . import db


class Device(db.Model):
    __tablename__ = "devices"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    device_type = db.Column(db.String(100), nullable=False)
    count = db.Column(db.Integer, nullable=False)

    customer = db.relationship("Customer", back_populates="devices")
