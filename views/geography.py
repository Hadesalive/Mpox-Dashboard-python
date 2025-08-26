import pandas as pd
import plotly.express as px
import streamlit as st


def geography_tab(df: pd.DataFrame, context_note: str):
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
    st.caption(f"ℹ️ Choropleth of confirmed cases across Africa. {context_note}")

    # Data quality note: countries with missing cases
    if "country" in df.columns and "confirmed_cases" in df.columns:
        missing_countries = df[df["confirmed_cases"].isna()]["country"].dropna().unique().tolist()
        if missing_countries:
            st.caption(f"Data quality: missing confirmed cases for {len(missing_countries)} countries in selection.")


