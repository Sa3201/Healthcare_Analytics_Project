"""Healthcare Staffing Analytics dashboard.

Run locally from the repository root:
    streamlit run streamlit_dashboard/app.py


.streamlit/secrets.toml contains Snowflake credentials. Do not commit this
real secrets file.
"""

import pandas as pd
import plotly.express as px
import streamlit as st


DATABASE = "PP2_HEALTHCARE"
SCHEMA = "ANALYTICS"
PORTFOLIO_URL = "https://your-portfolio-url.streamlit.app"  # Update before deployment.
GITHUB_URL = "https://github.com/Sa3201/Healthcare_Analytics_Project"

MARTS = {
    "state_summary": "MART_STATE_STAFFING_SUMMARY",
    "low_staffing": "MART_LOW_STAFFING_FACILITIES",
    "staffing_quality": "MART_STAFFING_QUALITY",
}


st.set_page_config(
    page_title="Healthcare Analytics Dashboard",
    page_icon="🏥",
    layout="wide",
)


@st.cache_data(ttl=600, show_spinner=False)
def load_mart(table_name: str) -> pd.DataFrame:
    """Read one dashboard mart from Snowflake and make column names consistent."""
    connection = st.connection("snowflake")
    data = connection.query(
        f"SELECT * FROM {DATABASE}.{SCHEMA}.{table_name}",
        ttl=600,
    )
    data.columns = [column.lower() for column in data.columns]
    return data


def get_mart(mart_key: str) -> pd.DataFrame:
    """Show a friendly error instead of exposing Snowflake connection details."""
    try:
        return load_mart(MARTS[mart_key])
    except Exception:
        st.error("The dashboard could not load data from Snowflake.")
        st.info("Check your .streamlit/secrets.toml values and Snowflake role permissions.")
        st.stop()


