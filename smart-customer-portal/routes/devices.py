from __future__ import annotations

from flask import jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from models import Customer, Device, db

from .main import main_bp
from .utils import error_response

DEVICE_FIELDS = {"customer_id", "device_type", "count"}


def device_to_dict(device: Device) -> dict:
    return {
        "id": device.id,
        "customer_id": device.customer_id,
        "device_type": device.device_type,
        "count": device.count,
    }


def parse_device_payload(payload: dict) -> tuple[dict | None, str | None]:
    missing_fields = sorted(DEVICE_FIELDS - payload.keys())
    if missing_fields:
        return None, f"Missing required fields: {', '.join(missing_fields)}"

    unknown_fields = sorted(set(payload.keys()) - DEVICE_FIELDS)
    if unknown_fields:
        return None, f"Unknown fields in payload: {', '.join(unknown_fields)}"

    parsed: dict = {}
    try:
        parsed["customer_id"] = int(payload["customer_id"])
    except (TypeError, ValueError):
        return None, "Field 'customer_id' must be an integer."

    device_type = payload.get("device_type")
    if not isinstance(device_type, str) or not device_type.strip():
        return None, "Field 'device_type' must be a non-empty string."
    parsed["device_type"] = device_type.strip()

    try:
        parsed["count"] = int(payload["count"])
    except (TypeError, ValueError):
        return None, "Field 'count' must be an integer."

    return parsed, None


@main_bp.get("/devices")
def get_devices():
    try:
        devices = Device.query.order_by(Device.id.asc()).all()
    except SQLAlchemyError:
        return error_response("Failed to fetch devices.", status_code=500)

    return jsonify([device_to_dict(device) for device in devices]), 200


@main_bp.post("/devices")
def create_device():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error_response("Request body must be valid JSON.")

    parsed_payload, validation_error = parse_device_payload(payload)
    if validation_error:
        return error_response(validation_error)

    try:
        customer = db.session.get(Customer, parsed_payload["customer_id"])
        if customer is None:
            return error_response("Customer not found.", status_code=404)

        device = Device(**parsed_payload)
        db.session.add(device)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return error_response("Failed to create device.", status_code=500)

    return jsonify(device_to_dict(device)), 201
