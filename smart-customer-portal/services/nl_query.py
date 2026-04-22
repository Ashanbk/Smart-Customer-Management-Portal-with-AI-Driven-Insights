from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from threading import Lock
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
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
MIN_INTENT_CONFIDENCE = 0.15

SCHEMA_DESCRIPTION = """
SQLite schema:
- customers(id, company_name, region, plan_tier, contract_start, contract_end, nps_score, monthly_usage)
- tickets(id, customer_id, severity, status, created_at)
- devices(id, customer_id, device_type, count)

Join keys:
- tickets.customer_id = customers.id
- devices.customer_id = customers.id
""".strip()

INTENT_TRAINING_SAMPLES: dict[str, list[str]] = {
    "portfolio_summary": [
        "show summary metrics",
        "give me dashboard numbers",
        "overall business metrics",
        "how many customers tickets and devices",
        "account portfolio overview",
        "show total counts",
        "quick summary of data",
        "high level KPI summary",
        "how many customers do we have",
        "total customers tickets devices",
        "show me the overall numbers",
        "what is our customer count",
        "business overview",
        "portfolio stats",
    ],
    "customers_by_region": [
        "show customers in europe",
        "customers from apac",
        "list accounts by region",
        "who are our north america customers",
        "region wise customer list",
        "customers in latam",
        "show me customers by region",
        "list customers in mea",
        "european customers",
        "asia pacific accounts",
        "north american customers",
        "show customers from region",
        "which customers are in europe",
    ],
    "customers_by_plan": [
        "show enterprise customers",
        "customers on business plan",
        "list accounts by plan tier",
        "who is on starter plan",
        "customers with growth subscription",
        "plan wise customer list",
        "show customers by plan",
        "enterprise tier accounts",
        "what plans do customers have",
        "show all business tier customers",
        "list growth plan accounts",
    ],
    "tickets_by_status": [
        "show open tickets",
        "list resolved tickets",
        "tickets in progress",
        "ticket status report",
        "give me closed tickets",
        "unresolved support tickets",
        "how many tickets by status",
        "status wise tickets",
        "pending tickets",
        "completed tickets",
        "show me all open issues",
    ],
    "tickets_by_severity": [
        "show critical tickets",
        "high severity tickets",
        "low priority support issues",
        "tickets by severity",
        "list medium severity tickets",
        "severity wise ticket report",
        "show sev1 tickets",
        "critical support incidents",
        "p1 tickets",
        "priority tickets",
        "show all high priority issues",
    ],
    "contracts_expiring": [
        "contracts expiring soon",
        "show renewals in next 90 days",
        "which customers have contract ending soon",
        "customers with upcoming contract expiry",
        "who is expiring in 30 days",
        "contract end report",
        "renewal pipeline",
        "list contracts ending next quarter",
        "upcoming renewals",
        "which contracts need renewal",
        "show expiring contracts",
    ],
    "top_churn_risk": [
        "top churn risk customers",
        "who is most likely to churn",
        "show customers at risk",
        "highest churn probability accounts",
        "customers likely to leave",
        "top 10 risky customers",
        "churn prediction list",
        "at risk customer ranking",
        "show me customers about to leave",
        "which customers might cancel",
    ],
    "top_health_scores": [
        "top healthy customers",
        "best customer health score",
        "show account health ranking",
        "customers with highest health",
        "health score leaderboard",
        "top performing customers",
        "best customer wellness score",
        "healthy account list",
        "most satisfied customers",
        "customers in good standing",
    ],
    "device_inventory": [
        "device inventory summary",
        "show devices by type",
        "how many iot gateways",
        "list customer devices",
        "device count report",
        "show router devices",
        "hardware inventory by device",
        "edge router usage",
        "what devices do we have",
        "device breakdown",
    ],
}

REGION_SYNONYMS: dict[str, list[str]] = {
    "north america": ["north america", "na", "usa", "us", "canada"],
    "europe": ["europe", "eu", "european"],
    "apac": ["apac", "asia pacific", "asia"],
    "latam": ["latam", "latin america"],
    "mea": ["mea", "middle east", "africa", "middle east africa"],
}

PLAN_SYNONYMS: dict[str, list[str]] = {
    "starter": ["starter", "basic"],
    "growth": ["growth", "pro", "professional"],
    "business": ["business", "biz"],
    "enterprise": ["enterprise", "premium", "corporate"],
}

