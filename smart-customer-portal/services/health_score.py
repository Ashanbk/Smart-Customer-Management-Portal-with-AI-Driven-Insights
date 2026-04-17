from __future__ import annotations

from datetime import date

from models import Customer

MAX_USAGE_BASELINE = 50000.0
MAX_TICKET_COUNT = 20


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def calculate_customer_health_score(customer: Customer) -> int:
    nps_normalized = (clamp(float(customer.nps_score), -100.0, 100.0) + 100.0) / 200.0
    nps_component = nps_normalized * 35.0

    usage_normalized = clamp(float(customer.monthly_usage), 0.0, MAX_USAGE_BASELINE) / MAX_USAGE_BASELINE
    usage_component = usage_normalized * 30.0

    ticket_count = len(customer.tickets)
    ticket_ratio = clamp(float(ticket_count), 0.0, float(MAX_TICKET_COUNT)) / float(MAX_TICKET_COUNT)
    ticket_component = (1.0 - ticket_ratio) * 20.0

    days_until_expiry = (customer.contract_end - date.today()).days
    if days_until_expiry <= 0:
        contract_component = 0.0
    elif days_until_expiry <= 30:
        contract_component = 2.0
    elif days_until_expiry <= 90:
        contract_component = 8.0
    elif days_until_expiry <= 180:
        contract_component = 12.0
    else:
        contract_component = 15.0

    score = nps_component + usage_component + ticket_component + contract_component
    return int(round(clamp(score, 0.0, 100.0)))
