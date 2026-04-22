import json
from datetime import date

import altair as alt
import pandas as pd
import requests
import streamlit as st
from requests.exceptions import RequestException

DEFAULT_API_URL = "http://127.0.0.1:5000"
REQUEST_TIMEOUT = 10

st.set_page_config(page_title="Customer Portal", layout="wide")


def apply_theme() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700&family=Manrope:wght@400;500;700&display=swap');

            :root {
                --bg-deep: #040a11;
                --bg-mid: #0b1d2d;
                --glass: rgba(5, 20, 32, 0.70);
                --stroke: rgba(75, 205, 255, 0.45);
                --mint: #38f2b4;
                --text-main: #e8f7ff;
                --text-soft: #9bc4d9;
            }

            /* Fix main content visibility */
            .main .block-container {
                padding-top: 2rem;
                padding-bottom: 2rem;
                padding-left: 1.5rem;
                padding-right: 1.5rem;
                max-width: 100%;
            }

            .stApp {
                background:
                    radial-gradient(circle at 12% 8%, rgba(49, 217, 255, 0.16), transparent 28%),
                    radial-gradient(circle at 88% 16%, rgba(56, 242, 180, 0.12), transparent 30%),
                    linear-gradient(155deg, var(--bg-deep), var(--bg-mid) 55%, #081017 100%);
            }

            .block-container {
                padding-top: 1.1rem;
                padding-bottom: 2.2rem;
            }

            /* Ensure proper column spacing */
            div[data-testid="stHorizontalBlock"] {
                gap: 1rem;
            }

            /* Fix tabs visibility */
            .stTabs [data-baseweb="tab-list"] {
                gap: 0.5rem;
            }

            .stTabs [data-baseweb="tab"] {
                padding: 0.75rem 1.25rem;
            }

            /* Fix form input visibility */
            .stTextInput input, .stPassword input {
                padding: 0.75rem 1rem;
                font-size: 1rem;
            }

            /* Fix button visibility */
            .stButton > button {
                padding: 0.75rem 1.5rem;
                font-size: 1rem;
            }

            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, rgba(7, 23, 36, 0.95), rgba(4, 14, 24, 0.95));
                border-right: 1px solid rgba(90, 204, 255, 0.24);
                padding: 1rem;
            }

            .hero-shell {
                border: 1px solid var(--stroke);
                border-radius: 18px;
                padding: 1.35rem 1.5rem;
                background: linear-gradient(140deg, rgba(8, 29, 43, 0.80), rgba(9, 19, 30, 0.62));
                box-shadow: 0 0 26px rgba(49, 217, 255, 0.12);
                animation: pulseGlow 7s ease-in-out infinite;
            }

            .hero-title {
                font-family: "Orbitron", sans-serif;
                letter-spacing: 0.09em;
                color: var(--text-main);
                font-size: 1.5rem;
                margin: 0;
            }

            .hero-copy {
                font-family: "Manrope", sans-serif;
                color: var(--text-soft);
                margin-top: 0.45rem;
                margin-bottom: 0;
                line-height: 1.45;
            }

            .kpi-card {
                border: 1px solid rgba(95, 211, 255, 0.30);
                background: var(--glass);
                border-radius: 14px;
                padding: 0.9rem 1rem;
                min-height: 112px;
                animation: riseIn 0.65s ease both;
            }

            .kpi-label {
                font-family: "Manrope", sans-serif;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                font-size: 0.74rem;
                color: #91b4c6;
                margin: 0 0 0.3rem 0;
            }

            .kpi-value {
                font-family: "Orbitron", sans-serif;
                color: var(--text-main);
                font-size: 1.7rem;
                margin: 0;
            }

            .kpi-note {
                font-family: "Manrope", sans-serif;
                color: #6fd9ff;
                font-size: 0.8rem;
                margin-top: 0.35rem;
            }

            .step-box {
                border: 1px solid rgba(90, 204, 255, 0.24);
                border-radius: 12px;
                padding: 0.85rem 0.9rem;
                background: rgba(7, 26, 38, 0.72);
                min-height: 112px;
            }

            .step-box h4 {
                font-family: "Orbitron", sans-serif;
                color: var(--text-main);
                margin: 0 0 0.35rem 0;
                font-size: 0.95rem;
            }

            .step-box p {
                margin: 0;
                color: var(--text-soft);
                font-family: "Manrope", sans-serif;
                font-size: 0.88rem;
                line-height: 1.4;
            }

            .signal-card,
            .profile-card {
                border: 1px solid rgba(90, 204, 255, 0.30);
                border-radius: 12px;
                background: rgba(5, 20, 33, 0.72);
                padding: 0.8rem 0.9rem;
                margin-top: 0.7rem;
            }

            .signal-card h4,
            .profile-card h4 {
                margin: 0 0 0.45rem 0;
                font-family: "Orbitron", sans-serif;
                font-size: 0.9rem;
                color: var(--mint);
            }

            .signal-card pre,
            .profile-card pre {
                background: transparent;
                margin: 0;
                padding: 0;
                color: #d9effa;
                font-size: 0.84rem;
                white-space: pre-wrap;
                font-family: "Manrope", sans-serif;
            }

            .stButton > button {
                border: 1px solid rgba(101, 224, 255, 0.55);
                border-radius: 11px;
                color: #e8f7ff;
                background: linear-gradient(120deg, #0a3146, #0f4768);
                font-family: "Orbitron", sans-serif;
                letter-spacing: 0.04em;
                transition: 0.18s transform, 0.18s box-shadow;
            }

            .stButton > button:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 24px rgba(49, 217, 255, 0.21);
            }

            div[data-baseweb="input"] > div,
            div[data-baseweb="textarea"] > div,
            div[data-baseweb="select"] > div {
                border-radius: 11px;
                border: 1px solid rgba(86, 201, 246, 0.34);
                background: rgba(4, 17, 28, 0.58);
            }

            .stTabs [data-baseweb="tab-list"] {
                gap: 0.4rem;
            }

            .stTabs [data-baseweb="tab"] {
                border: 1px solid rgba(89, 203, 248, 0.28);
                border-radius: 9px;
                background: rgba(5, 18, 29, 0.55);
                color: #d3f0ff;
                font-family: "Orbitron", sans-serif;
                letter-spacing: 0.04em;
            }

            @keyframes pulseGlow {
                0% { box-shadow: 0 0 20px rgba(49, 217, 255, 0.10); }
                50% { box-shadow: 0 0 32px rgba(49, 217, 255, 0.18); }
                100% { box-shadow: 0 0 20px rgba(49, 217, 255, 0.10); }
            }

            @keyframes riseIn {
                from { transform: translateY(8px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def ensure_state() -> None:
    if "customers_df" not in st.session_state:
        st.session_state.customers_df = pd.DataFrame()
    if "health_result" not in st.session_state:
        st.session_state.health_result = None
    if "churn_result" not in st.session_state:
        st.session_state.churn_result = None
    if "nl_result" not in st.session_state:
        st.session_state.nl_result = None
    if "auth_customer_id" not in st.session_state:
        st.session_state.auth_customer_id = None
    if "signed_in" not in st.session_state:
        st.session_state.signed_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""


# Demo credentials for sign-in
DEMO_USERS = {
    "admin": "admin123",
    "operator": "operator123",
    "viewer": "viewer123",
}


def render_signin_form() -> None:
    # Center the login form with proper spacing
    st.markdown(
        """
        <style>
            .login-container {
                max-width: 400px;
                margin: 80px auto;
                padding: 40px;
                background: linear-gradient(145deg, rgba(8, 29, 43, 0.85), rgba(9, 19, 30, 0.75));
                border: 1px solid rgba(75, 205, 255, 0.35);
                border-radius: 20px;
                box-shadow: 0 0 40px rgba(49, 217, 255, 0.15);
            }
            .login-title {
                font-family: "Orbitron", sans-serif;
                font-size: 1.8rem;
                color: #e8f7ff;
                text-align: center;
                margin-bottom: 8px;
                letter-spacing: 0.08em;
            }
            .login-subtitle {
                font-family: "Manrope", sans-serif;
                color: #9bc4d9;
                text-align: center;
                margin-bottom: 30px;
                font-size: 0.95rem;
            }
            .demo-creds {
                background: rgba(56, 242, 180, 0.1);
                border: 1px solid rgba(56, 242, 180, 0.3);
                border-radius: 12px;
                padding: 15px;
                margin-top: 20px;
                text-align: center;
            }
            .demo-creds-title {
                color: #38f2b4;
                font-family: "Orbitron", sans-serif;
                font-size: 0.85rem;
                margin-bottom: 8px;
            }
            .demo-creds-text {
                color: #9bc4d9;
                font-family: "Manrope", sans-serif;
                font-size: 0.8rem;
                line-height: 1.6;
            }
        </style>
        <div class="login-container">
            <h1 class="login-title">Customer Portal</h1>
            <p class="login-subtitle">Sign in to access your dashboard</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Create a centered form container
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        with st.form("signin_form", clear_on_submit=True):
            st.markdown("<div style='text-align: center; margin-bottom: 20px;'></div>", unsafe_allow_html=True)
            username = st.text_input("Username", placeholder="Enter username", label_visibility="collapsed")
            password = st.text_input("Password", type="password", placeholder="Enter password", label_visibility="collapsed")
            st.markdown("<br>", unsafe_allow_html=True)
            submit = st.form_submit_button("Sign In", use_container_width=True)

            if submit:
                if username in DEMO_USERS and DEMO_USERS[username] == password:
                    st.session_state.signed_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid username or password")

        # Show demo credentials below the form
        st.markdown(
            """
            <div class="demo-creds">
                <p class="demo-creds-title">Demo Credentials</p>
                <p class="demo-creds-text">
                    admin / admin123<br>
                    operator / operator123<br>
                    viewer / viewer123
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_signout_button() -> None:
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Sign Out", use_container_width=True):
            st.session_state.signed_in = False
            st.session_state.username = ""
            st.session_state.auth_customer_id = None
            st.rerun()


def normalize_customers_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    normalized_df = df.copy()
    if "id" in normalized_df.columns:
        normalized_df["id"] = pd.to_numeric(normalized_df["id"], errors="coerce")
        normalized_df = normalized_df.dropna(subset=["id"])
        normalized_df["id"] = normalized_df["id"].astype(int)

    for numeric_col in ["nps_score", "monthly_usage"]:
        if numeric_col in normalized_df.columns:
            normalized_df[numeric_col] = pd.to_numeric(
                normalized_df[numeric_col], errors="coerce"
            )

    for date_col in ["contract_start", "contract_end"]:
        if date_col in normalized_df.columns:
            normalized_df[date_col] = pd.to_datetime(
                normalized_df[date_col], errors="coerce"
            )

    return normalized_df.reset_index(drop=True)


def parse_response(response: requests.Response):
    try:
        return response.json()
    except ValueError:
        return {"raw_response": response.text}


def fetch_get(api_url: str, endpoint: str):
    try:
        response = requests.get(f"{api_url}{endpoint}", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return parse_response(response), None
    except RequestException as exc:
        return None, str(exc)


def fetch_post(api_url: str, endpoint: str, payload: dict):
    try:
        response = requests.post(
            f"{api_url}{endpoint}", json=payload, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return parse_response(response), None
    except RequestException as exc:
        return None, str(exc)


def render_hero(total_customers: int, scoped_customers: int, mode: str) -> None:
    mode_label = "Customer Self-Service" if mode == "Customer Self-Service" else "Operations View"
    st.markdown(
        f"""
        <div class="hero-shell">
            <h1 class="hero-title">Customer Portal</h1>
            <p class="hero-copy">
                Clear actions, fast diagnostics, and AI insights in one guided flow.
                Mode: <strong>{mode_label}</strong> | Portfolio records: <strong>{total_customers}</strong>
                | Active scope: <strong>{scoped_customers}</strong>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi(label: str, value: str, note: str) -> None:
    st.markdown(
        f"""
        <div class="kpi-card">
            <p class="kpi-label">{label}</p>
            <p class="kpi-value">{value}</p>
            <p class="kpi-note">{note}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_signal(title: str, payload) -> None:
    formatted = (
        json.dumps(payload, indent=2)
        if isinstance(payload, (dict, list))
        else str(payload)
    )
    st.markdown(
        f"""
        <div class="signal-card">
            <h4>{title}</h4>
            <pre>{formatted}</pre>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_health_text(health_result: dict) -> None:
    """Render health score as a human-readable text message."""
    customer_id = health_result.get("customer_id", "Unknown")
    score = health_result.get("health_score", 0)

    if score >= 80:
        status = "Excellent"
        emoji = "🌟"
        description = "This customer has outstanding health metrics. They show strong engagement, high satisfaction, and stable contract status."
    elif score >= 60:
        status = "Good"
        emoji = "✅"
        description = "This customer is in good standing with healthy engagement patterns. Monitor for any changes in usage or satisfaction."
    elif score >= 40:
        status = "Moderate"
        emoji = "⚠️"
        description = "This customer shows some concerns that may need attention. Review NPS scores and ticket history for improvement opportunities."
    else:
        status = "At Risk"
        emoji = "🚨"
        description = "This customer requires immediate attention. Low health scores indicate potential churn risk. Consider proactive outreach."

    st.markdown(
        f"""
        <div class="signal-card">
            <h4>Health Assessment for Customer #{customer_id}</h4>
            <pre style="font-size: 1.1rem; line-height: 1.6;">{emoji} Health Score: {score}/100 ({status})

{description}

The health score is calculated based on:
• NPS Score (35% weight) - Customer satisfaction metric
• Monthly Usage (30% weight) - Engagement level
• Ticket Count (20% weight) - Support activity (inverse)
• Contract Duration (15% weight) - Account stability</pre>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_churn_text(churn_result: dict) -> None:
    """Render churn risk as a human-readable text message."""
    customer_id = churn_result.get("customer_id", "Unknown")
    probability = churn_result.get("churn_probability", 0)
    explanation = churn_result.get("explanation", {})

    probability_pct = probability * 100

    if probability >= 0.6:
        risk_level = "High Risk"
        emoji = "🚨"
        recommendation = "Immediate action recommended. Reach out to understand concerns and offer retention incentives."
    elif probability >= 0.4:
        risk_level = "Medium Risk"
        emoji = "⚠️"
        recommendation = "Schedule a check-in call to address any issues and reinforce value proposition."
    elif probability >= 0.2:
        risk_level = "Low Risk"
        emoji = "✅"
        recommendation = "Continue regular engagement. Monitor for any changes in usage or satisfaction."
    else:
        risk_level = "Very Low Risk"
        emoji = "🌟"
        recommendation = "Customer is stable. Focus on maintaining satisfaction and exploring upsell opportunities."

    # Build factors text
    factors_text = ""
    if explanation and "top_factors" in explanation:
        factors_text = "\nKey factors influencing this risk score:\n"
        for factor in explanation["top_factors"]:
            factor_name = factor.get("label", factor.get("factor", "Unknown"))
            direction = factor.get("direction", "neutral")
            factors_text += f"• {factor_name}: {direction}\n"

    st.markdown(
        f"""
        <div class="signal-card">
            <h4>Churn Risk Assessment for Customer #{customer_id}</h4>
            <pre style="font-size: 1.1rem; line-height: 1.6;">{emoji} Churn Probability: {probability_pct:.1f}% ({risk_level})

{recommendation}{factors_text}
The churn prediction model analyzes:
• NPS Score - Lower scores increase churn risk
• Monthly Usage - Lower usage indicates disengagement
• Ticket Count - High support activity may signal issues
• Contract Days Left - Expiring contracts increase risk</pre>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_profile_card(customer_row: pd.Series) -> None:
    payload = {
        "customer_id": int(customer_row["id"]),
        "company_name": customer_row.get("company_name", "N/A"),
        "region": customer_row.get("region", "N/A"),
        "plan_tier": customer_row.get("plan_tier", "N/A"),
        "contract_start": str(customer_row.get("contract_start", "N/A"))[:10],
        "contract_end": str(customer_row.get("contract_end", "N/A"))[:10],
        "nps_score": (
            round(float(customer_row["nps_score"]), 2)
            if pd.notna(customer_row.get("nps_score"))
            else "N/A"
        ),
        "monthly_usage": (
            round(float(customer_row["monthly_usage"]), 2)
            if pd.notna(customer_row.get("monthly_usage"))
            else "N/A"
        ),
    }
    st.markdown(
        f"""
        <div class="profile-card">
            <h4>Active Customer Profile</h4>
            <pre>{json.dumps(payload, indent=2)}</pre>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_customer_row(df: pd.DataFrame, customer_id: int | None) -> pd.Series | None:
    if customer_id is None or df.empty or "id" not in df.columns:
        return None

    matched = df[df["id"] == int(customer_id)]
    if matched.empty:
        return None

    return matched.iloc[0]


def validate_auth_customer(df: pd.DataFrame) -> None:
    auth_customer_id = st.session_state.auth_customer_id
    if auth_customer_id is None:
        return

    if df.empty or "id" not in df.columns:
        st.session_state.auth_customer_id = None
        return

    if int(auth_customer_id) not in set(df["id"].tolist()):
        st.session_state.auth_customer_id = None


def build_customer_scope(df: pd.DataFrame, mode: str) -> pd.DataFrame:
    if mode != "Customer Self-Service":
        return df

    auth_customer_id = st.session_state.auth_customer_id
    if auth_customer_id is None or df.empty or "id" not in df.columns:
        return pd.DataFrame(columns=df.columns)

    scoped = df[df["id"] == int(auth_customer_id)]
    return scoped.reset_index(drop=True)


def derive_proxy_metrics(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    enriched = df.copy()

    if "nps_score" in enriched.columns:
        nps = pd.to_numeric(enriched["nps_score"], errors="coerce")
    else:
        nps = pd.Series(0.0, index=enriched.index)
    nps = nps.fillna(0).clip(-100, 100)

    if "monthly_usage" in enriched.columns:
        usage = pd.to_numeric(enriched["monthly_usage"], errors="coerce")
    else:
        usage = pd.Series(0.0, index=enriched.index)
    usage = usage.fillna(0).clip(0, 50000)

    if "contract_end" in enriched.columns:
        contract_end = pd.to_datetime(enriched["contract_end"], errors="coerce")
    else:
        contract_end = pd.Series(pd.NaT, index=enriched.index)
    days_left = (contract_end - pd.Timestamp(date.today())).dt.days
    days_left = pd.to_numeric(days_left, errors="coerce").fillna(0).clip(lower=0)

    plan_map = {
        "starter": 0.18,
        "basic": 0.15,
        "growth": 0.11,
        "business": 0.08,
        "enterprise": 0.05,
    }
    if "plan_tier" in enriched.columns:
        plan_tier = enriched["plan_tier"].astype(str)
    else:
        plan_tier = pd.Series("unknown", index=enriched.index)
    plan_risk = (
        plan_tier.str.lower()
        .map(plan_map)
        .fillna(0.12)
    )

    proxy_health = (
        ((nps + 100) / 200) * 45
        + (usage / 50000) * 30
        + ((days_left.clip(upper=365) / 365) * 20)
        + ((1 - plan_risk) * 5)
    ).clip(0, 100)

    proxy_churn = (
        (1 - (nps + 100) / 200) * 0.35
        + (1 - (usage / 50000)) * 0.25
        + (1 - days_left.clip(upper=365) / 365) * 0.25
        + plan_risk * 0.15
    ).clip(0, 1)

    enriched["proxy_health_score"] = proxy_health.round(2)
    enriched["proxy_churn_probability"] = proxy_churn.round(4)
    enriched["contract_end"] = contract_end
    enriched["contract_month"] = contract_end.dt.to_period("M").dt.to_timestamp()

    return enriched


def render_health_trend_chart(trend_df: pd.DataFrame) -> None:
    chart = (
        alt.Chart(trend_df)
        .mark_line(point=True, strokeWidth=3, color="#31d9ff")
        .encode(
            x=alt.X("contract_month:T", title="Contract End Timeline"),
            y=alt.Y("avg_health:Q", title="Average Health", scale=alt.Scale(domain=[0, 100])),
            tooltip=[
                alt.Tooltip("contract_month:T", title="Month"),
                alt.Tooltip("avg_health:Q", title="Avg Health", format=".2f"),
                alt.Tooltip("customer_count:Q", title="Customers"),
            ],
        )
        .properties(height=300, title="Health Trend")
    )
    st.altair_chart(chart, use_container_width=True)


def render_churn_trend_chart(trend_df: pd.DataFrame) -> None:
    chart = (
        alt.Chart(trend_df)
        .mark_line(point=True, strokeWidth=3, color="#38f2b4")
        .encode(
            x=alt.X("contract_month:T", title="Contract End Timeline"),
            y=alt.Y("avg_churn:Q", title="Average Churn Probability", scale=alt.Scale(domain=[0, 1])),
            tooltip=[
                alt.Tooltip("contract_month:T", title="Month"),
                alt.Tooltip("avg_churn:Q", title="Avg Churn", format=".2%"),
                alt.Tooltip("customer_count:Q", title="Customers"),
            ],
        )
        .properties(height=300, title="Churn Trendline")
    )
    st.altair_chart(chart, use_container_width=True)


def render_plan_segment_chart(df: pd.DataFrame) -> None:
    if "plan_tier" not in df.columns:
        st.info("Plan tier is unavailable in the current dataset.")
        return

    segment_df = (
        df.groupby("plan_tier", dropna=False)
        .agg(
            customers=("id", "count"),
            avg_health=("proxy_health_score", "mean"),
            avg_churn=("proxy_churn_probability", "mean"),
        )
        .reset_index()
        .sort_values(by="avg_churn", ascending=False)
    )

    chart = (
        alt.Chart(segment_df)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X("plan_tier:N", title="Plan Tier", sort="-y"),
            y=alt.Y("avg_churn:Q", title="Average Churn", scale=alt.Scale(domain=[0, 1])),
            color=alt.Color("avg_health:Q", title="Avg Health", scale=alt.Scale(scheme="tealblues")),
            tooltip=[
                alt.Tooltip("plan_tier:N", title="Plan"),
                alt.Tooltip("customers:Q", title="Customers"),
                alt.Tooltip("avg_health:Q", title="Avg Health", format=".2f"),
                alt.Tooltip("avg_churn:Q", title="Avg Churn", format=".2%"),
            ],
        )
        .properties(height=300, title="Plan Tier Risk Profile")
    )
    st.altair_chart(chart, use_container_width=True)


apply_theme()
ensure_state()

# Sign-in gate
if not st.session_state.signed_in:
    render_signin_form()
    st.stop()

# Show sign-out button after successful sign-in
render_signout_button()
st.markdown(f"**Signed in as:** {st.session_state.username}")
st.write("")

st.sidebar.markdown("## Command Rail")
api_url = st.sidebar.text_input("Backend API URL", value=DEFAULT_API_URL)
st.sidebar.caption("Keep this synced with your running backend service.")

portal_mode = st.sidebar.radio(
    "Experience Mode",
    options=["Operations View", "Customer Self-Service"],
    index=0,
)

st.sidebar.markdown("### Interaction Path")
st.sidebar.markdown("1. Sync customer data feed")
st.sidebar.markdown("2. Sign in or pick a profile context")
st.sidebar.markdown("3. Run diagnostics, AI insight, and trend charts")

if st.sidebar.button("Clear Session Outputs", use_container_width=True):
    st.session_state.health_result = None
    st.session_state.churn_result = None
    st.session_state.nl_result = None
    st.success("Signals and AI output were cleared.")

active_df = normalize_customers_df(st.session_state.customers_df)
validate_auth_customer(active_df)

if portal_mode == "Customer Self-Service":
    st.sidebar.markdown("### Customer Sign-In")
    if active_df.empty:
        st.sidebar.info("Sync customers first, then sign in as a profile.")
    else:
        profile_source = active_df.sort_values(by=["company_name", "id"])
        profile_ids = profile_source["id"].tolist()

        profile_lookup = {
            int(row["id"]): (
                f"{int(row['id'])} | {row.get('company_name', 'Unknown')} "
                f"({row.get('region', 'N/A')}, {row.get('plan_tier', 'N/A')})"
            )
            for _, row in profile_source.iterrows()
        }

        selected_profile_id = st.sidebar.selectbox(
            "Select customer profile",
            options=profile_ids,
            format_func=lambda cust_id: profile_lookup.get(int(cust_id), str(cust_id)),
        )

        login_col, logout_col = st.sidebar.columns(2)
        with login_col:
            if st.button("Sign In", use_container_width=True):
                st.session_state.auth_customer_id = int(selected_profile_id)
                st.sidebar.success(f"Signed in to profile {int(selected_profile_id)}.")
        with logout_col:
            if st.button("Sign Out", use_container_width=True):
                st.session_state.auth_customer_id = None
                st.sidebar.info("Profile session ended.")

        if st.session_state.auth_customer_id is not None:
            st.sidebar.caption(
                f"Active profile: {profile_lookup.get(st.session_state.auth_customer_id, st.session_state.auth_customer_id)}"
            )

scoped_df = build_customer_scope(active_df, portal_mode)
scoped_metrics_df = derive_proxy_metrics(scoped_df if portal_mode == "Customer Self-Service" else active_df)

render_hero(
    total_customers=len(active_df),
    scoped_customers=len(scoped_df) if portal_mode == "Customer Self-Service" else len(active_df),
    mode=portal_mode,
)
st.write("")

kpi_col1, kpi_col2, kpi_col3 = st.columns(3)

if portal_mode == "Customer Self-Service":
    context_df = scoped_metrics_df
    volume_note = "records in signed-in customer scope"
else:
    context_df = scoped_metrics_df
    volume_note = "records currently available"

with kpi_col1:
    render_kpi("Customer Volume", str(len(context_df)), volume_note)

with kpi_col2:
    if not context_df.empty and "proxy_health_score" in context_df.columns:
        render_kpi(
            "Avg Health",
            f"{context_df['proxy_health_score'].mean():.1f}",
            "calculated from customer telemetry",
        )
    else:
        render_kpi("Avg Health", "N/A", "sync and sign in to compute")

with kpi_col3:
    if not context_df.empty and "proxy_churn_probability" in context_df.columns:
        high_risk = (context_df["proxy_churn_probability"] >= 0.60).sum()
        render_kpi("High Risk Segment", str(int(high_risk)), "churn probability >= 60%")
    else:
        render_kpi("High Risk Segment", "N/A", "requires customer records")

st.write("")

step_col1, step_col2, step_col3 = st.columns(3)
with step_col1:
    st.markdown(
        """
        <div class="step-box">
            <h4>Step 1: Sync</h4>
            <p>Pull the latest customer records from the backend and lock your working scope.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with step_col2:
    st.markdown(
        """
        <div class="step-box">
            <h4>Step 2: Diagnose</h4>
            <p>Run health and churn checks with profile-aware controls for clearer decisions.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with step_col3:
    st.markdown(
        """
        <div class="step-box">
            <h4>Step 3: Forecast</h4>
            <p>Read trend charts and ask AI for next-best actions based on current customer context.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")

tab_feed, tab_diagnostics, tab_ai, tab_trends = st.tabs(
    ["Live Feed", "Customer Diagnostics", "AI Concierge", "Trend Radar"]
)

with tab_feed:
    st.subheader("Live Customer Feed")
    sync_col, hint_col = st.columns([1, 2])

    with sync_col:
        if st.button("Sync Customer Feed", use_container_width=True):
            payload, error = fetch_get(api_url, "/customers")
            if error:
                st.error(f"Could not load customers: {error}")
            else:
                st.session_state.customers_df = normalize_customers_df(pd.DataFrame(payload))
                validate_auth_customer(st.session_state.customers_df)
                st.success("Customer feed synced.")

    with hint_col:
        st.info(
            "Operations mode shows all records. Self-service mode shows only the signed-in profile."
        )

    live_df = normalize_customers_df(st.session_state.customers_df)
    validate_auth_customer(live_df)

    if live_df.empty:
        st.warning("No customer data loaded yet. Click 'Sync Customer Feed' to start.")
    elif portal_mode == "Customer Self-Service" and st.session_state.auth_customer_id is None:
        st.warning("Sign in to a customer profile from the sidebar to view scoped data.")
    else:
        scope_df = build_customer_scope(live_df, portal_mode)
        if portal_mode == "Operations View":
            scope_df = live_df

        active_profile = get_customer_row(live_df, st.session_state.auth_customer_id)
        if portal_mode == "Customer Self-Service" and active_profile is not None:
            render_profile_card(active_profile)

        search = st.text_input(
            "Search rows across all fields",
            placeholder="Type company, region, id, plan, or any value...",
        )
        filtered_df = scope_df
        if search.strip():
            search_mask = scope_df.astype(str).apply(
                lambda column: column.str.contains(
                    search, case=False, na=False, regex=False
                )
            )
            filtered_df = scope_df[search_mask.any(axis=1)]

        st.dataframe(filtered_df, use_container_width=True, height=420)
        st.caption(f"Showing {len(filtered_df)} of {len(scope_df)} records.")

with tab_diagnostics:
    st.subheader("Customer Diagnostics")
    st.write("Run precise diagnostics with profile-aware controls.")

    diagnostics_df = normalize_customers_df(st.session_state.customers_df)
    validate_auth_customer(diagnostics_df)

    locked_customer_id = (
        st.session_state.auth_customer_id
        if portal_mode == "Customer Self-Service"
        else None
    )

    if diagnostics_df.empty:
        st.warning("Sync customers first to run diagnostics.")
    elif portal_mode == "Customer Self-Service" and locked_customer_id is None:
        st.warning("Sign in to a customer profile from the sidebar to run diagnostics.")
    else:
        if locked_customer_id is not None:
            target_customer_id = int(locked_customer_id)
            st.info("Self-service mode is active. Diagnostics are locked to your profile.")
            st.number_input(
                "Customer ID",
                min_value=1,
                step=1,
                value=target_customer_id,
                disabled=True,
                key="locked_customer_id_display",
            )

            profile_row = get_customer_row(diagnostics_df, target_customer_id)
            if profile_row is not None:
                render_profile_card(profile_row)
        else:
            available_ids = diagnostics_df["id"].tolist() if "id" in diagnostics_df.columns else [1]
            default_id = int(available_ids[0]) if available_ids else 1
            target_customer_id = int(
                st.number_input(
                    "Customer ID",
                    min_value=1,
                    step=1,
                    value=default_id,
                    key="selected_customer_id",
                )
            )

        health_col, churn_col = st.columns(2)

        with health_col:
            if st.button("Generate Health Score", use_container_width=True):
                payload, error = fetch_get(
                    api_url, f"/customers/{target_customer_id}/health-score"
                )
                if error:
                    st.error(f"Health score request failed: {error}")
                else:
                    st.session_state.health_result = payload
                    st.success(
                        f"Health score generated for customer {target_customer_id}."
                    )

        with churn_col:
            if st.button("Check Churn Risk", use_container_width=True):
                payload, error = fetch_get(
                    api_url, f"/customers/{target_customer_id}/churn-risk"
                )
                if error:
                    st.error(f"Churn risk request failed: {error}")
                else:
                    st.session_state.churn_result = payload
                    st.success(
                        f"Churn risk generated for customer {target_customer_id}."
                    )

    if st.session_state.health_result is not None:
        render_health_text(st.session_state.health_result)

    if st.session_state.churn_result is not None:
        render_churn_text(st.session_state.churn_result)

with tab_ai:
    st.subheader("AI Concierge")
    st.write("Ask for summaries, warnings, and recommended next actions.")

    ai_df = normalize_customers_df(st.session_state.customers_df)
    validate_auth_customer(ai_df)

    profile_row = get_customer_row(ai_df, st.session_state.auth_customer_id)
    scoped_prompt = (
        portal_mode == "Customer Self-Service"
        and st.session_state.auth_customer_id is not None
    )

    if scoped_prompt and profile_row is not None:
        st.info(
            f"AI prompts can be scoped to customer {int(profile_row['id'])} - {profile_row.get('company_name', 'N/A')}."
        )

    query = st.text_area(
        "Your question",
        placeholder="Example: Which contracts need proactive renewal outreach in the next 60 days?",
        height=130,
    )

    scope_toggle = st.checkbox(
        "Scope AI query to signed-in customer profile",
        value=True,
        disabled=not scoped_prompt,
    )

    if st.button("Run AI Insight", use_container_width=True):
        if not query.strip():
            st.warning("Please enter a question before running the AI insight.")
        else:
            final_query = query.strip()
            if scope_toggle and scoped_prompt and profile_row is not None:
                final_query = (
                    "For customer_id "
                    f"{int(profile_row['id'])} ({profile_row.get('company_name', 'Unknown')}), "
                    f"answer this: {query.strip()}"
                )

            payload, error = fetch_post(api_url, "/nl-query", {"query": final_query})
            if error:
                st.error(f"AI query failed: {error}")
            else:
                st.session_state.nl_result = payload
                st.success("AI insight generated.")

    if st.session_state.nl_result is not None:
        render_signal("AI Response", st.session_state.nl_result)

with tab_trends:
    st.subheader("Trend Radar")
    st.write("Visual health and churn trendlines for the active interaction scope.")

    trends_df = normalize_customers_df(st.session_state.customers_df)
    validate_auth_customer(trends_df)

    if trends_df.empty:
        st.warning("Sync customer data to generate trend charts.")
    elif portal_mode == "Customer Self-Service" and st.session_state.auth_customer_id is None:
        st.warning("Sign in to a profile to view customer-scoped trends.")
    else:
        scope_df = build_customer_scope(trends_df, portal_mode)
        if portal_mode == "Operations View":
            scope_df = trends_df

        metric_df = derive_proxy_metrics(scope_df)
        valid_timeline_df = metric_df.dropna(subset=["contract_month"])

        if valid_timeline_df.empty:
            st.info("Contract timeline fields are unavailable; charts need contract dates.")
        else:
            trend_df = (
                valid_timeline_df.groupby("contract_month")
                .agg(
                    avg_health=("proxy_health_score", "mean"),
                    avg_churn=("proxy_churn_probability", "mean"),
                    customer_count=("id", "count"),
                )
                .reset_index()
                .sort_values(by="contract_month")
            )

            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                render_health_trend_chart(trend_df)
            with chart_col2:
                render_churn_trend_chart(trend_df)

        st.write("")
        render_plan_segment_chart(metric_df)

        st.write("")
        st.markdown("### Highest Risk Customers")
        risk_table = metric_df.sort_values(
            by="proxy_churn_probability", ascending=False
        )
        visible_columns = [
            column
            for column in [
                "id",
                "company_name",
                "region",
                "plan_tier",
                "contract_end",
                "proxy_health_score",
                "proxy_churn_probability",
            ]
            if column in risk_table.columns
        ]
        st.dataframe(risk_table[visible_columns].head(12), use_container_width=True)
