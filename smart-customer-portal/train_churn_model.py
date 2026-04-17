from app import create_app
from services import train_and_store_churn_model


def main():
    app = create_app()
    with app.app_context():
        payload = train_and_store_churn_model()

    print(
        "Churn model trained and stored successfully. "
        f"Samples used: {payload['sample_count']}."
    )


if __name__ == "__main__":
    main()
