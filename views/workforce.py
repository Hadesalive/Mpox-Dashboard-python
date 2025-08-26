import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


def workforce_tab(df: pd.DataFrame, context_note: str):
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

    # Data quality hints
    dq = []
    for c in ["trained_chws", "deployed_chws", "confirmed_cases"]:
        if c in df.columns:
            miss = df[c].isna().mean()
            if miss > 0:
                dq.append(f"{c.replace('_',' ').title()} missing: {miss*100:.1f}%")
    if dq:
        st.caption(" • ".join(dq))


