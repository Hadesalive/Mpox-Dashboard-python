import os
from datetime import datetime
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.ensemble import IsolationForest
from statsmodels.tsa.statespace.sarimax import SARIMAX
from utils.data import load_data, filter_data, make_filter_note
from utils.style import apply_base_theme, COLOR_SEQ
from views.geography import geography_tab
from views.vaccination import vaccination_tab
from views.workforce import workforce_tab
from views.deep_dives import deep_dives_tab
from views.insights_view import insights_tab
from views.recommendations import recommendations_tab
from views.findings import findings_tab


# -----------------------------
# App configuration
# -----------------------------
st.set_page_config(
    page_title="Mpox Africa Dashboard",
    page_icon="🦠",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_base_theme()


@st.cache_data(show_spinner=False)
def _load_data_cached(default_path: str, uploaded_file: Optional[bytes]):
    return load_data(default_path, uploaded_file)


def build_sidebar(df) -> Tuple[Optional[Tuple[datetime, datetime]], List[str], List[str], List[str]]:
    st.sidebar.header("Filters")

    # Date range
    date_range = None
    with st.sidebar.expander("Date & Time", expanded=True):
        if "report_date" in df.columns and not df["report_date"].isna().all():
            min_dt = st.session_state.get("_min_dt") or df["report_date"].min()
            max_dt = st.session_state.get("_max_dt") or df["report_date"].max()
            st.session_state["_min_dt"], st.session_state["_max_dt"] = min_dt, max_dt
            start_dt, end_dt = st.slider(
                "Report date range",
                min_value=min_dt.to_pydatetime(),
                max_value=max_dt.to_pydatetime(),
                value=(min_dt.to_pydatetime(), max_dt.to_pydatetime()),
                key="date_range_slider",
            )
            date_range = (start_dt, end_dt)

    # Country filter
    countries: List[str] = []
    with st.sidebar.expander("Geography"):
        if "country" in df.columns:
            all_countries = sorted([c for c in df["country"].dropna().unique().tolist()])
            countries = st.multiselect("Countries", options=all_countries, default=[], key="countries_multiselect")

    # Clade filter
    clades: List[str] = []
    with st.sidebar.expander("Pathogen"):
        if "clade" in df.columns:
            all_clades = sorted([c for c in df["clade"].fillna("Unknown").unique().tolist()])
            clades = st.multiselect("Clades", options=all_clades, default=[], key="clades_multiselect")

    # Notes filter
    notes: List[str] = []
    with st.sidebar.expander("Surveillance"):
        if "surveillance_notes" in df.columns:
            all_notes = sorted([n for n in df["surveillance_notes"].dropna().unique().tolist()])
            notes = st.multiselect("Surveillance notes", options=all_notes, default=[], key="notes_multiselect")

    # Reset filters button
    if st.sidebar.button("Reset filters"):
        for k in ["date_range_slider", "countries_multiselect", "clades_multiselect", "notes_multiselect"]:
            if k in st.session_state:
                del st.session_state[k]
        st.experimental_rerun()
    return date_range, countries, clades, notes


def main():
    try:
        st.markdown("<h1>Mpox Africa Dashboard</h1>", unsafe_allow_html=True)
        st.caption("Interactive insights on outbreak trends, vaccination progress, surveillance, and workforce capacity.")

        # Debug: Show current working directory and available files
        st.info(f"Current working directory: {os.getcwd()}")
        try:
            files = os.listdir(".")
            st.info(f"Available files: {files}")
        except Exception as e:
            st.error(f"Error listing files: {e}")

        # Try multiple paths for deployment compatibility
        possible_paths = [
            "mpox_africa_dataset.xlsx",  # Current directory
            os.path.join(os.path.dirname(__file__), "mpox_africa_dataset.xlsx"),  # Script directory
            os.path.join(os.getcwd(), "mpox_africa_dataset.xlsx")  # Working directory
        ]
        
        st.info(f"Trying paths: {possible_paths}")
        
        default_data_path = None
        for path in possible_paths:
            if os.path.exists(path):
                default_data_path = path
                st.success(f"Found dataset at: {path}")
                break
        
        if default_data_path is None:
            st.error("Dataset file not found. Please ensure 'mpox_africa_dataset.xlsx' is in the project directory.")
            st.info("Available files in directory:")
            try:
                files = os.listdir(".")
                st.write(files)
            except Exception as e:
                st.write(f"Error listing files: {e}")
            return

        st.sidebar.header("Data")
        uploaded = st.sidebar.file_uploader("Upload Excel (.xlsx) to override", type=["xlsx"], key="data_upload")

        try:
            df = _load_data_cached(default_data_path, uploaded)
            st.success(f"Data loaded successfully! Shape: {df.shape}")
        except FileNotFoundError:
            st.error("Default dataset not found. Please upload an Excel file using the sidebar.")
            return
        except Exception as e:
            st.exception(e)
            st.error(f"Error loading data: {str(e)}")
            return

        date_range, countries, clades, notes = build_sidebar(df)
        filtered = filter_data(df, date_range, countries, clades, notes)
        context_note = make_filter_note(date_range, countries, clades, notes)

        st.success(f"Data filtered successfully! Filtered shape: {filtered.shape}")

        tabs = st.tabs(["Findings", "Geography", "Vaccination", "Workforce", "Deep Dives", "Insights", "Recommendations"])
        with tabs[0]:
            findings_tab(filtered, context_note)
        with tabs[1]:
            geography_tab(filtered, context_note)
        with tabs[2]:
            vaccination_tab(filtered, context_note)
        with tabs[3]:
            workforce_tab(filtered, context_note)
        with tabs[4]:
            deep_dives_tab(filtered, context_note)
        with tabs[5]:
            insights_tab(filtered)
        with tabs[6]:
            recommendations_tab(filtered, context_note)

        st.markdown("---")
        with st.expander("Data preview"):
            st.dataframe(filtered.head(200))
            st.download_button("Download filtered CSV", data=filtered.to_csv(index=False).encode("utf-8"), file_name="filtered_data.csv", mime="text/csv")
    
    except Exception as e:
        st.error(f"An error occurred while running the dashboard: {str(e)}")
        st.exception(e)
        st.info("Please check the logs for more details or try refreshing the page.")


if __name__ == "__main__":
    main()


def legacy_geography_tab(df: pd.DataFrame, context_note: str):
    if not {"country", "confirmed_cases"}.issubset(df.columns):
        st.info("Geography view requires 'country' and 'confirmed_cases' columns.")
        return
    agg = df.groupby("country", as_index=False).agg(
        confirmed_cases=("confirmed_cases", "sum"),
        deaths=("deaths", "sum") if "deaths" in df.columns else ("confirmed_cases", "sum"),
    )
    fig = px.choropleth(
        agg,
        locations="country",
        locationmode="country names",
        color="confirmed_cases",
        color_continuous_scale="Greens",
        scope="africa",
        title="Confirmed Cases by Country",
        hover_name="country",
        hover_data={"confirmed_cases": ":,", "deaths": ":,"},
    )
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=50, b=0))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Choropleth of confirmed cases across Africa. {context_note}")


