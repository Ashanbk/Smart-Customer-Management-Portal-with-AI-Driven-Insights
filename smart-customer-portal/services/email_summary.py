from __future__ import annotations

from collections import Counter
from datetime import date

from models import Customer

from .churn_prediction import predict_customer_churn_risk
from .health_score import calculate_customer_health_score


def _health_band(score: int) -> str:
    if score >= 75:
        return "Strong"
    if score >= 50:
        return "Moderate"
    return "Weak"


def _churn_band(probability: float) -> str:
    if probability >= 0.65:
        return "High"
    if probability >= 0.40:
        return "Medium"
    return "Low"


def _build_recommendation(
    health_score: int,
    churn_probability: float,
    open_tickets: int,
    contract_days_left: int,
) -> str:
    if churn_probability >= 0.65 or health_score < 45:
        return (
            "Schedule an urgent customer success review in the next 7 days, "
            "prioritize open support issues, and align on a retention plan."
        )
    if churn_probability >= 0.40 or health_score < 65:
        return (
            "Run a proactive check-in this month, review usage expansion opportunities, "
            "and monitor support turnaround for unresolved tickets."
        )
    if contract_days_left <= 90:
        return (
            "Customer is stable but contract is nearing expiry. Start renewal discussions "
            "with a value recap and roadmap walkthrough."
        )
    if open_tickets > 0:
        return (
            "Customer health is good. Keep momentum by closing remaining tickets quickly "
            "and sharing progress updates."
        )
    return (
        "Customer is healthy. Continue regular engagement and identify cross-sell or "
        "upsell opportunities based on current usage."
    )


def generate_customer_email_summary(customer: Customer) -> str:
    health_score = calculate_customer_health_score(customer)
    churn_prediction = predict_customer_churn_risk(customer)
    churn_probability = float(churn_prediction["churn_probability"])
    churn_probability_pct = churn_probability * 100.0

    tickets = list(customer.tickets)
    ticket_count = len(tickets)
    contract_days_left = (customer.contract_end - date.today()).days

    status_counter = Counter(ticket.status for ticket in tickets)
    severity_counter = Counter(ticket.severity for ticket in tickets)
    open_tickets = status_counter.get("Open", 0) + status_counter.get("In Progress", 0)

    latest_ticket = max(tickets, key=lambda ticket: ticket.created_at) if tickets else None

    top_factors = churn_prediction["explanation"]["top_factors"][:2]
    factor_summary = ", ".join(
        f"{factor['label']} ({factor['direction']})" for factor in top_factors
    )
    if not factor_summary:
        factor_summary = "No dominant churn factors identified."

    recommendation = _build_recommendation(
        health_score=health_score,
        churn_probability=churn_probability,
        open_tickets=open_tickets,
        contract_days_left=contract_days_left,
    )

    lines = [
        "Customer Email Summary",
        "======================",
        f"Customer: {customer.company_name}",
        f"Region: {customer.region}",
        f"Plan Tier: {customer.plan_tier}",
        "",
        "Account Signals",
        "---------------",
        f"Health Score: {health_score}/100 ({_health_band(health_score)})",
        f"Churn Risk: {churn_probability_pct:.1f}% ({_churn_band(churn_probability)})",
        f"Churn Drivers: {factor_summary}",
        f"Contract Days Left: {contract_days_left}",
        "",
        "Ticket Overview",
        "---------------",
        f"Total Tickets: {ticket_count}",
        (
            "Status Breakdown: "
            f"Open={status_counter.get('Open', 0)}, "
            f"In Progress={status_counter.get('In Progress', 0)}, "
            f"Resolved={status_counter.get('Resolved', 0)}, "
            f"Closed={status_counter.get('Closed', 0)}"
        ),
        (
            "Severity Breakdown: "
            f"Critical={severity_counter.get('Critical', 0)}, "
            f"High={severity_counter.get('High', 0)}, "
            f"Medium={severity_counter.get('Medium', 0)}, "
            f"Low={severity_counter.get('Low', 0)}"
        ),
    ]

    if latest_ticket is not None:
        lines.append(
            "Latest Ticket: "
            f"#{latest_ticket.id} | {latest_ticket.status} | "
            f"{latest_ticket.severity} | {latest_ticket.created_at.isoformat()}"
        )
    else:
        lines.append("Latest Ticket: No tickets found.")

    lines.extend(
        [
            "",
            "Recommendation",
            "--------------",
            recommendation,
        ]
    )

    return "\n".join(lines)
