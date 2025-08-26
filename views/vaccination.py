import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from utils.style import COLOR_SEQ


def vaccination_tab(df: pd.DataFrame, context_note: str):
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
    st.caption(f"ℹ️ Flow shows Allocated → Deployed → Administered doses by country. {context_note}")

    st.markdown("---")
    st.subheader("Rates (%)")
    rate_cols = ["deployment_rate_pct", "administration_rate_pct", "uptake_rate_pct"]
    rate_df = agg.sort_values("uptake_rate_pct", ascending=True)
    fig2 = px.bar(rate_df, y="country", x=rate_cols, orientation="h", barmode="group",
                  title="Deployment, Administration, Uptake Rates")
    fig2.update_layout(height=520)
    st.plotly_chart(fig2, use_container_width=True)
    st.caption(f"ℹ️ Deployment % = Deployed/Allocated; Administration % = Administered/Deployed; Uptake % = Administered/Allocated. {context_note}")

    # Data quality and alerts
    dq_msgs = []
    for c in ["vaccine_dose_allocated", "vaccine_dose_deployed", "vaccinations_administered"]:
        if c in df.columns:
            miss = df[c].isna().mean()
            if miss > 0:
                dq_msgs.append(f"{c.replace('_',' ').title()} missing: {miss*100:.1f}%")
    if dq_msgs:
        st.caption(" • ".join(dq_msgs))

    # Lightweight alert: negative stock or implausible rates
    if needed.issubset(df.columns):
        chk = agg.copy()
        chk["undeployed"] = chk["allocated"] - chk["deployed"]
        chk["not_admin"] = chk["deployed"] - chk["administered"]
        alerts = []
        if (chk[["allocated","deployed","administered"]] < 0).any().any():
            alerts.append("Negative values detected")
        if (chk["deployment_rate_pct"] > 110).any() or (chk["administration_rate_pct"] > 110).any():
            alerts.append("Rates exceed 110% (possible data issue)")
        if (chk["not_admin"] < -1).any():
            alerts.append("Administered exceeds deployed in some countries")
        if alerts:
            st.caption("Alerts: " + " • ".join(alerts))


