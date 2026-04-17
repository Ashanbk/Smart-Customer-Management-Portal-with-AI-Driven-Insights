from __future__ import annotations

from datetime import date

from flask import Response, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from models import Customer, db
from services import (
    calculate_customer_health_score,
    generate_customer_email_summary,
    predict_customer_churn_risk,
)

from .main import main_bp
from .utils import error_response

CUSTOMER_FIELDS = {
    "company_name",
    "region",
    "plan_tier",
    "contract_start",
    "contract_end",
    "nps_score",
    "monthly_usage",
}


def customer_to_dict(customer: Customer) -> dict:
    return {
        "id": customer.id,
        "company_name": customer.company_name,
        "region": customer.region,
        "plan_tier": customer.plan_tier,
        "contract_start": customer.contract_start.isoformat(),
        "contract_end": customer.contract_end.isoformat(),
        "nps_score": customer.nps_score,
        "monthly_usage": customer.monthly_usage,
    }


def parse_customer_payload(payload: dict, partial: bool = False) -> tuple[dict | None, str | None]:
    unknown_fields = sorted(set(payload.keys()) - CUSTOMER_FIELDS)
    if unknown_fields:
        return None, f"Unknown fields in payload: {', '.join(unknown_fields)}"

    required_fields = CUSTOMER_FIELDS if not partial else set()
    missing_fields = sorted(required_fields - payload.keys())
    if missing_fields:
        return None, f"Missing required fields: {', '.join(missing_fields)}"

    parsed: dict = {}
    for key in CUSTOMER_FIELDS:
        if key not in payload:
            continue

        value = payload[key]
        if key in {"contract_start", "contract_end"}:
            if not isinstance(value, str):
                return None, f"Field '{key}' must be an ISO date string."
            try:
                parsed[key] = date.fromisoformat(value)
            except ValueError:
                return None, f"Field '{key}' must be in YYYY-MM-DD format."
        elif key == "nps_score":
            try:
                parsed[key] = int(value)
            except (TypeError, ValueError):
                return None, "Field 'nps_score' must be an integer."
        elif key == "monthly_usage":
            try:
                parsed[key] = float(value)
            except (TypeError, ValueError):
                return None, "Field 'monthly_usage' must be a number."
        else:
            if not isinstance(value, str) or not value.strip():
                return None, f"Field '{key}' must be a non-empty string."
            parsed[key] = value.strip()

    if {"contract_start", "contract_end"} <= parsed.keys():
        if parsed["contract_end"] < parsed["contract_start"]:
            return None, "Field 'contract_end' must be on or after 'contract_start'."

    return parsed, None


@main_bp.get("/customers")
def get_customers():
    try:
        customers = Customer.query.order_by(Customer.id.asc()).all()
    except SQLAlchemyError:
        return error_response("Failed to fetch customers.", status_code=500)

    return jsonify([customer_to_dict(customer) for customer in customers]), 200


@main_bp.post("/customers")
def create_customer():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error_response("Request body must be valid JSON.")

    parsed_payload, validation_error = parse_customer_payload(payload)
    if validation_error:
        return error_response(validation_error)

    customer = Customer(**parsed_payload)

    try:
        db.session.add(customer)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return error_response("Failed to create customer.", status_code=500)

    return jsonify(customer_to_dict(customer)), 201


@main_bp.put("/customers/<int:customer_id>")
def update_customer(customer_id: int):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error_response("Request body must be valid JSON.")

    updatable_fields = set(payload.keys()) & CUSTOMER_FIELDS
    if not updatable_fields:
        return error_response("No valid customer fields provided for update.")

    parsed_payload, validation_error = parse_customer_payload(payload, partial=True)
    if validation_error:
        return error_response(validation_error)

    try:
        customer = db.session.get(Customer, customer_id)
        if customer is None:
            return error_response("Customer not found.", status_code=404)

        for field_name, field_value in parsed_payload.items():
            setattr(customer, field_name, field_value)

        if customer.contract_end < customer.contract_start:
            return error_response(
                "Field 'contract_end' must be on or after 'contract_start'."
            )

        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return error_response("Failed to update customer.", status_code=500)

    return jsonify(customer_to_dict(customer)), 200


@main_bp.delete("/customers/<int:customer_id>")
def delete_customer(customer_id: int):
    try:
        customer = db.session.get(Customer, customer_id)
        if customer is None:
            return error_response("Customer not found.", status_code=404)

        db.session.delete(customer)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return error_response("Failed to delete customer.", status_code=500)

    return jsonify({"message": "Customer deleted successfully."}), 200


@main_bp.get("/customers/<int:customer_id>/health-score")
def get_customer_health_score(customer_id: int):
    try:
        customer = db.session.get(Customer, customer_id)
        if customer is None:
            return error_response("Customer not found.", status_code=404)

        score = calculate_customer_health_score(customer)
    except SQLAlchemyError:
        return error_response("Failed to calculate customer health score.", status_code=500)

    return jsonify({"customer_id": customer_id, "health_score": score}), 200


@main_bp.get("/customers/<int:customer_id>/churn-risk")
def get_customer_churn_risk(customer_id: int):
    try:
        customer = (
            db.session.query(Customer)
            .options(selectinload(Customer.tickets))
            .filter(Customer.id == customer_id)
            .one_or_none()
        )
        if customer is None:
            return error_response("Customer not found.", status_code=404)

        prediction = predict_customer_churn_risk(customer)
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except SQLAlchemyError:
        return error_response("Failed to calculate customer churn risk.", status_code=500)

    return (
        jsonify(
            {
                "customer_id": customer.id,
                "churn_probability": prediction["churn_probability"],
                "explanation": prediction["explanation"],
            }
        ),
        200,
    )


@main_bp.get("/customers/<int:customer_id>/email-summary")
def get_customer_email_summary(customer_id: int):
    try:
        customer = (
            db.session.query(Customer)
            .options(selectinload(Customer.tickets))
            .filter(Customer.id == customer_id)
            .one_or_none()
        )
        if customer is None:
            return error_response("Customer not found.", status_code=404)

        summary_text = generate_customer_email_summary(customer)
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except RuntimeError as exc:
        return error_response(str(exc), status_code=500)
    except SQLAlchemyError:
        return error_response("Failed to generate customer email summary.", status_code=500)

    return Response(summary_text, mimetype="text/plain"), 200
