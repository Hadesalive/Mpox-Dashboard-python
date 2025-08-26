import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from utils.style import COLOR_SEQ
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


@st.cache_data(show_spinner=False)
def _country_summary_cached(df_json: str) -> pd.DataFrame:
    agg = pd.read_json(df_json, orient="records")
    if "report_date" in agg.columns:
        agg["week"] = pd.to_datetime(agg["report_date"]).dt.to_period("W-SUN").dt.start_time
    out = agg.groupby("country", as_index=False).agg(
        total_cases=("confirmed_cases", "sum") if "confirmed_cases" in agg.columns else ("report_date", "count"),
        total_deaths=("deaths", "sum") if "deaths" in agg.columns else ("report_date", "count"),
        allocated=("vaccine_dose_allocated", "sum") if "vaccine_dose_allocated" in agg.columns else ("report_date", "count"),
        deployed=("vaccine_dose_deployed", "sum") if "vaccine_dose_deployed" in agg.columns else ("report_date", "count"),
        administered=("vaccinations_administered", "sum") if "vaccinations_administered" in agg.columns else ("report_date", "count"),
        trained=("trained_chws", "sum") if "trained_chws" in agg.columns else ("report_date", "count"),
        deployed_chws=("deployed_chws", "sum") if "deployed_chws" in agg.columns else ("report_date", "count"),
        sites=("active_surveillance_sites", "sum") if "active_surveillance_sites" in agg.columns else ("report_date", "count"),
        labs=("testing_laboratries", "sum") if "testing_laboratries" in agg.columns else ("report_date", "count"),
        latest_coverage=("vaccine_coverage", "max") if "vaccine_coverage" in agg.columns else ("report_date", "count"),
        last_report=("report_date", "max") if "report_date" in agg.columns else ("country", "count"),
    )
    with np.errstate(divide='ignore', invalid='ignore'):
        out["cfr_percent"] = (out.get("total_deaths", 0) / out.get("total_cases", 1)) * 100
        out["deployed_per_case"] = out.get("deployed_chws", 0) / out.get("total_cases", 1)
        out["surveillance_per_case"] = (out.get("sites", 0) + out.get("labs", 0)) / out.get("total_cases", 1)
        out["uptake_rate_pct"] = (out.get("administered", 0) / out.get("allocated", 1)) * 100
        out["allocation_per_1000"] = (out.get("allocated", 0) / out.get("total_cases", 1)) * 1000
    return out


def _country_summary(df: pd.DataFrame) -> pd.DataFrame:
    agg = df.copy()
    if "report_date" in agg.columns:
        agg["week"] = pd.to_datetime(agg["report_date"]).dt.to_period("W-SUN").dt.start_time
    return _country_summary_cached(agg.to_json(orient="records"))


def _recommendations_for_row(r: pd.Series) -> list:
    recs = []
    # Clinical outcomes & care
    if r.get("cfr_percent", 0) > 3:
        recs.append("Clinical: Investigate high CFR; ensure rapid referral, oxygen, antivirals, IPC training.")
    # Workforce
    if r.get("deployed_per_case", 1e9) < 0.5:
        recs.append("Workforce: Surge deploy CHWs; target <500 cases per deployed CHW; mobile teams for hotspots.")
    # Surveillance
    if r.get("surveillance_per_case", 1e9) < 0.02:
        recs.append("Surveillance: Expand active sites/labs; improve sample transport and reporting cadence.")
    # Vaccination allocation and uptake
    if r.get("allocation_per_1000", 2e9) < 2000:
        recs.append("Allocation: Advocate for doses aligned to burden; prioritize high-risk geographies.")
    if r.get("uptake_rate_pct", 100) < 70:
        recs.append("Uptake: Address last-mile constraints; microplanning, outreach, community engagement.")
    # Data quality prompts
    if pd.isna(r.get("latest_coverage", np.nan)):
        recs.append("Data: Improve coverage reporting frequency and completeness.")
    if len(recs) == 0:
        recs.append("Maintain current strategy; continue monitoring and targeted micro-adjustments.")
    return recs


