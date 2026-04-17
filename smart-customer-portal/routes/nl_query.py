from __future__ import annotations

from flask import jsonify, request

from services import run_nl_query

from .main import main_bp
from .utils import error_response


@main_bp.post("/nl-query")
def nl_query():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error_response("Request body must be valid JSON.")

    query_text = payload.get("query")
    if not isinstance(query_text, str) or not query_text.strip():
        return error_response("Field 'query' must be a non-empty string.")

    try:
        response_payload = run_nl_query(query_text)
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except RuntimeError as exc:
        return error_response(str(exc), status_code=500)

    return jsonify(response_payload), 200