STATUS_SYNONYMS: dict[str, list[str]] = {
    "open": ["open", "unresolved", "new"],
    "in progress": ["in progress", "progress", "wip", "working"],
    "resolved": ["resolved", "fixed", "done"],
    "closed": ["closed", "completed"],
}

SEVERITY_SYNONYMS: dict[str, list[str]] = {
    "critical": ["critical", "sev1", "p1"],
    "high": ["high", "sev2", "p2"],
    "medium": ["medium", "sev3", "p3"],
    "low": ["low", "minor", "sev4", "p4"],
}

DEVICE_SYNONYMS: dict[str, list[str]] = {
    "iot gateway": ["iot gateway", "gateway"],
    "smart sensor": ["smart sensor", "sensor"],
    "edge router": ["edge router", "router"],
    "controller unit": ["controller unit", "controller"],
    "monitoring node": ["monitoring node", "monitor"],
}

FOLLOW_UP_PREFIXES = (
    "what about",
    "how about",
    "and",
    "also",
    "same",
    "for",
    "only",
)

_CONTEXT_LOCK = Lock()
_LAST_CONTEXT: dict[str, Any] = {
    "query": None,
    "sql_query": None,
    "intent": None,
    "params": None,
}

_MODEL_LOCK = Lock()
_INTENT_MODEL: Pipeline | None = None


@dataclass(frozen=True)
class QueryPlan:
    intent: str
    sql_query: str
    params: dict[str, Any]
    used_previous_context: bool


def _normalize_text(value: str) -> str:
    lowered = value.lower().replace("-", " ")
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _build_follow_up_terms() -> set[str]:
    terms: set[str] = set()
    synonym_maps = (
        REGION_SYNONYMS,
        PLAN_SYNONYMS,
        STATUS_SYNONYMS,
        SEVERITY_SYNONYMS,
        DEVICE_SYNONYMS,
    )
    for synonym_map in synonym_maps:
        for patterns in synonym_map.values():
            for pattern in patterns:
                terms.update(_normalize_text(pattern).split())

    terms.update(
        {
            "customer",
            "customers",
            "ticket",
            "tickets",
            "device",
            "devices",
            "contract",
            "contracts",
            "expiring",
            "renewal",
            "summary",
            "metrics",
            "health",
            "churn",
        }
    )
    return terms


FOLLOW_UP_ENTITY_TERMS = _build_follow_up_terms()


def _looks_like_follow_up(query: str) -> bool:
    normalized = _normalize_text(query)
    if not normalized:
        return False

    if any(normalized.startswith(prefix) for prefix in FOLLOW_UP_PREFIXES):
        return True

    tokens = normalized.split()
    return len(tokens) <= 3 and any(token in FOLLOW_UP_ENTITY_TERMS for token in tokens)


def _extract_enum_value(query: str, synonyms: dict[str, list[str]]) -> str | None:
    normalized_query = f" {_normalize_text(query)} "
    for canonical, patterns in synonyms.items():
        for pattern in patterns:
            normalized_pattern = _normalize_text(pattern)
            if not normalized_pattern:
                continue
            token = f" {normalized_pattern} "
            if token in normalized_query:
                return canonical
    return None


