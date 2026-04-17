from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .customer import Customer
from .device import Device
from .ticket import Ticket

__all__ = ["db", "Customer", "Ticket", "Device"]
