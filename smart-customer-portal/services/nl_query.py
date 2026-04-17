from __future__ import annotations

import os
import re
from datetime import date, datetime
from decimal import Decimal
from threading import Lock
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from models import db

ALLOWED_TABLES = {"customers", "tickets", "devices"}
DISALLOWED_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "replace",
    "truncate",
    "attach",
    "detach",
    "pragma",
    "vacuum",
    "reindex",
    "grant",
    "revoke",
    "commit",
    "rollback",
    "savepoint",
}
MAX_RESULT_ROWS = 200

SCHEMA_DESCRIPTION = """
SQLite schema:
- customers(id, company_name, region, plan_tier, contract_start, contract_end, nps_score, monthly_usage)
- tickets(id, customer_id, severity, status, created_at)
- devices(id, customer_id, device_type, count)

Join keys:
- tickets.customer_id = customers.id
- devices.customer_id = customers.id
""".strip()

_CONTEXT_LOCK = Lock()
_LAST_CONTEXT: dict[str, str | None] = {"query": None, "sql_query": None}


def _get_openai_client():
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI package not installed. Install dependencies from requirements.txt."
        ) from exc

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    return OpenAI(api_key=api_key)


def _get_previous_context() -> dict[str, str | None]:
    with _CONTEXT_LOCK:
        return {"query": _LAST_CONTEXT["query"], "sql_query": _LAST_CONTEXT["sql_query"]}


def _set_previous_context(query: str, sql_query: str):
    with _CONTEXT_LOCK:
        _LAST_CONTEXT["query"] = query
        _LAST_CONTEXT["sql_query"] = sql_query


def _extract_sql(response_text: str) -> str:
    sql = response_text.strip()
    if sql.startswith("```"):
        sql = re.sub(r"^```(?:sql)?", "", sql, flags=re.IGNORECASE).strip()
        if sql.endswith("```"):
            sql = sql[:-3].strip()
    return sql


def _generate_sql_from_nl(user_query: str) -> tuple[str, bool]:
    client = _get_openai_client()
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    context = _get_previous_context()
    has_previous_context = bool(context["query"] and context["sql_query"])
    context_block = (
        (
            f"Previous user query: {context['query']}\n"
            f"Previous SQL query: {context['sql_query']}\n"
            "Use this only when the new query is a follow-up."
        )
        if has_previous_context
        else "No previous query context."
    )

    system_prompt = (
        "You convert natural language to safe SQLite SQL.\n"
        "Rules:\n"
        "1) Return exactly one SQL SELECT statement.\n"
        "2) No markdown, no explanations, no comments.\n"
        "3) Use only tables and columns from the provided schema.\n"
        "4) No DDL or DML operations."
    )

    user_prompt = (
        f"{SCHEMA_DESCRIPTION}\n\n"
        f"{context_block}\n\n"
        f"Natural language query:\n{user_query}"
    )

    try:
        completion = client.chat.completions.create(
            model=model_name,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Failed to generate SQL from OpenAI.") from exc

    message = completion.choices[0].message.content if completion.choices else None
    if not message:
        raise RuntimeError("OpenAI did not return SQL text.")

    return _extract_sql(message), has_previous_context


def _validate_and_finalize_sql(sql_query: str) -> str:
    sql = sql_query.strip().rstrip(";").strip()
    if not sql:
        raise ValueError("Generated SQL was empty.")
    if ";" in sql:
        raise ValueError("Generated SQL must be a single statement.")
    if "--" in sql or "/*" in sql or "*/" in sql:
        raise ValueError("Generated SQL contains disallowed comments.")

    normalized = re.sub(r"\s+", " ", sql.lower())
    if not normalized.startswith("select "):
        raise ValueError("Only SELECT queries are allowed.")

    keyword_pattern = r"\b(" + "|".join(sorted(DISALLOWED_KEYWORDS)) + r")\b"
    if re.search(keyword_pattern, normalized):
        raise ValueError("Generated SQL contains disallowed operations.")

    referenced_tables = re.findall(r"\b(?:from|join)\s+([a-z_][a-z0-9_]*)", normalized)
    invalid_tables = sorted({table for table in referenced_tables if table not in ALLOWED_TABLES})
    if invalid_tables:
        raise ValueError(
            "Generated SQL references disallowed tables: " + ", ".join(invalid_tables)
        )

    if " limit " not in f" {normalized} ":
        sql = f"{sql} LIMIT {MAX_RESULT_ROWS}"

    return sql


def _serialize_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _execute_sql_query(sql_query: str) -> list[dict[str, Any]]:
    try:
        result = db.session.execute(text(sql_query))
        rows = result.mappings().all()
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise RuntimeError("Generated SQL failed during execution.") from exc

    serialized_rows: list[dict[str, Any]] = []
    for row in rows:
        serialized_rows.append({key: _serialize_value(value) for key, value in row.items()})
    return serialized_rows


def run_nl_query(user_query: str) -> dict[str, Any]:
    clean_query = user_query.strip()
    if not clean_query:
        raise ValueError("Field 'query' must be a non-empty string.")

    generated_sql, used_previous_context = _generate_sql_from_nl(clean_query)
    safe_sql = _validate_and_finalize_sql(generated_sql)
    results = _execute_sql_query(safe_sql)

    _set_previous_context(query=clean_query, sql_query=safe_sql)
    return {
        "query": clean_query,
        "sql_query": safe_sql,
        "used_previous_context": used_previous_context,
        "row_count": len(results),
        "results": results,
    }
