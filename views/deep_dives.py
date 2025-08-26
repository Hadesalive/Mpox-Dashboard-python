from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from utils.style import COLOR_SEQ


def deep_dives_tab(df: pd.DataFrame, context_note: str):
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
        clade_agg = df.dropna(subset=["clade"]).groupby("clade", as_index=False).agg(
            total_cases=("confirmed_cases", "sum") if "confirmed_cases" in df.columns else ("weekly_new_cases", "sum"),
            total_deaths=("deaths", "sum") if "deaths" in df.columns else ("weekly_new_cases", "sum"),
        )
        if not clade_agg.empty and "total_cases" in clade_agg.columns:
            fig_pie = px.pie(clade_agg, names="clade", values="total_cases", title="Proportion of Total Cases by Clade")
            fig_pie.update_layout(height=420)
            st.plotly_chart(fig_pie, use_container_width=True)
            st.caption(f"Distribution of total cases by clade within the selection. {context_note}")

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

    # Data quality note
    dq_msgs = []
    for c in ["vaccine_dose_allocated", "vaccine_dose_deployed", "vaccinations_administered", "active_surveillance_sites", "testing_laboratries"]:
        if c in df.columns:
            miss = df[c].isna().mean()
            if miss > 0:
                dq_msgs.append(f"{c.replace('_',' ').title()} missing: {miss*100:.1f}%")
    if dq_msgs:
        st.caption(" • ".join(dq_msgs))