def _assign_personas(summary: pd.DataFrame) -> pd.DataFrame:
    # Features for clustering (handle missing with 0s where appropriate)
    feat_cols = [
        "total_cases", "cfr_percent", "deployed_per_case", "surveillance_per_case",
        "allocation_per_1000", "uptake_rate_pct"
    ]
    use = summary.copy()
    for c in feat_cols:
        if c not in use.columns:
            use[c] = 0.0
    X = use[feat_cols].fillna(0.0).values
    # Scale and cluster into up to 4 personas (fallback to smaller if few countries)
    n_countries = len(use)
    if n_countries < 4:
        n_clusters = max(2, n_countries)
    else:
        n_clusters = 4
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    labels = km.fit_predict(Xs)
    use["persona_id"] = labels

    # Human-friendly persona names via centroid heuristics
    centroids = pd.DataFrame(km.cluster_centers_, columns=feat_cols)
    # Interpret centroids on original scale by inverse transform for readability
    centroids_orig = pd.DataFrame(scaler.inverse_transform(km.cluster_centers_), columns=feat_cols)
    persona_names = {}
    for i, row in centroids_orig.iterrows():
        name = "Balanced"
        if row["total_cases"] > np.nanmedian(use["total_cases"]) and row["deployed_per_case"] < np.nanmedian(use["deployed_per_case"]) and row["surveillance_per_case"] < np.nanmedian(use["surveillance_per_case"]):
            name = "High-burden, low capacity"
        elif row["allocation_per_1000"] < np.nanmedian(use["allocation_per_1000"]) and row["uptake_rate_pct"] < np.nanmedian(use["uptake_rate_pct"]):
            name = "Under-allocated, low uptake"
        elif row["allocation_per_1000"] > np.nanmedian(use["allocation_per_1000"]) and row["uptake_rate_pct"] < np.nanmedian(use["uptake_rate_pct"]):
            name = "Well-allocated, low uptake"
        elif row["total_cases"] < np.nanmedian(use["total_cases"]) and row["surveillance_per_case"] < np.nanmedian(use["surveillance_per_case"]):
            name = "Low burden, weak surveillance"
        persona_names[i] = name
    use["persona_name"] = use["persona_id"].map(persona_names)
    return use


def _persona_playbook(name: str) -> list:
    if name == "High-burden, low capacity":
        return [
            "Immediate CHW surge and hotspot targeting",
            "Expand surveillance sites and labs; expedite sample logistics",
            "Deploy stock to high-incidence districts first",
            "Stand up clinical support: oxygen access, antivirals, IPC refreshers",
        ]
    if name == "Under-allocated, low uptake":
        return [
            "Advocate for additional doses aligned to burden",
            "Community engagement and microplanning to address hesitancy and access",
            "Weekend/evening clinics; reduce friction at point-of-care",
        ]
    if name == "Well-allocated, low uptake":
        return [
            "Last-mile delivery optimization; staffing at vaccination posts",
            "Targeted outreach to low-coverage subpopulations",
            "Monitor wastage and cold-chain integrity",
        ]
    if name == "Low burden, weak surveillance":
        return [
            "Increase sentinel sites, ensure weekly reporting cadence",
            "Strengthen lab confirmation capacity; training and QA",
            "Rapid investigation of any cluster signals",
        ]
    return [
        "Maintain response and continue monitoring",
        "Address localized gaps surfaced in metrics (CHW, surveillance, uptake)",
    ]