def legacy_vaccination_tab(df: pd.DataFrame, context_note: str):
    needed = {"country", "vaccine_dose_allocated", "vaccine_dose_deployed", "vaccinations_administered"}
    if not needed.issubset(df.columns):
        st.info("Vaccination view requires allocation, deployment, and administered columns.")
        return
    agg = df.groupby("country", as_index=False).agg(
        allocated=("vaccine_dose_allocated", "sum"),
        deployed=("vaccine_dose_deployed", "sum"),
        administered=("vaccinations_administered", "sum"),
    )
    agg["deployment_rate_pct"] = (agg["deployed"] / agg["allocated"]).replace([np.inf, -np.inf], np.nan) * 100
    agg["administration_rate_pct"] = (agg["administered"] / agg["deployed"]).replace([np.inf, -np.inf], np.nan) * 100
    agg["uptake_rate_pct"] = (agg["administered"] / agg["allocated"]).replace([np.inf, -np.inf], np.nan) * 100

    st.subheader("Allocation vs Deployment vs Administration")
    melted = agg.melt(id_vars=["country"], value_vars=["allocated", "deployed", "administered"],
                      var_name="stage", value_name="doses")
    fig = px.bar(melted, x="country", y="doses", color="stage", barmode="group", title="Vaccine Flow by Country",
                 color_discrete_sequence=COLOR_SEQ)
    fig.update_layout(xaxis_tickangle=-30, height=460)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Allocated → Deployed → Administered doses by country. {context_note}")

    st.markdown("---")
    st.subheader("Rates (%)")
    rate_cols = ["deployment_rate_pct", "administration_rate_pct", "uptake_rate_pct"]
    rate_df = agg.sort_values("uptake_rate_pct", ascending=True)
    fig2 = px.bar(rate_df, y="country", x=rate_cols, orientation="h", barmode="group",
                  title="Deployment, Administration, Uptake Rates")
    fig2.update_layout(height=520)
    st.plotly_chart(fig2, use_container_width=True)
    st.caption(f"Rates derived from selected countries and dates. {context_note}")


