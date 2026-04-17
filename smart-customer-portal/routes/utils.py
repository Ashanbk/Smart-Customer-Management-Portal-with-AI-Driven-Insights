from __future__ import annotations

from typing import Any

from flask import jsonify


def error_response(message: str, status_code: int = 400, details: Any | None = None):
    payload = {"error": message}
    if details is not None:
        payload["details"] = details
    return jsonify(payload), status_code