def choose_quarter(data: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Add a quarter filter when the table contains calendar-quarter data."""
    if "calendar_quarter" not in data.columns:
        return data, "All available data"

    quarters = sorted(data["calendar_quarter"].dropna().unique(), reverse=True)
    selected_quarter = st.sidebar.selectbox("Calendar quarter", quarters)
    return data[data["calendar_quarter"] == selected_quarter], selected_quarter


def add_occupancy_percent(data: pd.DataFrame) -> pd.DataFrame:
    """Convert decimal occupancy values to percentages for charts and tables."""
    formatted = data.copy()
    if "average_occupancy_rate" in formatted.columns:
        formatted["average_occupancy_percent"] = formatted["average_occupancy_rate"] * 100
    return formatted


def filter_by_state(data: pd.DataFrame, key: str) -> pd.DataFrame:
    """Add a state filter and return only the selected states."""
    states = sorted(data["state"].dropna().unique())
    selected_states = st.sidebar.multiselect("State", states, default=states, key=key)
    return data[data["state"].isin(selected_states)]


def metric_tile(label: str, value: str, annotation: str) -> None:
    """Display one KPI in a bordered tile with a short definition."""
    with st.container(border=True):
        st.metric(label, value)
        st.caption(annotation)


def chart_tile(title: str, annotation: str, chart) -> None:
    """Display one chart in a bordered tile with a consulting-style takeaway."""
    with st.container(border=True):
        st.subheader(title)
        st.markdown(f"**Key takeaway:** {annotation}")
        st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False})


def information_tile(title: str, text: str) -> None:
    """Display a short methodology note in the same visual style as charts."""
    with st.container(border=True):
        st.subheader(title)
        st.caption(text)


def dashboard_navigation(pages: list) -> None:
    """Render the page links in the main dashboard area above each page title."""
    navigation_columns = st.columns(4, gap="small")
    for column, page in zip(navigation_columns, pages):
        with column:
            st.page_link(
                page,
                label=page.title,
                icon=page.icon,
                use_container_width=True,
            )

    st.divider()


def overview_page() -> None:
    st.title("Healthcare Analytics Dashboard")
    st.caption("Nursing-home staffing, occupancy, contractor use, and quality measures.")

    data, selected_quarter = choose_quarter(get_mart("state_summary"))
    data = filter_by_state(data, key="overview_state_filter")
    if data.empty:
        st.warning("Select at least one state to view the overview.")
        return
    st.subheader(f"Overview — {selected_quarter}")

    total_facilities = int(data["facility_count"].sum())
    average_hprd = data["average_staffing_hprd"].mean()
    average_rn_hprd = data["average_rn_hprd"].mean()
    average_occupancy = data["average_occupancy_percent"].mean()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_tile("Facilities", f"{total_facilities:,}", "Facilities represented in this quarter.")
    with col2:
        metric_tile("Average staffing HPRD", f"{average_hprd:.2f}", "Total nursing hours per resident day.")
    with col3:
        metric_tile("Average RN HPRD", f"{average_rn_hprd:.2f}", "Registered-nurse hours per resident day.")
    with col4:
        metric_tile("Average occupancy proxy", f"{average_occupancy:.1f}%", "Resident census divided by certified beds.")

    left, right = st.columns(2)
    with left:
        chart_data = data.sort_values("average_staffing_hprd", ascending=False)
        chart = px.bar(
            chart_data,
            x="state",
            y="average_staffing_hprd",
            labels={"average_staffing_hprd": "Staffing HPRD", "state": "State"},
        )
        chart_tile(
            "Average Staffing HPRD by State",
            "Nursing time per resident varies across states",
            chart,
        )

    with right:
        chart = px.scatter(
            data,
            x="average_occupancy_percent",
            y="average_staffing_hprd",
            size="facility_count",
            hover_name="state",
            labels={
                "average_occupancy_percent": "Occupancy proxy (%)",
                "average_staffing_hprd": "Staffing HPRD",
                "facility_count": "Facilities",
            },
        )
        chart_tile(
            "Occupancy Proxy vs. Staffing HPRD",
            "States with higher occupancy tend to have lower staffing levels",
            chart,
        )

    information_tile(
        "How to read these metrics",
        "HPRD means staffing hours per resident day. Occupancy is a proxy based on resident census divided by certified beds.",
    )


def state_staffing_page() -> None:
    st.title("State Staffing")
    st.caption("Compare staffing levels, occupancy, and contractor use across states.")

    data, selected_quarter = choose_quarter(get_mart("state_summary"))
    data = filter_by_state(data, key="state_staffing_filter")
    if data.empty:
        st.warning("Select at least one state to compare staffing metrics.")
        return
    data = data.sort_values("average_staffing_hprd", ascending=False)

    left, right = st.columns(2)
    with left:
        staffing_chart = px.bar(
            data,
            x="state",
            y=["average_staffing_hprd", "average_rn_hprd"],
            barmode="group",
            labels={"value": "Hours per resident day", "state": "State", "variable": "Metric"},
        )
        chart_tile(
            f"Total and RN Staffing HPRD — {selected_quarter}",
            "RN staffing mix varies across states",
            staffing_chart,
        )

    with right:
        contractor_chart = px.bar(
            data.sort_values("average_contract_hour_percent", ascending=False),
            x="state",
            y="average_contract_hour_percent",
            labels={"average_contract_hour_percent": "Contractor hours (%)", "state": "State"},
        )
        chart_tile(
            "Average Contractor Hours Percentage",
            "Higher contractor share signals greater reliance on temporary nursing staff",
            contractor_chart,
        )

    display_columns = [
        "state",
        "facility_count",
        "average_daily_census",
        "average_staffing_hprd",
        "average_rn_hprd",
        "average_occupancy_percent",
        "average_contract_hour_percent",
    ]
    with st.container(border=True):
        st.subheader("State metrics table")
        st.markdown("**Key takeaway:** States lead and trail on staffing, occupancy, and contractor use")
        st.dataframe(
            data[display_columns],
            use_container_width=True,
            hide_index=True,
            column_config={
                "facility_count": st.column_config.NumberColumn("Facilities", format="%d"),
                "average_daily_census": st.column_config.NumberColumn("Average daily census", format="%.1f"),
                "average_staffing_hprd": st.column_config.NumberColumn("Staffing HPRD", format="%.2f"),
                "average_rn_hprd": st.column_config.NumberColumn("RN HPRD", format="%.2f"),
                "average_occupancy_percent": st.column_config.NumberColumn("Occupancy proxy", format="%.1f%%"),
                "average_contract_hour_percent": st.column_config.NumberColumn("Contractor hours", format="%.1f%%"),
            },
        )


def facility_watchlist_page() -> None:
    st.title("Facility Watchlist")
    st.caption("Facilities with the lowest average staffing HPRD in the selected quarter.")

    data, selected_quarter = choose_quarter(get_mart("low_staffing"))
    filtered = add_occupancy_percent(filter_by_state(data, key="watchlist_state_filter"))
    if filtered.empty:
        st.warning("Select at least one state to view the facility watchlist.")
        return

    chart = px.scatter(
        filtered,
        x="average_daily_census",
        y="average_staffing_hprd",
        color="state",
        hover_name="facility_name",
        hover_data=["facility_ccn", "average_rn_hprd", "average_occupancy_percent"],
        labels={
            "average_daily_census": "Average daily resident census",
            "average_staffing_hprd": "Average staffing HPRD",
        },
    )
    chart_tile(
        f"Staffing HPRD vs. Resident Census — {selected_quarter}",
        "Low HPRD and high resident census flag facilities for review",
        chart,
    )

    display_columns = [
        "staffing_rank",
        "facility_name",
        "facility_ccn",
        "state",
        "average_daily_census",
        "average_staffing_hprd",
        "average_rn_hprd",
        "average_occupancy_percent",
        "contract_hour_percentage",
    ]
    with st.container(border=True):
        st.subheader("Lowest-staffed facilities")
        st.markdown("**Key takeaway:** Lowest-HPRD facilities form the watchlist")
        st.dataframe(
            filtered.sort_values("staffing_rank")[display_columns],
            use_container_width=True,
            hide_index=True,
            column_config={
                "staffing_rank": "Rank",
                "facility_name": "Facility",
                "facility_ccn": "CMS CCN",
                "average_daily_census": st.column_config.NumberColumn("Average daily census", format="%.1f"),
                "average_staffing_hprd": st.column_config.NumberColumn("Staffing HPRD", format="%.2f"),
                "average_rn_hprd": st.column_config.NumberColumn("RN HPRD", format="%.2f"),
                "average_occupancy_percent": st.column_config.NumberColumn("Occupancy proxy", format="%.1f%%"),
                "contract_hour_percentage": st.column_config.NumberColumn("Contractor hours", format="%.1f%%"),
            },
        )


def staffing_quality_page() -> None:
    st.title("Staffing & Quality")
    st.caption("Explore the relationship between staffing levels and CMS quality measures.")

    data, selected_quarter = choose_quarter(get_mart("staffing_quality"))
    state_data = filter_by_state(data, key="quality_state_filter")

    quality_sources = sorted(state_data["quality_source"].dropna().unique())
    selected_source = st.sidebar.selectbox(
        "Quality source",
        ["All sources", *quality_sources],
        key="quality_source_filter",
    )
    if selected_source != "All sources":
        state_data = state_data[state_data["quality_source"] == selected_source]
    if state_data.empty:
        st.warning("Select at least one state and quality source to view quality results.")
        return

    measures = sorted(state_data["measure_name"].dropna().unique())
    selected_measure = st.sidebar.selectbox("Quality measure", measures)
    filtered = state_data[state_data["measure_name"] == selected_measure]

    chart = px.scatter(
        filtered,
        x="average_staffing_hprd",
        y="measure_score",
        color="state",
        hover_name="facility_name",
        hover_data=["facility_ccn", "average_rn_hprd", "average_daily_census", "measure_period"],
        labels={"average_staffing_hprd": "Average staffing HPRD", "measure_score": "Quality measure score"},
    )
    chart_tile(
        f"Staffing HPRD vs. Quality Score — {selected_quarter}",
        "Staffing levels and quality scores vary across facilities",
        chart,
    )

    with st.container(border=True):
        st.subheader("Facility quality detail")
        st.markdown("**Key takeaway:** Outlier facilities warrant deeper review")
        st.dataframe(
            filtered[
                [
                    "facility_name",
                    "facility_ccn",
                    "state",
                    "average_staffing_hprd",
                    "average_rn_hprd",
                    "measure_name",
                    "measure_score",
                    "measure_period",
                ]
            ].sort_values("measure_score"),
            use_container_width=True,
            hide_index=True,
            column_config={
                "facility_name": "Facility",
                "facility_ccn": "CMS CCN",
                "average_staffing_hprd": st.column_config.NumberColumn("Staffing HPRD", format="%.2f"),
                "average_rn_hprd": st.column_config.NumberColumn("RN HPRD", format="%.2f"),
                "measure_name": "Quality measure",
                "measure_score": st.column_config.NumberColumn("Score", format="%.2f"),
                "measure_period": "Reporting period",
            },
        )

    information_tile(
        "Interpretation note",
        "This page supports exploratory analysis only. The staffing and CMS quality measures use different reporting periods, so the charts do not prove causation.",
    )


def main() -> None:
    with st.sidebar:
        st.title("🏥 Healthcare Analytics Dashboard")
        st.caption("Tech Stack: Google Drive | AWS Glue | Amazon S3 | Snowflake | dbt | Streamlit")

    pages = [
        st.Page(overview_page, title="Overview", icon="🏠", default=True),
        st.Page(state_staffing_page, title="State Staffing", icon="👩‍⚕️"),
        st.Page(facility_watchlist_page, title="Facility Watchlist", icon="⚠️"),
        st.Page(staffing_quality_page, title="Staffing & Quality", icon="📈"),
    ]
    navigation = st.navigation(pages, position="hidden")
    dashboard_navigation(pages)
    navigation.run()

    # These links render after the page filters, at the bottom of the sidebar content.
    with st.sidebar:
        st.divider()
        st.link_button("View portfolio hub", PORTFOLIO_URL)
        st.link_button("View project code", GITHUB_URL)


if __name__ == "__main__":
    main()