def _extract_result_limit(query: str, default_limit: int = 25) -> int:
    patterns = [
        r"\btop\s+(\d{1,3})\b",
        r"\bfirst\s+(\d{1,3})\b",
        r"\blimit\s+(\d{1,3})\b",
        r"\b(\d{1,3})\s+(?:rows|records|customers|tickets|devices)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, query, flags=re.IGNORECASE)
        if match:
            return max(1, min(int(match.group(1)), MAX_RESULT_ROWS))
    return max(1, min(default_limit, MAX_RESULT_ROWS))


def _extract_days_window(query: str, default_days: int = 90) -> int:
    patterns = [
        r"\bnext\s+(\d{1,4})\s+days?\b",
        r"\bwithin\s+(\d{1,4})\s+days?\b",
        r"\bin\s+(\d{1,4})\s+days?\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, query, flags=re.IGNORECASE)
        if match:
            return max(1, min(int(match.group(1)), 3650))
    return max(1, min(default_days, 3650))


def _train_intent_model() -> Pipeline:
    corpus: list[str] = []
    labels: list[str] = []
    for intent, examples in INTENT_TRAINING_SAMPLES.items():
        for example in examples:
            corpus.append(example)
            labels.append(intent)

    model = Pipeline(
        steps=[
            ("vectorizer", TfidfVectorizer(ngram_range=(1, 2), lowercase=True)),
            ("classifier", LogisticRegression(max_iter=2000, random_state=42)),
        ]
    )
    model.fit(corpus, labels)
    return model


def _get_intent_model() -> Pipeline:
    global _INTENT_MODEL
    if _INTENT_MODEL is not None:
        return _INTENT_MODEL

    with _MODEL_LOCK:
        if _INTENT_MODEL is None:
            _INTENT_MODEL = _train_intent_model()

    return _INTENT_MODEL


def _predict_intent(user_query: str) -> tuple[str, float]:
    model = _get_intent_model()
    probabilities = model.predict_proba([user_query])[0]
    classes = model.named_steps["classifier"].classes_
    best_index = int(probabilities.argmax())
    return str(classes[best_index]), float(probabilities[best_index])


def _openai_is_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


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


def _get_previous_context() -> dict[str, Any]:
    with _CONTEXT_LOCK:
        params = _LAST_CONTEXT["params"]
        copied_params = dict(params) if isinstance(params, dict) else None
        return {
            "query": _LAST_CONTEXT["query"],
            "sql_query": _LAST_CONTEXT["sql_query"],
            "intent": _LAST_CONTEXT["intent"],
            "params": copied_params,
        }


def _set_previous_context(
    query: str,
    sql_query: str,
    intent: str | None,
    params: dict[str, Any] | None,
):
    with _CONTEXT_LOCK:
        _LAST_CONTEXT["query"] = query
        _LAST_CONTEXT["sql_query"] = sql_query
        _LAST_CONTEXT["intent"] = intent
        _LAST_CONTEXT["params"] = dict(params) if isinstance(params, dict) else None


def _extract_sql(response_text: str) -> str:
    sql = response_text.strip()
    if sql.startswith("```"):
        sql = re.sub(r"^```(?:sql)?", "", sql, flags=re.IGNORECASE).strip()
        if sql.endswith("```"):
            sql = sql[:-3].strip()
    return sql


def _generate_sql_from_openai(user_query: str) -> tuple[str, bool]:
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


def _build_ml_query_plan(user_query: str, previous_context: dict[str, Any]) -> tuple[QueryPlan | None, float]:
    predicted_intent, confidence = _predict_intent(user_query)

    resolved_intent = predicted_intent
    used_previous_context = False
    previous_intent = previous_context.get("intent")
    previous_params = previous_context.get("params")
    if not isinstance(previous_params, dict):
        previous_params = {}

    if confidence < MIN_INTENT_CONFIDENCE:
        if previous_intent and _looks_like_follow_up(user_query):
            resolved_intent = str(previous_intent)
            used_previous_context = True
        else:
            return None, confidence

    limit = _extract_result_limit(user_query)

    if resolved_intent == "portfolio_summary":
        return (
            QueryPlan(
                intent=resolved_intent,
                sql_query=(
                    "SELECT "
                    "(SELECT COUNT(*) FROM customers) AS customer_count, "
                    "(SELECT COUNT(*) FROM tickets) AS ticket_count, "
                    "(SELECT COUNT(*) FROM devices) AS device_row_count, "
                    "(SELECT ROUND(AVG(nps_score), 2) FROM customers) AS average_nps_score, "
                    "(SELECT ROUND(AVG(monthly_usage), 2) FROM customers) AS average_monthly_usage"
                ),
                params={},
                used_previous_context=used_previous_context,
            ),
            confidence,
        )

    if resolved_intent == "customers_by_region":
        region = _extract_enum_value(user_query, REGION_SYNONYMS)
        if region is None and used_previous_context:
            previous_region = previous_params.get("region")
            if isinstance(previous_region, str):
                region = previous_region

        if region is None:
            return (
                QueryPlan(
                    intent=resolved_intent,
                    sql_query=(
                        "SELECT region, COUNT(*) AS customer_count, "
                        "ROUND(AVG(nps_score), 2) AS average_nps_score "
                        "FROM customers "
                        "GROUP BY region "
                        "ORDER BY customer_count DESC "
                        "LIMIT :result_limit"
                    ),
                    params={"result_limit": limit},
                    used_previous_context=used_previous_context,
                ),
                confidence,
            )

        return (
            QueryPlan(
                intent=resolved_intent,
                sql_query=(
                    "SELECT id, company_name, region, plan_tier, nps_score, monthly_usage "
                    "FROM customers "
                    "WHERE lower(region) = :region "
                    "ORDER BY monthly_usage DESC "
                    "LIMIT :result_limit"
                ),
                params={"region": region, "result_limit": limit},
                used_previous_context=used_previous_context,
            ),
            confidence,
        )

    if resolved_intent == "customers_by_plan":
        plan_tier = _extract_enum_value(user_query, PLAN_SYNONYMS)
        if plan_tier is None and used_previous_context:
            previous_plan = previous_params.get("plan_tier")
            if isinstance(previous_plan, str):
                plan_tier = previous_plan

        if plan_tier is None:
            return (
                QueryPlan(
                    intent=resolved_intent,
                    sql_query=(
                        "SELECT plan_tier, COUNT(*) AS customer_count, "
                        "ROUND(AVG(nps_score), 2) AS average_nps_score "
                        "FROM customers "
                        "GROUP BY plan_tier "
                        "ORDER BY customer_count DESC "
                        "LIMIT :result_limit"
                    ),
                    params={"result_limit": limit},
                    used_previous_context=used_previous_context,
                ),
                confidence,
            )

        return (
            QueryPlan(
                intent=resolved_intent,
                sql_query=(
                    "SELECT id, company_name, region, plan_tier, nps_score, monthly_usage "
                    "FROM customers "
                    "WHERE lower(plan_tier) = :plan_tier "
                    "ORDER BY nps_score DESC "
                    "LIMIT :result_limit"
                ),
                params={"plan_tier": plan_tier, "result_limit": limit},
                used_previous_context=used_previous_context,
            ),
            confidence,
        )

    if resolved_intent == "tickets_by_status":
        status = _extract_enum_value(user_query, STATUS_SYNONYMS)
        if status is None and used_previous_context:
            previous_status = previous_params.get("status")
            if isinstance(previous_status, str):
                status = previous_status

        if status is None:
            return (
                QueryPlan(
                    intent=resolved_intent,
                    sql_query=(
                        "SELECT status, COUNT(*) AS ticket_count "
                        "FROM tickets "
                        "GROUP BY status "
                        "ORDER BY ticket_count DESC "
                        "LIMIT :result_limit"
                    ),
                    params={"result_limit": limit},
                    used_previous_context=used_previous_context,
                ),
                confidence,
            )

        return (
            QueryPlan(
                intent=resolved_intent,
                sql_query=(
                    "SELECT t.id, t.customer_id, c.company_name, t.severity, t.status, t.created_at "
                    "FROM tickets AS t "
                    "JOIN customers AS c ON c.id = t.customer_id "
                    "WHERE lower(t.status) = :status "
                    "ORDER BY t.created_at DESC "
                    "LIMIT :result_limit"
                ),
                params={"status": status, "result_limit": limit},
                used_previous_context=used_previous_context,
            ),
            confidence,
        )

    if resolved_intent == "tickets_by_severity":
        severity = _extract_enum_value(user_query, SEVERITY_SYNONYMS)
        if severity is None and used_previous_context:
            previous_severity = previous_params.get("severity")
            if isinstance(previous_severity, str):
                severity = previous_severity

        if severity is None:
            return (
                QueryPlan(
                    intent=resolved_intent,
                    sql_query=(
                        "SELECT severity, COUNT(*) AS ticket_count "
                        "FROM tickets "
                        "GROUP BY severity "
                        "ORDER BY ticket_count DESC "
                        "LIMIT :result_limit"
                    ),
                    params={"result_limit": limit},
                    used_previous_context=used_previous_context,
                ),
                confidence,
            )

        return (
            QueryPlan(
                intent=resolved_intent,
                sql_query=(
                    "SELECT t.id, t.customer_id, c.company_name, t.severity, t.status, t.created_at "
                    "FROM tickets AS t "
                    "JOIN customers AS c ON c.id = t.customer_id "
                    "WHERE lower(t.severity) = :severity "
                    "ORDER BY t.created_at DESC "
                    "LIMIT :result_limit"
                ),
                params={"severity": severity, "result_limit": limit},
                used_previous_context=used_previous_context,
            ),
            confidence,
        )

    if resolved_intent == "contracts_expiring":
        days_window = _extract_days_window(user_query)
        return (
            QueryPlan(
                intent=resolved_intent,
                sql_query=(
                    "SELECT id, company_name, region, plan_tier, contract_end, "
                    "CAST(julianday(contract_end) - julianday('now') AS INTEGER) AS days_left "
                    "FROM customers "
                    "WHERE date(contract_end) <= date('now', '+' || :days_window || ' days') "
                    "ORDER BY contract_end ASC "
                    "LIMIT :result_limit"
                ),
                params={"days_window": days_window, "result_limit": limit},
                used_previous_context=used_previous_context,
            ),
            confidence,
        )

    if resolved_intent == "top_churn_risk":
        top_n = _extract_result_limit(user_query, default_limit=10)
        return (
            QueryPlan(
                intent=resolved_intent,
                sql_query=(
                    "SELECT c.id, c.company_name, c.region, c.plan_tier, "
                    "COUNT(t.id) AS ticket_count, "
                    "ROUND(("
                    "(CASE WHEN c.nps_score < 0 THEN ABS(c.nps_score) / 100.0 ELSE 0 END) * 0.35 + "
                    "(CASE WHEN c.monthly_usage < 8000 THEN (8000 - c.monthly_usage) / 8000.0 ELSE 0 END) * 0.25 + "
                    "(MIN(COUNT(t.id), 10) / 10.0) * 0.25 + "
                    "(1.0 - (MIN(MAX(julianday(c.contract_end) - julianday('now'), 0), 365) / 365.0)) * 0.15"
                    "), 4) AS churn_risk_score "
                    "FROM customers AS c "
                    "LEFT JOIN tickets AS t ON t.customer_id = c.id "
                    "GROUP BY c.id "
                    "ORDER BY churn_risk_score DESC "
                    "LIMIT :result_limit"
                ),
                params={"result_limit": top_n},
                used_previous_context=used_previous_context,
            ),
            confidence,
        )

    if resolved_intent == "top_health_scores":
        top_n = _extract_result_limit(user_query, default_limit=10)
        return (
            QueryPlan(
                intent=resolved_intent,
                sql_query=(
                    "SELECT c.id, c.company_name, c.region, c.plan_tier, "
                    "COUNT(t.id) AS ticket_count, "
                    "ROUND(("
                    "((MIN(MAX(c.nps_score, -100), 100) + 100) / 200.0) * 35 + "
                    "(MIN(MAX(c.monthly_usage, 0), 50000) / 50000.0) * 30 + "
                    "(1.0 - (MIN(COUNT(t.id), 20) / 20.0)) * 20 + "
                    "(CASE "
                    "WHEN julianday(c.contract_end) - julianday('now') <= 0 THEN 0 "
                    "WHEN julianday(c.contract_end) - julianday('now') <= 30 THEN 2 "
                    "WHEN julianday(c.contract_end) - julianday('now') <= 90 THEN 8 "
                    "WHEN julianday(c.contract_end) - julianday('now') <= 180 THEN 12 "
                    "ELSE 15 END)"
                    "), 2) AS health_score "
                    "FROM customers AS c "
                    "LEFT JOIN tickets AS t ON t.customer_id = c.id "
                    "GROUP BY c.id "
                    "ORDER BY health_score DESC "
                    "LIMIT :result_limit"
                ),
                params={"result_limit": top_n},
                used_previous_context=used_previous_context,
            ),
            confidence,
        )

    if resolved_intent == "device_inventory":
        device_type = _extract_enum_value(user_query, DEVICE_SYNONYMS)
        if device_type is None and used_previous_context:
            previous_device_type = previous_params.get("device_type")
            if isinstance(previous_device_type, str):
                device_type = previous_device_type

        if device_type is None:
            return (
                QueryPlan(
                    intent=resolved_intent,
                    sql_query=(
                        "SELECT device_type, SUM(count) AS total_units, COUNT(*) AS customer_records "
                        "FROM devices "
                        "GROUP BY device_type "
                        "ORDER BY total_units DESC "
                        "LIMIT :result_limit"
                    ),
                    params={"result_limit": limit},
                    used_previous_context=used_previous_context,
                ),
                confidence,
            )

        return (
            QueryPlan(
                intent=resolved_intent,
                sql_query=(
                    "SELECT d.customer_id, c.company_name, d.device_type, d.count "
                    "FROM devices AS d "
                    "JOIN customers AS c ON c.id = d.customer_id "
                    "WHERE lower(d.device_type) = :device_type "
                    "ORDER BY d.count DESC "
                    "LIMIT :result_limit"
                ),
                params={"device_type": device_type, "result_limit": limit},
                used_previous_context=used_previous_context,
            ),
            confidence,
        )

    return None, confidence


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


def _execute_sql_query(sql_query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    execution_params = params if isinstance(params, dict) else {}
    try:
        result = db.session.execute(text(sql_query), execution_params)
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

    previous_context = _get_previous_context()
    ml_plan, intent_confidence = _build_ml_query_plan(clean_query, previous_context)

    if ml_plan is not None:
        safe_sql = _validate_and_finalize_sql(ml_plan.sql_query)
        results = _execute_sql_query(safe_sql, ml_plan.params)
        _set_previous_context(
            query=clean_query,
            sql_query=safe_sql,
            intent=ml_plan.intent,
            params=ml_plan.params,
        )
        return {
            "query": clean_query,
            "sql_query": safe_sql,
            "used_previous_context": ml_plan.used_previous_context,
            "row_count": len(results),
            "results": results,
            "query_mode": "ml_intent",
            "intent": ml_plan.intent,
            "query_type": ml_plan.intent,
            "intent_confidence": round(intent_confidence, 4),
        }

    if _openai_is_configured():
        generated_sql, used_previous_context = _generate_sql_from_openai(clean_query)
        safe_sql = _validate_and_finalize_sql(generated_sql)
        results = _execute_sql_query(safe_sql)

        _set_previous_context(query=clean_query, sql_query=safe_sql, intent=None, params=None)
        return {
            "query": clean_query,
            "sql_query": safe_sql,
            "used_previous_context": used_previous_context,
            "row_count": len(results),
            "results": results,
            "query_mode": "openai_sql",
            "intent": None,
            "query_type": None,
        }

    if _openai_is_configured():
        generated_sql, used_previous_context = _generate_sql_from_openai(clean_query)
        safe_sql = _validate_and_finalize_sql(generated_sql)
        results = _execute_sql_query(safe_sql)

        _set_previous_context(query=clean_query, sql_query=safe_sql, intent=None, params=None)
        return {
            "query": clean_query,
            "sql_query": safe_sql,
            "used_previous_context": used_previous_context,
            "row_count": len(results),
            "results": results,
            "query_mode": "openai_sql",
            "intent": None,
            "query_type": None,
        }

    # Fallback: Try keyword-based simple query matching
    fallback_result = _try_keyword_fallback(clean_query)
    if fallback_result is not None:
        return fallback_result

    raise ValueError(
        "Could not understand your query. Try examples like:\n"
        "• 'show customers in europe' - Filter customers by region\n"
        "• 'open tickets' - Show tickets by status\n"
        "• 'top 5 churn risk customers' - Show at-risk accounts\n"
        "• 'summary metrics' - Overall business numbers\n"
        "• 'contracts expiring soon' - Upcoming renewals"
    )


def _try_keyword_fallback(user_query: str) -> dict[str, Any] | None:
    """Simple keyword-based fallback for common queries."""
    query_lower = user_query.lower().strip()

    # Customer queries
    if any(kw in query_lower for kw in ["customer", "account", "company"]):
        if "region" in query_lower or any(r in query_lower for r in ["europe", "apac", "na", "latam", "mea", "america", "asia"]):
            region = None
            for r in ["europe", "apac", "north america", "latam", "mea"]:
                if r in query_lower:
                    region = r
                    break
            if region:
                sql = "SELECT id, company_name, region, plan_tier, nps_score, monthly_usage FROM customers WHERE lower(region) = :region ORDER BY monthly_usage DESC LIMIT 25"
                results = _execute_sql_query(sql, {"region": region})
                return {
                    "query": user_query,
                    "sql_query": sql,
                    "used_previous_context": False,
                    "row_count": len(results),
                    "results": results,
                    "query_mode": "keyword_fallback",
                    "intent": "customers_by_region",
                    "query_type": "customers_by_region",
                    "intent_confidence": 0.5,
                }

        if "plan" in query_lower or any(p in query_lower for p in ["enterprise", "business", "growth", "starter"]):
            plan = None
            for p in ["enterprise", "business", "growth", "starter"]:
                if p in query_lower:
                    plan = p
                    break
            if plan:
                sql = "SELECT id, company_name, region, plan_tier, nps_score, monthly_usage FROM customers WHERE lower(plan_tier) = :plan ORDER BY nps_score DESC LIMIT 25"
                results = _execute_sql_query(sql, {"plan": plan})
                return {
                    "query": user_query,
                    "sql_query": sql,
                    "used_previous_context": False,
                    "row_count": len(results),
                    "results": results,
                    "query_mode": "keyword_fallback",
                    "intent": "customers_by_plan",
                    "query_type": "customers_by_plan",
                    "intent_confidence": 0.5,
                }

        # Default: show all customers
        sql = "SELECT id, company_name, region, plan_tier, nps_score, monthly_usage FROM customers ORDER BY id LIMIT 25"
        results = _execute_sql_query(sql)
        return {
            "query": user_query,
            "sql_query": sql,
            "used_previous_context": False,
            "row_count": len(results),
            "results": results,
            "query_mode": "keyword_fallback",
            "intent": "all_customers",
            "query_type": "all_customers",
            "intent_confidence": 0.5,
        }

    # Ticket queries
    if "ticket" in query_lower:
        if "status" in query_lower or any(s in query_lower for s in ["open", "closed", "resolved", "progress"]):
            status = None
            for s in ["open", "closed", "resolved", "in progress"]:
                if s in query_lower:
                    status = s
                    break
            if status:
                sql = "SELECT t.id, t.customer_id, c.company_name, t.severity, t.status, t.created_at FROM tickets t JOIN customers c ON c.id = t.customer_id WHERE lower(t.status) = :status ORDER BY t.created_at DESC LIMIT 25"
                results = _execute_sql_query(sql, {"status": status})
                return {
                    "query": user_query,
                    "sql_query": sql,
                    "used_previous_context": False,
                    "row_count": len(results),
                    "results": results,
                    "query_mode": "keyword_fallback",
                    "intent": "tickets_by_status",
                    "query_type": "tickets_by_status",
                    "intent_confidence": 0.5,
                }

        if "severity" in query_lower or any(s in query_lower for s in ["critical", "high", "medium", "low", "p1", "p2"]):
            severity = None
            for s in ["critical", "high", "medium", "low"]:
                if s in query_lower:
                    severity = s
                    break
            if severity:
                sql = "SELECT t.id, t.customer_id, c.company_name, t.severity, t.status, t.created_at FROM tickets t JOIN customers c ON c.id = t.customer_id WHERE lower(t.severity) = :severity ORDER BY t.created_at DESC LIMIT 25"
                results = _execute_sql_query(sql, {"severity": severity})
                return {
                    "query": user_query,
                    "sql_query": sql,
                    "used_previous_context": False,
                    "row_count": len(results),
                    "results": results,
                    "query_mode": "keyword_fallback",
                    "intent": "tickets_by_severity",
                    "query_type": "tickets_by_severity",
                    "intent_confidence": 0.5,
                }

        # Default: show all tickets
        sql = "SELECT t.id, t.customer_id, c.company_name, t.severity, t.status, t.created_at FROM tickets t JOIN customers c ON c.id = t.customer_id ORDER BY t.created_at DESC LIMIT 25"
        results = _execute_sql_query(sql)
        return {
            "query": user_query,
            "sql_query": sql,
            "used_previous_context": False,
            "row_count": len(results),
            "results": results,
            "query_mode": "keyword_fallback",
            "intent": "all_tickets",
            "query_type": "all_tickets",
            "intent_confidence": 0.5,
        }

    # Summary/overview queries
    if any(kw in query_lower for kw in ["summary", "overview", "metrics", "total", "count", "dashboard", "kpi"]):
        sql = (
            "SELECT "
            "(SELECT COUNT(*) FROM customers) AS customer_count, "
            "(SELECT COUNT(*) FROM tickets) AS ticket_count, "
            "(SELECT COUNT(*) FROM devices) AS device_count, "
            "(SELECT ROUND(AVG(nps_score), 2) FROM customers) AS average_nps, "
            "(SELECT ROUND(AVG(monthly_usage), 2) FROM customers) AS average_usage"
        )
        results = _execute_sql_query(sql)
        return {
            "query": user_query,
            "sql_query": sql,
            "used_previous_context": False,
            "row_count": len(results),
            "results": results,
            "query_mode": "keyword_fallback",
            "intent": "portfolio_summary",
            "query_type": "portfolio_summary",
            "intent_confidence": 0.5,
        }

    # Churn risk queries
    if "churn" in query_lower or "risk" in query_lower:
        sql = (
            "SELECT c.id, c.company_name, c.region, c.plan_tier, "
            "COUNT(t.id) AS ticket_count, "
            "ROUND(("
            "(CASE WHEN c.nps_score < 0 THEN ABS(c.nps_score) / 100.0 ELSE 0 END) * 0.35 + "
            "(CASE WHEN c.monthly_usage < 8000 THEN (8000 - c.monthly_usage) / 8000.0 ELSE 0 END) * 0.25 + "
            "(MIN(COUNT(t.id), 10) / 10.0) * 0.25 + "
            "(1.0 - (MIN(MAX(julianday(c.contract_end) - julianday('now'), 0), 365) / 365.0)) * 0.15"
            "), 4) AS churn_risk_score "
            "FROM customers AS c "
            "LEFT JOIN tickets AS t ON t.customer_id = c.id "
            "GROUP BY c.id "
            "ORDER BY churn_risk_score DESC "
            "LIMIT 10"
        )
        results = _execute_sql_query(sql)
        return {
            "query": user_query,
            "sql_query": sql,
            "used_previous_context": False,
            "row_count": len(results),
            "results": results,
            "query_mode": "keyword_fallback",
            "intent": "top_churn_risk",
            "query_type": "top_churn_risk",
            "intent_confidence": 0.5,
        }

    # Health score queries
    if "health" in query_lower:
        sql = (
            "SELECT c.id, c.company_name, c.region, c.plan_tier, "
            "COUNT(t.id) AS ticket_count, "
            "ROUND(("
            "((MIN(MAX(c.nps_score, -100), 100) + 100) / 200.0) * 35 + "
            "(MIN(MAX(c.monthly_usage, 0), 50000) / 50000.0) * 30 + "
            "(1.0 - (MIN(COUNT(t.id), 20) / 20.0)) * 20 + "
            "(CASE "
            "WHEN julianday(c.contract_end) - julianday('now') <= 0 THEN 0 "
            "WHEN julianday(c.contract_end) - julianday('now') <= 30 THEN 2 "
            "WHEN julianday(c.contract_end) - julianday('now') <= 90 THEN 8 "
            "WHEN julianday(c.contract_end) - julianday('now') <= 180 THEN 12 "
            "ELSE 15 END)"
            "), 2) AS health_score "
            "FROM customers AS c "
            "LEFT JOIN tickets AS t ON t.customer_id = c.id "
            "GROUP BY c.id "
            "ORDER BY health_score DESC "
            "LIMIT 10"
        )
        results = _execute_sql_query(sql)
        return {
            "query": user_query,
            "sql_query": sql,
            "used_previous_context": False,
            "row_count": len(results),
            "results": results,
            "query_mode": "keyword_fallback",
            "intent": "top_health_scores",
            "query_type": "top_health_scores",
            "intent_confidence": 0.5,
        }

    # Contract expiry queries
    if "contract" in query_lower or "expir" in query_lower or "renewal" in query_lower:
        sql = (
            "SELECT id, company_name, region, plan_tier, contract_end, "
            "CAST(julianday(contract_end) - julianday('now') AS INTEGER) AS days_left "
            "FROM customers "
            "WHERE date(contract_end) <= date('now', '+90 days') "
            "ORDER BY contract_end ASC "
            "LIMIT 25"
        )
        results = _execute_sql_query(sql)
        return {
            "query": user_query,
            "sql_query": sql,
            "used_previous_context": False,
            "row_count": len(results),
            "results": results,
            "query_mode": "keyword_fallback",
            "intent": "contracts_expiring",
            "query_type": "contracts_expiring",
            "intent_confidence": 0.5,
        }

    # Device queries
    if "device" in query_lower or "iot" in query_lower or "router" in query_lower or "sensor" in query_lower:
        sql = "SELECT device_type, SUM(count) AS total_units, COUNT(*) AS customer_records FROM devices GROUP BY device_type ORDER BY total_units DESC LIMIT 25"
        results = _execute_sql_query(sql)
        return {
            "query": user_query,
            "sql_query": sql,
            "used_previous_context": False,
            "row_count": len(results),
            "results": results,
            "query_mode": "keyword_fallback",
            "intent": "device_inventory",
            "query_type": "device_inventory",
            "intent_confidence": 0.5,
        }

    return None
