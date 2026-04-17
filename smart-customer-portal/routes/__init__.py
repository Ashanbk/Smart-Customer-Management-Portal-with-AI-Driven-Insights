from .main import main_bp

# Import route modules so their endpoints are registered on the blueprint.
from . import customers, devices, nl_query, tickets

__all__ = ["main_bp"]
