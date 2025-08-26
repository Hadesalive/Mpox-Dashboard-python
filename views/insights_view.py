from typing import List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.ensemble import IsolationForest

from utils.style import COLOR_SEQ


def insights_tab(df: pd.DataFrame):
    st.subheader("Insights & Recommendations")
    st.caption("Insights prioritize clarity: toggles below refine analytics.")
    enable_anomaly = st.checkbox("Enable anomaly detection (weekly cases)", value=True)

    required = {"country", "confirmed_cases"}
    if not required.issubset(df.columns):
        st.info("Insights require at least country and confirmed_cases.")
        return

    agg = df.copy()
    agg["week"] = agg.get("report_date")
    if "report_date" in agg.columns:
        agg["week"] = pd.to_datetime(agg["report_date"]).dt.to_period("W-SUN").dt.start_time

    # Build a weekly cases dataframe to power anomalies/forecasts even if weekly_new_cases is missing
    weekly: Optional[pd.DataFrame] = None
    if {"country", "week", "weekly_new_cases"}.issubset(agg.columns):
        weekly = agg.dropna(subset=["week"]).groupby(["country", "week"], as_index=False)["weekly_new_cases"].sum()
    elif {"country", "report_date", "confirmed_cases"}.issubset(agg.columns):
        tmp = agg.dropna(subset=["report_date"]).copy()
        tmp["report_date"] = pd.to_datetime(tmp["report_date"]).dt.normalize()
        daily = tmp.groupby(["country", "report_date"], as_index=False)["confirmed_cases"].sum().sort_values(["country", "report_date"]) 
        # For each country, decide if series is cumulative (mostly non-decreasing). If so, use diff; else, use weekly sum.
        weekly_list: List[pd.DataFrame] = []
        for country, grp in daily.groupby("country"):
            grp = grp.sort_values("report_date").copy()
            diffs = grp["confirmed_cases"].diff()
            non_decreasing_ratio = (diffs.fillna(0) >= 0).mean()
            if non_decreasing_ratio >= 0.8:
                # Treat as cumulative; compute incident by diff, floor at 0
                grp["incident"] = grp["confirmed_cases"].diff().fillna(0).clip(lower=0)
            else:
                # Treat as incident counts; use values directly
                grp["incident"] = grp["confirmed_cases"].fillna(0)
            grp["week"] = grp["report_date"].dt.to_period("W-SUN").dt.start_time
            wk = grp.groupby(["country", "week"], as_index=False)["incident"].sum().rename(columns={"incident": "weekly_new_cases"})
            weekly_list.append(wk)
        if weekly_list:
            weekly = pd.concat(weekly_list, ignore_index=True)
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
    with np.errstate(divide='ignore', invalid='ignore'):
        country_latest["cfr_percent"] = (country_latest["total_deaths"] / country_latest["total_cases"]) * 100
        country_latest["deployed_per_case"] = country_latest["deployed_chws"] / country_latest["total_cases"].replace(0, np.nan)
        country_latest["surveillance_per_case"] = (country_latest["sites"] + country_latest["labs"]) / country_latest["total_cases"].replace(0, np.nan)
        country_latest["uptake_rate_pct"] = (country_latest["administered"] / country_latest["allocated"]).replace([np.inf, -np.inf], np.nan) * 100
        country_latest["allocation_per_1000"] = (country_latest["allocated"] / country_latest["total_cases"]) * 1000

    growth = None
    if weekly is not None and not weekly.empty:
        recent = weekly.groupby("country").tail(4)
        growth = recent.groupby("country")["weekly_new_cases"].apply(lambda s: (s.iloc[-1] - s.iloc[0]) / max(s.iloc[0], 1)).rename("growth4w")
        country_latest = country_latest.merge(growth.reset_index(), on="country", how="left")

    def score_row(r):
        s = 0.0
        s += min(r.get("total_cases", 0) / 10000.0, 1.0) * 25
        s += min(r.get("cfr_percent", 0) / 5.0, 1.0) * 25
        dep = r.get("deployed_per_case", np.nan)
        if pd.notna(dep):
            s += min(1.0 / max(dep, 1e-6), 10) / 10 * 15
        surv = r.get("surveillance_per_case", np.nan)
        if pd.notna(surv):
            s += min(1.0 / max(surv, 1e-6), 10) / 10 * 15
        per1000 = r.get("allocation_per_1000", np.nan)
        if pd.notna(per1000):
            s += max(0.0, (1.5 - min(per1000 / 1000.0, 3.0))) / 1.5 * 10
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
    st.caption("Higher score = higher response priority. Score blends burden (cases, CFR), capacity gaps (CHWs, surveillance), equity (allocation vs burden), and recent growth.")

    # Score breakdown and drill-down
    st.markdown("---")
    st.subheader("Score breakdown and drill-down")
    def score_components(r):
        comp = {
            "burden_cases": min(r.get("total_cases", 0) / 10000.0, 1.0) * 25,
            "burden_cfr": min(r.get("cfr_percent", 0) / 5.0, 1.0) * 25,
        }
        dep = r.get("deployed_per_case", np.nan)
        comp["gap_chw_per_case"] = (min(1.0 / max(dep, 1e-6), 10) / 10 * 15) if pd.notna(dep) else 0
        surv = r.get("surveillance_per_case", np.nan)
        comp["gap_surveillance_per_case"] = (min(1.0 / max(surv, 1e-6), 10) / 10 * 15) if pd.notna(surv) else 0
        per1000 = r.get("allocation_per_1000", np.nan)
        comp["equity_allocation"] = (max(0.0, (1.5 - min(per1000 / 1000.0, 3.0))) / 1.5 * 10) if pd.notna(per1000) else 0
        g = r.get("growth4w", 0)
        comp["trend_growth"] = (max(0.0, min(g, 1.0)) * 10) if pd.notna(g) else 0
        return comp

    sel_country = st.selectbox("Select country", options=top["country"].tolist(), index=0, key="insights_sel_country")
    sel_row = top[top["country"] == sel_country].iloc[0].to_dict()
    comps = score_components(sel_row)
    comp_df = pd.DataFrame({"component": list(comps.keys()), "value": list(comps.values())})
    fig_comp = px.bar(comp_df, x="component", y="value", title=f"{sel_country}: score contribution by factor",
                      color="component", color_discrete_sequence=COLOR_SEQ)
    fig_comp.update_layout(height=360, showlegend=False)
    st.plotly_chart(fig_comp, use_container_width=True)
    st.caption("Each component contributes to the priority score: burden (cases, CFR), capacity gaps (CHWs, surveillance), equity (allocation per 1,000 cases), and recent growth.")
    colm1, colm2, colm3 = st.columns(3)
    with colm1:
        st.metric("CFR %", f"{sel_row.get('cfr_percent', np.nan):.2f}")
        st.metric("CHWs per case (deployed)", f"{sel_row.get('deployed_per_case', np.nan):.3f}")
    with colm2:
        st.metric("Surveillance per case", f"{sel_row.get('surveillance_per_case', np.nan):.3f}")
        st.metric("Allocation per 1,000 cases", f"{sel_row.get('allocation_per_1000', np.nan):.0f}")
    with colm3:
        st.metric("Uptake %", f"{sel_row.get('uptake_rate_pct', np.nan):.1f}")
        st.metric("4-week growth", f"{sel_row.get('growth4w', 0.0):.2f}")
    st.caption("CFR: deaths/cases. CHWs/surv per case: higher is better. Allocation per 1,000: vaccine allocation adjusted for burden. Uptake %: administered/allocated.")

    if enable_anomaly and weekly is not None and not weekly.empty:
        st.markdown("---")
        st.subheader("Anomaly detection (weekly cases)")
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
            st.caption("Flags unusual spikes/drops using IsolationForest on level and week-over-week change. Use as a prompt for review, not a definitive alarm.")
        else:
            st.info("No recent anomalies detected (or insufficient data).")

    # Forecasting removed per request

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

    top = country_latest.sort_values("priority_score", ascending=False)
    rec_view = top[["country", "priority_score", "cfr_percent", "deployed_per_case", "surveillance_per_case", "allocation_per_1000", "uptake_rate_pct"]].copy()
    rec_view["recommendations"] = top.apply(rec_for_row, axis=1)
    st.dataframe(rec_view.head(15), use_container_width=True)

    # What-if simulator
    st.markdown("---")
    st.subheader("What-if simulator (per country)")
    sim_country = st.selectbox("Country to simulate", options=top["country"].tolist(), index=0, key="insights_sim_country")
    base = country_latest[country_latest["country"] == sim_country].iloc[0].copy()
    c1, c2, c3 = st.columns(3)
    with c1:
        add_doses = st.slider("Additional allocated doses", 0, 100000, 10000, step=1000, key="insights_add_doses")
    with c2:
        inc_chw_pct = st.slider("Increase deployed CHWs (%)", 0, 200, 20, step=5, key="insights_inc_chw")
    with c3:
        add_labs = st.slider("Add labs (count)", 0, 200, 10, step=5, key="insights_add_labs")

    sim = base.copy()
    sim["allocated"] = base.get("allocated", 0) + add_doses
    sim["deployed_chws"] = base.get("deployed_chws", 0) * (1 + inc_chw_pct / 100.0)
    sim["labs"] = base.get("labs", 0) + add_labs
    with np.errstate(divide='ignore', invalid='ignore'):
        sim["deployed_per_case"] = sim.get("deployed_chws", 0) / max(sim.get("total_cases", 0), 1)
        sim["surveillance_per_case"] = (sim.get("sites", 0) + sim.get("labs", 0)) / max(sim.get("total_cases", 0), 1)
        sim["allocation_per_1000"] = (sim.get("allocated", 0) / max(sim.get("total_cases", 0), 1)) * 1000
    sim_score = score_row(sim)
    base_score = base.get("priority_score", 0)
    st.metric("Projected priority score", f"{sim_score:.1f}", delta=f"{sim_score - base_score:+.1f}")
    st.caption("Adjust inputs to see how capacity changes could shift priority score.")

    # Data quality and alerts
    st.markdown("---")
    st.subheader("Data quality & alerts")
    dq = {}
    total_rows = len(df)
    if total_rows > 0:
        if "report_date" in df.columns:
            try:
                max_dt = pd.to_datetime(df["report_date"]).max()
                age_days = (pd.Timestamp.now(tz=max_dt.tz) - max_dt).days if pd.notnull(max_dt) else None
            except Exception:
                age_days = None
            dq["Freshness"] = f"{age_days} days old" if age_days is not None else "n/a"
            if age_days is not None and age_days > 28:
                dq["Freshness"] += " (stale)"
        if "clade" in df.columns:
            unknown = df["clade"].isna() | df["clade"].astype(str).str.lower().eq("unknown")
            dq["Unknown clade %"] = f"{(unknown.mean()*100):.1f}%"
        if "vaccinations_administered" in df.columns:
            dq["Vax missing %"] = f"{df['vaccinations_administered'].isna().mean()*100:.1f}%"
        if "deployed_chws" in df.columns:
            dq["CHW missing %"] = f"{df['deployed_chws'].isna().mean()*100:.1f}%"
        # Consistency checks
        if {"vaccine_dose_allocated", "vaccine_dose_deployed", "vaccinations_administered"}.issubset(df.columns):
            try:
                chk = df[["vaccine_dose_allocated","vaccine_dose_deployed","vaccinations_administered"]].copy()
                neg_any = (chk < 0).any().any()
                over_admin = (chk["vaccinations_administered"] > chk["vaccine_dose_deployed"]).mean()
                over_deploy = (chk["vaccine_dose_deployed"] > chk["vaccine_dose_allocated"]).mean()
                dq["Negatives present"] = "Yes" if neg_any else "No"
                dq[">Administered > Deployed (rows %)"] = f"{over_admin*100:.1f}%"
                dq[">Deployed > Allocated (rows %)"] = f"{over_deploy*100:.1f}%"
            except Exception:
                pass
    cols = st.columns(len(dq) if dq else 1)
    for i, (k, v) in enumerate(dq.items() if dq else [("No data quality metrics", "")]):
        with cols[i]:
            st.markdown(f"**{k}**")
            st.caption(v)

    alerts = []
    if sel_row.get("cfr_percent", 0) > 3:
        alerts.append("High CFR")
    if sel_row.get("allocation_per_1000", 999999) < 2000:
        alerts.append("Under-allocated")
    if sel_row.get("deployed_per_case", 999) < 0.5:
        alerts.append("Low CHW coverage")
    if sel_row.get("surveillance_per_case", 999) < 0.02:
        alerts.append("Low surveillance")
    if alerts:
        st.markdown(" ".join([f"`{a}`" for a in alerts]))
    st.caption("Alerts highlight potential areas requiring action; review alongside context and recent trends.")