def recommendations_tab(df: pd.DataFrame, context_note: str):
    st.subheader("Tailored Country Recommendations")
    st.caption("Guidance is based on burden, CFR, workforce, surveillance, and vaccination metrics. ℹ️ Hover over badges and captions for quick help.")

    if "country" not in df.columns:
        st.info("Recommendations require 'country' column.")
        return

    summary = _country_summary(df)
    summary = _assign_personas(summary)
    countries = summary["country"].tolist()
    sel = st.multiselect("Select countries", options=sorted(countries), default=countries[:5], key="recs_sel_countries")
    sort_by = st.selectbox("Sort by", options=["total_cases", "persona_name", "cfr_percent", "uptake_rate_pct"], index=0, key="recs_sort")
    if not sel:
        st.info("Select at least one country.")
        return

    view = summary[summary["country"].isin(sel)].copy()
    # Persona badges
    def badge(name: str) -> str:
        if name == "High-burden, low capacity":
            return "🔴 High-burden, low capacity"
        if name == "Under-allocated, low uptake":
            return "🟠 Under-allocated, low uptake"
        if name == "Well-allocated, low uptake":
            return "🟡 Well-allocated, low uptake"
        if name == "Low burden, weak surveillance":
            return "🟣 Low burden, weak surveillance"
        return "🟢 Balanced"
    view["persona_badge"] = view.get("persona_name", "Balanced").apply(badge)
    # Stale flag by last report date
    if "last_report" in view.columns:
        try:
            days_old = (pd.Timestamp.now(tz=pd.Timestamp(view["last_report"].max()).tz) - pd.to_datetime(view["last_report"])) .dt.days
        except Exception:
            days_old = pd.Series([None] * len(view), index=view.index)
        view["stale"] = days_old.fillna(0) > 28
    if sort_by in view.columns:
        view = view.sort_values(sort_by, ascending=False if sort_by != "persona_name" else True)
    # Key metrics table
    show_cols = [
        "country", "persona_badge", "total_cases", "cfr_percent", "deployed_per_case", "surveillance_per_case",
        "allocation_per_1000", "uptake_rate_pct", "latest_coverage", "stale"
    ]
    show_cols = [c for c in show_cols if c in view.columns]
    st.dataframe(view[show_cols].head(100), use_container_width=True)
    st.caption("CFR: deaths/cases. CHWs/surv per case: higher is better. Allocation/1,000 adjusts doses for burden. Uptake: administered/allocated. 'stale' means last report >28 days.")

    # CSV downloads
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button("Download country metrics (CSV)", data=view[show_cols].to_csv(index=False).encode("utf-8"), file_name="country_metrics.csv", mime="text/csv")
    # DQ report per country (simple)
    dq = pd.DataFrame({"country": view["country"]})
    if "last_report" in view.columns:
        dq["last_report"] = pd.to_datetime(view["last_report"]) if "last_report" in view.columns else pd.NaT
    dq["stale_>28d"] = view.get("stale", False)
    with col_dl2:
        st.download_button("Download DQ report (CSV)", data=dq.to_csv(index=False).encode("utf-8"), file_name="dq_report.csv", mime="text/csv")

    st.markdown("---")
    st.subheader("Country-specific recommendations")
    for _, row in view.iterrows():
        country_name = row["country"]
        recs = _recommendations_for_row(row)
        with st.expander(f"{country_name}"):
            st.caption(f"Persona: {row.get('persona_name', 'Balanced')}")
            playbook = _persona_playbook(row.get("persona_name", "Balanced"))
            if playbook:
                st.markdown("Persona playbook:")
                for p in playbook:
                    st.markdown(f"- {p}")
            # Highlight key issues
            bullets = []
            if row.get("cfr_percent", 0) > 3:
                bullets.append("High CFR")
            if row.get("deployed_per_case", 999) < 0.5:
                bullets.append("Low CHW coverage")
            if row.get("surveillance_per_case", 999) < 0.02:
                bullets.append("Low surveillance")
            if row.get("allocation_per_1000", 999999) < 2000:
                bullets.append("Under-allocation vs burden")
            if row.get("uptake_rate_pct", 100) < 70:
                bullets.append("Low uptake")
            if bullets:
                st.markdown("Key flags: " + " ".join([f"`{b}`" for b in bullets]))

            st.markdown("- Short-term (0-4 weeks):")
            for rec in recs:
                st.markdown(f"  - {rec}")

            # Optional mini chart: allocation vs uptake vs cases
            sub = df[df.get("country") == country_name]
            if {"report_date", "weekly_new_cases"}.issubset(sub.columns) and not sub["report_date"].isna().all():
                ts = sub.dropna(subset=["report_date"]).groupby("report_date", as_index=False)["weekly_new_cases"].sum()
                fig = px.line(ts, x="report_date", y="weekly_new_cases", title=f"{country_name}: Weekly cases")
                fig.update_layout(height=260)
                st.plotly_chart(fig, use_container_width=True)


