import argparse
import random
from datetime import datetime, timedelta

from faker import Faker

from app import create_app
from models import Customer, Device, Ticket, db

SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"]
TICKET_STATUSES = ["Open", "In Progress", "Resolved", "Closed"]
PLAN_TIERS = ["Starter", "Growth", "Business", "Enterprise"]
REGIONS = ["North America", "Europe", "APAC", "LATAM", "MEA"]
DEVICE_TYPES = [
    "IoT Gateway",
    "Smart Sensor",
    "Edge Router",
    "Controller Unit",
    "Monitoring Node",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate sample customers, tickets, and devices into SQLite."
    )
    parser.add_argument(
        "--customers",
        type=int,
        default=220,
        help="Number of customers to create (default: 220).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop existing tables before generating data.",
    )
    return parser.parse_args()


def random_contract_dates():
    today = datetime.utcnow().date()
    start = today - timedelta(days=random.randint(30, 1500))
    end = start + timedelta(days=random.randint(180, 1460))
    return start, end


def random_ticket_datetime(contract_start):
    start_dt = datetime.combine(contract_start, datetime.min.time())
    end_dt = datetime.utcnow()
    total_seconds = int((end_dt - start_dt).total_seconds())
    if total_seconds <= 0:
        return end_dt
    random_offset = random.randint(0, total_seconds)
    return start_dt + timedelta(seconds=random_offset)


def build_customer(fake: Faker):
    contract_start, contract_end = random_contract_dates()
    customer = Customer(
        company_name=fake.company(),
        region=random.choice(REGIONS),
        plan_tier=random.choice(PLAN_TIERS),
        contract_start=contract_start,
        contract_end=contract_end,
        nps_score=random.randint(-100, 100),
        monthly_usage=round(random.uniform(100.0, 50000.0), 2),
    )

    ticket_count = random.randint(1, 6)
    for _ in range(ticket_count):
        customer.tickets.append(
            Ticket(
                severity=random.choice(SEVERITY_LEVELS),
                status=random.choice(TICKET_STATUSES),
                created_at=random_ticket_datetime(contract_start),
            )
        )

    device_count = random.randint(1, 4)
    selected_device_types = random.sample(
        DEVICE_TYPES,
        k=min(device_count, len(DEVICE_TYPES)),
    )
    for device_type in selected_device_types:
        customer.devices.append(
            Device(
                device_type=device_type,
                count=random.randint(1, 300),
            )
        )

    return customer


def generate_customers(customer_total: int = 220):
    fake = Faker()
    customers = [build_customer(fake) for _ in range(customer_total)]
    db.session.add_all(customers)
    db.session.commit()
    print(
        f"Data generation complete: inserted {customer_total} customers "
        f"(with tickets and devices)."
    )


def seed_data(customer_total: int, reset: bool):
    app = create_app()

    with app.app_context():
        if reset:
            db.drop_all()

        db.create_all()
        generate_customers(customer_total)


if __name__ == "__main__":
    args = parse_args()
    if args.customers < 200:
        raise ValueError("Please provide --customers value >= 200.")
    seed_data(customer_total=args.customers, reset=args.reset)