def legacy_workforce_tab(df: pd.DataFrame, context_note: str):
    has_cols = {"country", "trained_chws", "deployed_chws", "confirmed_cases"}.issubset(df.columns)
    if not has_cols:
        st.info("Workforce view requires trained/deployed CHWs and confirmed cases.")
        return
    agg = df.groupby("country", as_index=False).agg(
        trained=("trained_chws", "sum"),
        deployed=("deployed_chws", "sum"),
        cases=("confirmed_cases", "sum"),
    )
    agg["deployed_per_case"] = (agg["deployed"] / agg["cases"]).replace([np.inf, -np.inf], np.nan)
    agg["trained_per_case"] = (agg["trained"] / agg["cases"]).replace([np.inf, -np.inf], np.nan)

    cols = st.columns(2)
    with cols[0]:
        fig = px.bar(agg.sort_values("deployed_per_case"), x="country", y="deployed_per_case",
                     title="Deployed CHWs per Case")
        fig.update_layout(xaxis_tickangle=-30, height=460)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Deployed CHWs normalized per case. {context_note}")
    with cols[1]:
        fig2 = px.bar(agg.sort_values("trained_per_case"), x="country", y="trained_per_case",
                      title="Trained CHWs per Case")
        fig2.update_layout(xaxis_tickangle=-30, height=460)
        st.plotly_chart(fig2, use_container_width=True)
        st.caption(f"Trained CHWs normalized per case. {context_note}")


def legacy_build_sidebar(df: pd.DataFrame) -> Tuple[Optional[Tuple[datetime, datetime]], List[str], List[str], List[str]]:
    st.sidebar.header("Filters")

    # Date range
    date_range = None
    with st.sidebar.expander("Date & Time", expanded=True):
        if "report_date" in df.columns and not df["report_date"].isna().all():
            min_dt = pd.to_datetime(df["report_date"].min())
            max_dt = pd.to_datetime(df["report_date"].max())
            start_dt, end_dt = st.slider(
                "Report date range",
                min_value=min_dt.to_pydatetime(),
                max_value=max_dt.to_pydatetime(),
                value=(min_dt.to_pydatetime(), max_dt.to_pydatetime()),
            )
            date_range = (start_dt, end_dt)

    # Country filter
    countries = []
    with st.sidebar.expander("Geography"):
        if "country" in df.columns:
            all_countries = sorted([c for c in df["country"].dropna().unique().tolist()])
            countries = st.multiselect("Countries", options=all_countries, default=[])

    # Clade filter
    clades = []
    with st.sidebar.expander("Pathogen"):
        if "clade" in df.columns:
            all_clades = sorted([c for c in df["clade"].fillna("Unknown").unique().tolist()])
            clades = st.multiselect("Clades", options=all_clades, default=[])

    # Notes filter
    notes = []
    with st.sidebar.expander("Surveillance"):
        if "surveillance_notes" in df.columns:
            all_notes = sorted([n for n in df["surveillance_notes"].dropna().unique().tolist()])
            notes = st.multiselect("Surveillance notes", options=all_notes, default=[])

    return date_range, countries, clades, notes


def legacy_main():
    st.markdown("<h1>Mpox Africa Dashboard</h1>", unsafe_allow_html=True)
    st.caption("Interactive insights on outbreak trends, vaccination progress, surveillance, and workforce capacity.")

    default_data_path = os.path.join(os.path.dirname(__file__), "mpox_africa_dataset.xlsx")

    st.sidebar.header("Data")
    uploaded = st.sidebar.file_uploader("Upload Excel (.xlsx) to override", type=["xlsx"])

    try:
        df = _load_data_cached(default_data_path, uploaded)
    except FileNotFoundError:
        st.error("Default dataset not found. Please upload an Excel file using the sidebar.")
        return
    except Exception as e:
        st.exception(e)
        return

    date_range, countries, clades, notes = build_sidebar(df)
    filtered = filter_data(df, date_range, countries, clades, notes)
    context_note = make_filter_note(date_range, countries, clades, notes)

    tabs = st.tabs(["Overview", "Geography", "Vaccination", "Workforce", "Deep Dives", "Insights"])
    with tabs[0]:
        overview_tab(filtered, context_note)
    with tabs[1]:
        geography_tab(filtered, context_note)
    with tabs[2]:
        vaccination_tab(filtered, context_note)
    with tabs[3]:
        workforce_tab(filtered, context_note)
    with tabs[4]:
        deep_dives_tab(filtered, context_note)
    with tabs[5]:
        insights_tab(filtered)

    st.markdown("---")
    with st.expander("Data preview"):
        st.dataframe(filtered.head(200))


