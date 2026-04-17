from __future__ import annotations

from datetime import datetime

from flask import jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from models import Customer, Ticket, db

from .main import main_bp
from .utils import error_response

TICKET_FIELDS = {"customer_id", "severity", "status", "created_at"}
REQUIRED_TICKET_FIELDS = {"customer_id", "severity", "status"}


def ticket_to_dict(ticket: Ticket) -> dict:
    return {
        "id": ticket.id,
        "customer_id": ticket.customer_id,
        "severity": ticket.severity,
        "status": ticket.status,
        "created_at": ticket.created_at.isoformat(),
    }


def parse_ticket_payload(payload: dict) -> tuple[dict | None, str | None]:
    missing_fields = sorted(REQUIRED_TICKET_FIELDS - payload.keys())
    if missing_fields:
        return None, f"Missing required fields: {', '.join(missing_fields)}"

    unknown_fields = sorted(set(payload.keys()) - TICKET_FIELDS)
    if unknown_fields:
        return None, f"Unknown fields in payload: {', '.join(unknown_fields)}"

    parsed: dict = {}
    try:
        parsed["customer_id"] = int(payload["customer_id"])
    except (TypeError, ValueError):
        return None, "Field 'customer_id' must be an integer."

    severity = payload.get("severity")
    status = payload.get("status")
    if not isinstance(severity, str) or not severity.strip():
        return None, "Field 'severity' must be a non-empty string."
    if not isinstance(status, str) or not status.strip():
        return None, "Field 'status' must be a non-empty string."

    parsed["severity"] = severity.strip()
    parsed["status"] = status.strip()

    created_at = payload.get("created_at")
    if created_at is not None:
        if not isinstance(created_at, str):
            return None, "Field 'created_at' must be an ISO datetime string."
        try:
            parsed["created_at"] = datetime.fromisoformat(created_at)
        except ValueError:
            return None, "Field 'created_at' must be in ISO datetime format."

    return parsed, None


@main_bp.get("/tickets")
def get_tickets():
    try:
        tickets = Ticket.query.order_by(Ticket.id.asc()).all()
    except SQLAlchemyError:
        return error_response("Failed to fetch tickets.", status_code=500)

    return jsonify([ticket_to_dict(ticket) for ticket in tickets]), 200


@main_bp.post("/tickets")
def create_ticket():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error_response("Request body must be valid JSON.")

    parsed_payload, validation_error = parse_ticket_payload(payload)
    if validation_error:
        return error_response(validation_error)

    try:
        customer = db.session.get(Customer, parsed_payload["customer_id"])
        if customer is None:
            return error_response("Customer not found.", status_code=404)

        ticket = Ticket(**parsed_payload)
        db.session.add(ticket)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return error_response("Failed to create ticket.", status_code=500)

    return jsonify(ticket_to_dict(ticket)), 201
