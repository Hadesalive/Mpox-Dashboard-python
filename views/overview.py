import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


def kpi_card(label: str, value: float):
    st.metric(label=label, value=f"{value:,.0f}" if isinstance(value, (int, float, np.number)) else value)


def compute_rollup(df: pd.DataFrame) -> dict:
    result = {}
    if "confirmed_cases" in df.columns:
        result["total_confirmed"] = float(df["confirmed_cases"].sum())
    if "deaths" in df.columns:
        result["total_deaths"] = float(df["deaths"].sum())
    if {"deaths", "confirmed_cases"}.issubset(df.columns):
        denom = df["confirmed_cases"].sum()
        result["cfr_percent"] = float((df["deaths"].sum() / denom) * 100) if denom else np.nan
    if "vaccinations_administered" in df.columns:
        result["vaccinations_administered"] = float(df["vaccinations_administered"].sum())
    if "vaccine_coverage" in df.columns and "report_date" in df.columns:
        latest = df.sort_values("report_date").dropna(subset=["vaccine_coverage"]).tail(1)
        result["latest_coverage"] = float(latest["vaccine_coverage"].iloc[0]) if len(latest) else np.nan
    return result


def overview_tab(df: pd.DataFrame, context_note: str):
    roll = compute_rollup(df)
    st.subheader("Overview")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        kpi_card("Confirmed", roll.get("total_confirmed", np.nan))
    with col2:
        kpi_card("Deaths", roll.get("total_deaths", np.nan))
    with col3:
        kpi_card("CFR %", roll.get("cfr_percent", np.nan))
    with col4:
        kpi_card("Vaccinations", roll.get("vaccinations_administered", np.nan))
    with col5:
        kpi_card("Latest Coverage %", roll.get("latest_coverage", np.nan))
    st.caption("ℹ️ CFR: deaths/confirmed ×100. Coverage: latest reported vaccine coverage. Values reflect current filters.")

    st.markdown("---")
    left, right = st.columns((2, 1), gap="large")

    if "report_date" in df.columns and "weekly_new_cases" in df.columns and not df["report_date"].isna().all():
        ts = df.dropna(subset=["report_date"]).groupby("report_date", as_index=False)[
            [c for c in ["weekly_new_cases", "confirmed_cases", "deaths"] if c in df.columns]
        ].sum()
        fig = px.line(ts, x="report_date", y=[c for c in ["weekly_new_cases", "confirmed_cases", "deaths"] if c in ts.columns],
                      labels={"value": "Count", "report_date": "Date", "variable": "Metric"},
                      title="Trends Over Time")
        fig.update_layout(height=420, legend=dict(orientation="h"))
        left.plotly_chart(fig, use_container_width=True)
        left.caption(f"Weekly cases/confirmed/deaths over time. {context_note}")

    if "country" in df.columns and "confirmed_cases" in df.columns:
        top_countries = df.groupby("country", as_index=False)[[c for c in ["confirmed_cases", "deaths"] if c in df.columns]].sum()
        top_countries = top_countries.sort_values("confirmed_cases", ascending=False).head(12)
        bar = px.bar(top_countries, x="confirmed_cases", y="country", orientation="h",
                     color=("deaths" if "deaths" in top_countries.columns else None),
                     labels={"confirmed_cases": "Confirmed", "country": "Country", "deaths": "Deaths"},
                     title="Top Countries by Confirmed Cases")
        bar.update_layout(height=420)
        right.plotly_chart(bar, use_container_width=True)
        right.caption(f"Top countries by cumulative confirmed cases. {context_note}")

    # Subtle data quality hints
    dq_bits = []
    if "report_date" in df.columns:
        try:
            max_dt = pd.to_datetime(df["report_date"]).max()
            if pd.notnull(max_dt):
                age_days = (pd.Timestamp.now(tz=max_dt.tz) - max_dt).days
                dq_bits.append(f"Data freshness: {age_days} days old")
        except Exception:
            pass
    for col in ["confirmed_cases", "deaths", "vaccinations_administered"]:
        if col in df.columns:
            miss = df[col].isna().mean()
            if miss > 0:
                dq_bits.append(f"{col.replace('_',' ').title()} missing: {miss*100:.1f}%")
    if dq_bits:
        st.caption(" • ".join(dq_bits))