def legacy_deep_dives_tab(df: pd.DataFrame, context_note: str):
    st.subheader("Allocation vs Uptake (per Country)")
    needed_vax = {"country", "vaccine_dose_allocated", "vaccine_dose_deployed", "vaccinations_administered"}
    if needed_vax.issubset(df.columns):
        vax = df.groupby("country", as_index=False).agg(
            allocated=("vaccine_dose_allocated", "sum"),
            deployed=("vaccine_dose_deployed", "sum"),
            administered=("vaccinations_administered", "sum"),
            confirmed_cases=("confirmed_cases", "sum") if "confirmed_cases" in df.columns else ("vaccine_dose_allocated", "sum"),
        )
        vax["uptake_rate_pct"] = (vax["administered"] / vax["allocated"]).replace([np.inf, -np.inf], np.nan) * 100
        fig = px.scatter(
            vax,
            x="allocated",
            y="uptake_rate_pct",
            size="confirmed_cases",
            hover_name="country",
            color="country",
            title="Vaccine Allocation vs Uptake Rate",
            labels={"allocated": "Allocated Doses", "uptake_rate_pct": "Uptake Rate (%)"},
        )
        fig.update_layout(height=460, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Higher uptake at similar allocation suggests stronger in-country utilization. {context_note}")
    else:
        st.info("Need allocation, deployment, administered columns for this view.")

    st.markdown("---")
    st.subheader("Stock Bottlenecks Heatmap")
    if needed_vax.issubset(df.columns):
        stock = df.groupby("country", as_index=False).agg(
            allocated=("vaccine_dose_allocated", "sum"),
            deployed=("vaccine_dose_deployed", "sum"),
            administered=("vaccinations_administered", "sum"),
        )
        stock["undeployed_stock"] = stock["allocated"] - stock["deployed"]
        stock["in_country_not_admin"] = stock["deployed"] - stock["administered"]
        heat_df = stock.set_index("country")[
            ["undeployed_stock", "in_country_not_admin"]
        ]
        heat_df = heat_df.replace([np.inf, -np.inf], np.nan).fillna(0)
        fig_hm = px.imshow(
            heat_df.values,
            x=["Undeployed stock", "In-country not administered"],
            y=heat_df.index.tolist(),
            color_continuous_scale="YlOrRd",
            labels=dict(color="Doses"),
            title="Vaccine Stock Bottlenecks",
            aspect="auto",
        )
        fig_hm.update_layout(height=520)
        st.plotly_chart(fig_hm, use_container_width=True)
        st.caption(f"Where stock is stuck: central vs last-mile in-country. {context_note}")
    else:
        st.info("Need allocation, deployment, administered columns for this view.")

    st.markdown("---")
    cols = st.columns(2)
    with cols[0]:
        st.subheader("Surveillance vs CFR (Bubble)")
        # Relaxed requirements: need country and confirmed_cases, and at least one of sites/labs, and either deaths or CFR
        has_cases = {"country", "confirmed_cases"}.issubset(df.columns)
        has_sites = "active_surveillance_sites" in df.columns
        has_labs = "testing_laboratries" in df.columns
        has_deaths = "deaths" in df.columns
        has_cfr = "case_fatality_rate" in df.columns
        if has_cases and (has_sites or has_labs) and (has_deaths or has_cfr):
            agg_spec = {"cases": ("confirmed_cases", "sum")}
            if has_sites:
                agg_spec["sites"] = ("active_surveillance_sites", "sum")
            if has_labs:
                agg_spec["labs"] = ("testing_laboratries", "sum")
            if has_deaths:
                agg_spec["deaths"] = ("deaths", "sum")
            surv = df.groupby("country", as_index=False).agg(**agg_spec)
            surv["sites"] = surv.get("sites", pd.Series(0, index=surv.index)).fillna(0)
            surv["labs"] = surv.get("labs", pd.Series(0, index=surv.index)).fillna(0)
            surv["surveillance_per_case"] = (surv["sites"] + surv["labs"]) / surv["cases"].replace(0, np.nan)
            if has_deaths:
                surv["cfr_percent"] = (surv["deaths"] / surv["cases"]).replace([np.inf, -np.inf], np.nan) * 100
            else:
                # Use average CFR per country if deaths not available
                cfr_avg = df.groupby("country")["case_fatality_rate"].mean().rename("cfr_percent").reset_index()
                surv = surv.merge(cfr_avg, on="country", how="left")
            fig_bubble = px.scatter(
                surv.dropna(subset=["surveillance_per_case", "cfr_percent"]),
                x="surveillance_per_case",
                y="cfr_percent",
                size="cases",
                color="country",
                hover_name="country",
                title="Surveillance Capacity vs CFR",
                labels={"surveillance_per_case": "(Sites + Labs) per Case", "cfr_percent": "CFR (%)"},
            )
            fig_bubble.update_layout(height=460, showlegend=False)
            st.plotly_chart(fig_bubble, use_container_width=True)
            st.caption(f"More surveillance per case generally aligns with lower CFR. {context_note}")
        else:
            st.info("Showing surveillance vs CFR requires cases plus at least one of surveillance sites or labs, and deaths or CFR.")

    with cols[1]:
        st.subheader("Workforce & Surveillance Heatmap")
        # Relaxed: require country and confirmed_cases, plus at least one of trained/deployed/sites/labs
        has_cases2 = {"country", "confirmed_cases"}.issubset(df.columns)
        available_fields = [c for c in ["trained_chws", "deployed_chws", "active_surveillance_sites", "testing_laboratries"] if c in df.columns]
        if has_cases2 and available_fields:
            agg = {"cases": ("confirmed_cases", "sum")}
            if "trained_chws" in available_fields:
                agg["trained"] = ("trained_chws", "sum")
            if "deployed_chws" in available_fields:
                agg["deployed"] = ("deployed_chws", "sum")
            if "active_surveillance_sites" in available_fields:
                agg["sites"] = ("active_surveillance_sites", "sum")
            if "testing_laboratries" in available_fields:
                agg["labs"] = ("testing_laboratries", "sum")
            wk = df.groupby("country", as_index=False).agg(**agg)
            heat_cols = []
            if "trained" in wk.columns:
                wk["trained_per_case"] = wk["trained"] / wk["cases"].replace(0, np.nan)
                heat_cols.append("trained_per_case")
            if "deployed" in wk.columns:
                wk["deployed_per_case"] = wk["deployed"] / wk["cases"].replace(0, np.nan)
                heat_cols.append("deployed_per_case")
            if "sites" in wk.columns or "labs" in wk.columns:
                wk["sites"] = wk.get("sites", pd.Series(0, index=wk.index)).fillna(0)
                wk["labs"] = wk.get("labs", pd.Series(0, index=wk.index)).fillna(0)
                wk["surveillance_per_case"] = (wk["sites"] + wk["labs"]) / wk["cases"].replace(0, np.nan)
                heat_cols.append("surveillance_per_case")
            if heat_cols:
                heat2 = wk.set_index("country")[heat_cols].replace([np.inf, -np.inf], np.nan).fillna(0)
                fig_hm2 = px.imshow(
                    heat2.values,
                    x=[
                        "Deployed per case" if c == "deployed_per_case" else (
                            "Trained per case" if c == "trained_per_case" else "Surveillance per case"
                        ) for c in heat_cols
                    ],
                    y=heat2.index.tolist(),
                    color_continuous_scale="Blues",
                    labels=dict(color="Ratio"),
                    title="Per-case Workforce & Surveillance",
                    aspect="auto",
                )
                fig_hm2.update_layout(height=520)
                st.plotly_chart(fig_hm2, use_container_width=True)
                st.caption(f"Per-case workforce and surveillance ratios by country. {context_note}")
            else:
                st.info("No workforce/surveillance metrics available to compute ratios.")
        else:
            st.info("Requires cases and at least one of trained CHWs, deployed CHWs, sites, or labs.")

    st.markdown("---")
    st.subheader("Clade Distribution and Trends")
    if "clade" in df.columns:
        # Distribution
        clade_agg = df.dropna(subset=["clade"]).groupby("clade", as_index=False).agg(
            total_cases=("confirmed_cases", "sum") if "confirmed_cases" in df.columns else ("weekly_new_cases", "sum"),
            total_deaths=("deaths", "sum") if "deaths" in df.columns else ("weekly_new_cases", "sum"),
        )
        if not clade_agg.empty and "total_cases" in clade_agg.columns:
            fig_pie = px.pie(clade_agg, names="clade", values="total_cases", title="Proportion of Total Cases by Clade")
            fig_pie.update_layout(height=420)
            st.plotly_chart(fig_pie, use_container_width=True)
            st.caption(f"Distribution of total cases by clade within the selection. {context_note}")

        # Trend
        if {"report_date", "weekly_new_cases"}.issubset(df.columns) and not df["report_date"].isna().all():
            trend = df.dropna(subset=["report_date"]).copy()
            trend["clade"] = trend["clade"].fillna("Unknown")
            trend = trend.groupby(["report_date", "clade"], as_index=False)["weekly_new_cases"].sum()
            fig_trend = px.line(trend, x="report_date", y="weekly_new_cases", color="clade", title="Weekly Cases by Clade")
            fig_trend.update_layout(height=420)
            st.plotly_chart(fig_trend, use_container_width=True)
            st.caption(f"Weekly cases split by clade over time. {context_note}")
    else:
        st.info("No clade information available in data.")

    st.markdown("---")
    cols2 = st.columns(2)
    with cols2[0]:
        st.subheader("Top Clade-Country Combinations by CFR")
        if {"country", "clade", "confirmed_cases", "deaths"}.issubset(df.columns):
            ccc = df.dropna(subset=["clade"]).groupby(["country", "clade"], as_index=False).agg(
                total_confirmed=("confirmed_cases", "sum"),
                total_deaths=("deaths", "sum"),
            )
            ccc = ccc[ccc["total_confirmed"] > 0]
            ccc["cfr_percent"] = (ccc["total_deaths"] / ccc["total_confirmed"]) * 100
            top_ccc = ccc.sort_values("cfr_percent", ascending=False).head(10)
            top_ccc["label"] = top_ccc["country"] + " • " + top_ccc["clade"].astype(str)
            fig_ccc = px.bar(top_ccc, x="label", y="cfr_percent", color="country",
                             labels={"label": "Country • Clade", "cfr_percent": "CFR (%)"},
                             color_discrete_sequence=COLOR_SEQ)
            fig_ccc.update_layout(xaxis_tickangle=-30, height=460)
            st.plotly_chart(fig_ccc, use_container_width=True)
        else:
            st.info("Need clade, cases and deaths columns.")

    with cols2[1]:
        st.subheader("Unknown Clade Countries (Confirmed Cases)")
        if "country" in df.columns and "clade" in df.columns and "confirmed_cases" in df.columns:
            unk = df[df["clade"].isna() | df["clade"].str.lower().eq("unknown")]
            if not unk.empty:
                unk_agg = unk.groupby("country", as_index=False)["confirmed_cases"].sum().sort_values("confirmed_cases", ascending=False).head(12)
                fig_unk = px.bar(unk_agg, x="country", y="confirmed_cases", color_discrete_sequence=["#F59E0B"],
                                  labels={"confirmed_cases": "Confirmed"})
                fig_unk.update_layout(height=460)
                st.plotly_chart(fig_unk, use_container_width=True)
                st.caption(f"Countries with unknown clade reporting; improves with better genomics. {context_note}")
            else:
                st.info("No unknown clade records.")
        else:
            st.info("Need clade and confirmed cases columns.")

    st.markdown("---")
    cols3 = st.columns(2)
    with cols3[0]:
        st.subheader("Deployed vs Administered by Country")
        if {"country", "vaccine_dose_deployed", "vaccinations_administered"}.issubset(df.columns):
            vac = df.groupby("country", as_index=False).agg(
                deployed=("vaccine_dose_deployed", "sum"),
                administered=("vaccinations_administered", "sum"),
            ).sort_values("deployed", ascending=False)
            vac_m = vac.melt(id_vars=["country"], value_vars=["deployed", "administered"], var_name="stage", value_name="doses")
            fig_lines = px.line(vac_m, x="country", y="doses", color="stage", markers=True, color_discrete_sequence=COLOR_SEQ)
            fig_lines.update_layout(xaxis_tickangle=-30, height=420)
            st.plotly_chart(fig_lines, use_container_width=True)
            st.caption(f"Deployed vs administered doses by country. {context_note}")
        else:
            st.info("Need deployed and administered columns.")

    with cols3[1]:
        st.subheader("Allocation Efficiency (per 1,000 Cases)")
        if {"country", "vaccine_dose_allocated", "confirmed_cases"}.issubset(df.columns):
            eff = df.groupby("country", as_index=False).agg(
                allocated=("vaccine_dose_allocated", "sum"),
                confirmed=("confirmed_cases", "sum"),
                administered=("vaccinations_administered", "sum") if "vaccinations_administered" in df.columns else ("vaccine_dose_allocated", "sum"),
            )
            eff = eff[eff["confirmed"] > 0]
            eff["per_1000"] = (eff["allocated"] / eff["confirmed"]) * 1000
            fig_eff = px.scatter(eff, x="confirmed", y="per_1000", size="administered", hover_name="country",
                                 labels={"confirmed": "Confirmed Cases", "per_1000": "Allocated per 1,000 Cases"},
                                 color_discrete_sequence=["#06B6D4"])
            fig_eff.update_layout(height=420)
            st.plotly_chart(fig_eff, use_container_width=True)
            st.caption(f"Allocation per 1,000 cases vs burden; bubble ~ administered. {context_note}")
        else:
            st.info("Need allocated and confirmed cases columns.")

    st.markdown("---")
    st.subheader("Country Trends with Surveillance Notes")
    if {"country", "report_date", "weekly_new_cases"}.issubset(df.columns):
        default_sel = [c for c in ["Sierra Leone", "Uganda"] if "country" in df.columns and c in df["country"].unique()]
        selected = st.multiselect("Select countries", options=sorted(df["country"].dropna().unique().tolist()), default=default_sel)
        if selected:
            dsel = df[df["country"].isin(selected)].dropna(subset=["report_date"]).copy()
            dsel["surveillance_notes"] = dsel.get("surveillance_notes", pd.Series(index=dsel.index)).fillna("")
            fig_tr = px.line(dsel, x="report_date", y="weekly_new_cases", color="country",
                             hover_data=["surveillance_notes"], color_discrete_sequence=COLOR_SEQ,
                             title="Weekly Cases with Surveillance Notes (hover to see notes)")
            fig_tr.update_layout(height=420)
            st.plotly_chart(fig_tr, use_container_width=True)
            st.caption(f"Hover points to read surveillance notes. {context_note}")
        else:
            st.info("Select at least one country to see trends.")

def legacy_insights_tab(df: pd.DataFrame):
    st.subheader("Insights & Recommendations")
    # Controls
    col_tog1, col_tog2 = st.columns(2)
    with col_tog1:
        enable_forecast = st.checkbox("Enable 4-week case forecasts (SARIMAX)", value=False)
    with col_tog2:
        enable_anomaly = st.checkbox("Enable anomaly detection", value=True)

    # Aggregate country metrics
    required = {"country", "confirmed_cases"}
    if not required.issubset(df.columns):
        st.info("Insights require at least country and confirmed_cases.")
        return

    agg = df.copy()
    agg["week"] = agg.get("report_date")
    if "report_date" in agg.columns:
        agg["week"] = pd.to_datetime(agg["report_date"]).dt.to_period("W-SUN").dt.start_time
    country_latest = agg.groupby("country", as_index=False).agg(
        total_cases=("confirmed_cases", "sum"),
        total_deaths=("deaths", "sum") if "deaths" in agg.columns else ("confirmed_cases", "sum"),
        allocated=("vaccine_dose_allocated", "sum") if "vaccine_dose_allocated" in agg.columns else ("confirmed_cases", "sum"),
        deployed=("vaccine_dose_deployed", "sum") if "vaccine_dose_deployed" in agg.columns else ("confirmed_cases", "sum"),
        administered=("vaccinations_administered", "sum") if "vaccinations_administered" in agg.columns else ("confirmed_cases", "sum"),
        trained=("trained_chws", "sum") if "trained_chws" in agg.columns else ("confirmed_cases", "sum"),
        deployed_chws=("deployed_chws", "sum") if "deployed_chws" in agg.columns else ("confirmed_cases", "sum"),
        sites=("active_surveillance_sites", "sum") if "active_surveillance_sites" in agg.columns else ("confirmed_cases", "sum"),
        labs=("testing_laboratries", "sum") if "testing_laboratries" in agg.columns else ("confirmed_cases", "sum"),
        latest_coverage=("vaccine_coverage", "max") if "vaccine_coverage" in agg.columns else ("confirmed_cases", "sum"),
    )
    # Derived ratios
    with np.errstate(divide='ignore', invalid='ignore'):
        country_latest["cfr_percent"] = (country_latest["total_deaths"] / country_latest["total_cases"]) * 100
        country_latest["deployed_per_case"] = country_latest["deployed_chws"] / country_latest["total_cases"].replace(0, np.nan)
        country_latest["surveillance_per_case"] = (country_latest["sites"] + country_latest["labs"]) / country_latest["total_cases"].replace(0, np.nan)
        country_latest["uptake_rate_pct"] = (country_latest["administered"] / country_latest["allocated"]).replace([np.inf, -np.inf], np.nan) * 100
        country_latest["allocation_per_1000"] = (country_latest["allocated"] / country_latest["total_cases"]) * 1000

    # Trend features: recent 4 weeks growth in weekly_new_cases if available
    growth = None
    if {"week", "weekly_new_cases", "country"}.issubset(agg.columns):
        weekly = agg.dropna(subset=["week"]).groupby(["country", "week"], as_index=False)["weekly_new_cases"].sum()
        recent = weekly.groupby("country").tail(4)
        growth = recent.groupby("country")["weekly_new_cases"].apply(lambda s: (s.iloc[-1] - s.iloc[0]) / max(s.iloc[0], 1)).rename("growth4w")
        country_latest = country_latest.merge(growth.reset_index(), on="country", how="left")

    # Rule-based score (0-100)
    def score_row(r):
        s = 0.0
        # Burden
        s += min(r.get("total_cases", 0) / 10000.0, 1.0) * 25
        s += min(r.get("cfr_percent", 0) / 5.0, 1.0) * 25
        # Capacity gaps
        dep = r.get("deployed_per_case", np.nan)
        if pd.notna(dep):
            s += min(1.0 / max(dep, 1e-6), 10) / 10 * 15
        surv = r.get("surveillance_per_case", np.nan)
        if pd.notna(surv):
            s += min(1.0 / max(surv, 1e-6), 10) / 10 * 15
        # Vaccine equity
        per1000 = r.get("allocation_per_1000", np.nan)
        if pd.notna(per1000):
            s += max(0.0, (1.5 - min(per1000 / 1000.0, 3.0))) / 1.5 * 10
        # Trend
        g = r.get("growth4w", 0)
        if pd.notna(g):
            s += max(0.0, min(g, 1.0)) * 10
        return max(0.0, min(100.0, s))

    country_latest["priority_score"] = country_latest.apply(score_row, axis=1)
    top = country_latest.sort_values("priority_score", ascending=False)

    st.subheader("Priority ranking (rule-based)")
    fig_score = px.bar(top.head(10), x="country", y="priority_score", color="country", color_discrete_sequence=COLOR_SEQ,
                       title="Top Countries by Priority Score")
    fig_score.update_layout(height=420, showlegend=False)
    st.plotly_chart(fig_score, use_container_width=True)

    # Anomalies
    if enable_anomaly and {"week", "weekly_new_cases"}.issubset(agg.columns):
        st.markdown("---")
        st.subheader("Anomaly detection (weekly cases)")
        weekly = agg.dropna(subset=["week"]).groupby(["country", "week"], as_index=False)["weekly_new_cases"].sum()
        # Fit per-country isolation forest on simple features: change vs prev week
        anomalies = []
        for country, grp in weekly.groupby("country"):
            if len(grp) < 6:
                continue
            grp = grp.sort_values("week")
            grp["diff"] = grp["weekly_new_cases"].diff().fillna(0)
            X = grp[["weekly_new_cases", "diff"]].values
            try:
                iso = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
                grp["anomaly"] = iso.fit_predict(X)
                flagged = grp[grp["anomaly"] == -1].tail(3)
                if not flagged.empty:
                    for _, row in flagged.iterrows():
                        anomalies.append({"country": country, "week": row["week"], "weekly_new_cases": row["weekly_new_cases"]})
            except Exception:
                continue
        if anomalies:
            an_df = pd.DataFrame(anomalies)
            fig_an = px.scatter(an_df, x="week", y="weekly_new_cases", color="country",
                                title="Recent anomalous points (weekly cases)", color_discrete_sequence=COLOR_SEQ)
            fig_an.update_layout(height=360)
            st.plotly_chart(fig_an, use_container_width=True)
            st.caption("Flagged by IsolationForest based on level and week-over-week change.")
        else:
            st.info("No recent anomalies detected (or insufficient data).")

    # Forecasts
    if enable_forecast and {"week", "weekly_new_cases"}.issubset(agg.columns):
        st.markdown("---")
        st.subheader("4-week forecasts (experimental)")
        sel_countries = st.multiselect("Select countries for forecasting", options=sorted(agg["country"].dropna().unique().tolist()), default=top.head(3)["country"].tolist())
        for c in sel_countries:
            series = agg[agg["country"] == c].dropna(subset=["week"]).groupby("week")["weekly_new_cases"].sum().asfreq("W-SUN")
            series = series.fillna(0)
            if len(series) < 8:
                st.info(f"{c}: not enough history for forecasting.")
                continue
            try:
                model = SARIMAX(series, order=(1,1,1), seasonal_order=(0,1,1,52), enforce_stationarity=False, enforce_invertibility=False)
                res = model.fit(disp=False)
                fc = res.get_forecast(steps=4)
                pred_ci = fc.conf_int()
                pred = fc.predicted_mean
                df_plot = pd.DataFrame({
                    "week": series.index.tolist() + pred.index.tolist(),
                    "value": series.tolist() + pred.tolist(),
                    "segment": ["history"] * len(series) + ["forecast"] * len(pred)
                })
                fig_fc = px.line(df_plot, x="week", y="value", color="segment", title=f"{c}: Weekly cases forecast", color_discrete_sequence=COLOR_SEQ)
                fig_fc.update_layout(height=360, showlegend=True)
                st.plotly_chart(fig_fc, use_container_width=True)
            except Exception as e:
                st.info(f"{c}: forecasting failed ({e}).")

    # Recommendations (templated)
    st.markdown("---")
    st.subheader("Country recommendations")
    def rec_for_row(r):
        recs = []
        if r.get("cfr_percent", 0) > 3:
            recs.append("Investigate drivers of high CFR; ensure timely care, oxygen, and antivirals.")
        if r.get("deployed_per_case", 1e9) < 0.5:
            recs.append("Surge deploy CHWs; target <500 cases per deployed CHW.")
        if r.get("surveillance_per_case", 1e9) < 0.02:
            recs.append("Expand active sites and labs; aim for higher sites/labs per case.")
        if r.get("allocation_per_1000", 2e9) < 2000:
            recs.append("Advocate for additional vaccine allocation aligned to burden.")
        if r.get("uptake_rate_pct", 100) < 70:
            recs.append("Address last-mile bottlenecks; microplanning and outreach to raise uptake.")
        if len(recs) == 0:
            recs.append("Maintain current response; continue monitoring trends and capacity.")
        return " • ".join(recs)

    rec_view = top[["country", "priority_score", "cfr_percent", "deployed_per_case", "surveillance_per_case", "allocation_per_1000", "uptake_rate_pct"]].copy()
    rec_view["recommendations"] = top.apply(rec_for_row, axis=1)
    st.dataframe(rec_view.head(15), use_container_width=True)

