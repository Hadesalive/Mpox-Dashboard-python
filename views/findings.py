import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from datetime import datetime, timedelta

from utils.style import COLOR_SEQ


def _compute_executive_summary(df: pd.DataFrame) -> dict:
    """Compute executive-level summary metrics following industry standards"""
    summary = {}
    
    # Core epidemiological metrics
    if "confirmed_cases" in df.columns:
        summary["total_cases"] = int(df["confirmed_cases"].sum())
        summary["avg_cases_per_country"] = int(df.groupby("country")["confirmed_cases"].sum().mean())
        summary["max_cases_country"] = df.groupby("country")["confirmed_cases"].sum().idxmax()
        summary["max_cases_count"] = int(df.groupby("country")["confirmed_cases"].sum().max())
    
    if "deaths" in df.columns:
        summary["total_deaths"] = int(df["deaths"].sum())
        if summary.get("total_cases", 0) > 0:
            summary["overall_cfr"] = round((summary["total_deaths"] / summary["total_cases"]) * 100, 2)
    
    # Response capacity metrics
    if "deployed_chws" in df.columns:
        summary["total_chws"] = int(df["deployed_chws"].sum())
        summary["avg_chw_per_country"] = int(df.groupby("country")["deployed_chws"].sum().mean())
    
    if "vaccinations_administered" in df.columns:
        summary["total_vaccinations"] = int(df["vaccinations_administered"].sum())
    
    if "vaccine_dose_allocated" in df.columns:
        summary["total_allocated"] = int(df["vaccine_dose_allocated"].sum())
        if summary.get("total_allocated", 0) > 0:
            summary["uptake_rate"] = round((summary.get("total_vaccinations", 0) / summary["total_allocated"]) * 100, 2)
    
    # Data quality metrics
    if "report_date" in df.columns:
        try:
            max_date = pd.to_datetime(df["report_date"]).max()
            if pd.notnull(max_date):
                days_old = (pd.Timestamp.now(tz=max_date.tz) - max_date).days
                summary["data_freshness_days"] = days_old
                summary["data_freshness_status"] = "Current" if days_old <= 7 else "Recent" if days_old <= 30 else "Stale"
        except Exception:
            pass
    
    return summary


def _create_executive_dashboard(summary: dict):
    """Create executive-level dashboard with KPI cards"""
    st.markdown("## 📊 Executive Summary Dashboard")
    st.caption("Key Performance Indicators and Critical Metrics")
    
    # Primary KPIs in a grid layout
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        _create_kpi_card(
            "Total Cases",
            f"{summary.get('total_cases', 0):,}",
            "Confirmed Mpox cases",
            "#DC2626",
            "📈"
        )
    
    with col2:
        _create_kpi_card(
            "Case Fatality Rate",
            f"{summary.get('overall_cfr', 0)}%",
            "Deaths per 100 cases",
            "#F59E0B",
            "⚠️"
        )
    
    with col3:
        _create_kpi_card(
            "Vaccine Uptake",
            f"{summary.get('uptake_rate', 0)}%",
            "Administered vs allocated",
            "#10B981",
            "💉"
        )
    
    with col4:
        _create_kpi_card(
            "Active Countries",
            f"{summary.get('total_countries', 0)}",
            "Countries with data",
            "#3B82F6",
            "🌍"
        )
    
    # Secondary metrics row
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        _create_kpi_card(
            "Total CHWs",
            f"{summary.get('total_chws', 0):,}",
            "Deployed health workers",
            "#8B5CF6",
            "👥"
        )
    
    with col6:
        _create_kpi_card(
            "Avg Cases/Country",
            f"{summary.get('avg_cases_per_country', 0):,}",
            "Mean cases per country",
            "#06B6D4",
            "📊"
        )
    
    with col7:
        _create_kpi_card(
            "Data Status",
            summary.get('data_freshness_status', 'Unknown'),
            f"{summary.get('data_freshness_days', 0)} days old",
            "#EF4444" if summary.get('data_freshness_days', 0) > 30 else "#10B981",
            "📅"
        )
    
    with col8:
        _create_kpi_card(
            "Peak Country",
            summary.get('max_cases_country', 'N/A'),
            f"{summary.get('max_cases_count', 0):,} cases",
            "#F97316",
            "🔥"
        )


def _create_kpi_card(title: str, value: str, subtitle: str, color: str, icon: str):
    """Create professional KPI card with consistent styling"""
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {color}08, {color}15);
            border: 1px solid {color}20;
            border-radius: 12px;
            padding: 20px;
            margin: 8px 0;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        ">
            <div style="font-size: 1.5rem; margin-bottom: 8px;">{icon}</div>
            <h3 style="color: {color}; margin: 0; font-size: 1rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">{title}</h3>
            <div style="font-size: 1.8rem; font-weight: 800; color: {color}; margin: 12px 0; font-family: 'SF Mono', monospace;">{value}</div>
            <div style="color: #64748B; font-size: 0.85rem; line-height: 1.3;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def _create_trend_analysis(df: pd.DataFrame):
    """Create trend analysis section with time series and patterns"""
    st.markdown("## 📈 Trend Analysis & Patterns")
    st.caption("Temporal patterns and outbreak dynamics")
    
    if "report_date" in df.columns and "confirmed_cases" in df.columns:
        # Time series analysis
        df_time = df.copy()
        df_time["report_date"] = pd.to_datetime(df_time["report_date"])
        df_time = df_time.sort_values("report_date")
        
        # Aggregate by date
        daily_cases = df_time.groupby("report_date")["confirmed_cases"].sum().reset_index()
        daily_cases = daily_cases.set_index("report_date").asfreq("D").fillna(0)
        
        # Calculate rolling averages
        daily_cases["7_day_avg"] = daily_cases["confirmed_cases"].rolling(7).mean()
        daily_cases["14_day_avg"] = daily_cases["confirmed_cases"].rolling(14).mean()
        
        # Create trend visualization
        fig_trend = go.Figure()
        
        fig_trend.add_trace(go.Scatter(
            x=daily_cases.index,
            y=daily_cases["confirmed_cases"],
            mode="markers+lines",
            name="Daily Cases",
            line=dict(color="#3B82F6", width=2),
            marker=dict(size=4)
        ))
        
        fig_trend.add_trace(go.Scatter(
            x=daily_cases.index,
            y=daily_cases["7_day_avg"],
            mode="lines",
            name="7-Day Moving Average",
            line=dict(color="#EF4444", width=3, dash="dash")
        ))
        
        fig_trend.add_trace(go.Scatter(
            x=daily_cases.index,
            y=daily_cases["14_day_avg"],
            mode="lines",
            name="14-Day Moving Average",
            line=dict(color="#10B981", width=3, dash="dot")
        ))
        
        fig_trend.update_layout(
            title="Outbreak Trend Analysis",
            xaxis_title="Date",
            yaxis_title="Confirmed Cases",
            height=400,
            showlegend=True,
            hovermode="x unified"
        )
        
        st.plotly_chart(fig_trend, use_container_width=True)
        
        # Trend insights
        col_t1, col_t2 = st.columns(2)
        
        with col_t1:
            st.markdown("**Trend Insights:**")
            if len(daily_cases) > 14:
                recent_avg = daily_cases["7_day_avg"].iloc[-7:].mean()
                previous_avg = daily_cases["7_day_avg"].iloc[-14:-7].mean()
                
                if recent_avg > previous_avg * 1.1:
                    st.warning("📈 **Increasing Trend**: Recent 7-day average is higher than previous period")
                elif recent_avg < previous_avg * 0.9:
                    st.success("📉 **Decreasing Trend**: Recent 7-day average is lower than previous period")
                else:
                    st.info("➡️ **Stable Trend**: Case numbers remain relatively consistent")
        
        with col_t2:
            st.markdown("**Peak Analysis:**")
            if not daily_cases.empty:
                peak_date = daily_cases["confirmed_cases"].idxmax()
                peak_cases = daily_cases["confirmed_cases"].max()
                st.metric("Peak Date", peak_date.strftime("%B %d, %Y"))
                st.metric("Peak Cases", f"{int(peak_cases):,}")


def _create_geographic_insights(df: pd.DataFrame):
    """Create geographic distribution and clustering analysis"""
    st.markdown("## 🌍 Geographic Distribution & Clustering")
    st.caption("Spatial patterns and regional analysis")
    
    if "country" in df.columns:
        # Country-level aggregation
        country_data = df.groupby("country").agg({
            "confirmed_cases": "sum",
            "deaths": "sum",
            "deployed_chws": "sum",
            "vaccinations_administered": "sum"
        }).reset_index()
        
        # Calculate derived metrics
        country_data["cfr"] = (country_data["deaths"] / country_data["confirmed_cases"]) * 100
        country_data["chw_per_case"] = country_data["deployed_chws"] / country_data["confirmed_cases"]
        country_data["vaccination_rate"] = country_data["vaccinations_administered"] / country_data["confirmed_cases"]
        
        # Create geographic visualization
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            # Cases by country
            fig_cases = px.bar(
                country_data.sort_values("confirmed_cases", ascending=True).tail(10),
                x="confirmed_cases",
                y="country",
                orientation="h",
                title="Top 10 Countries by Cases",
                color="confirmed_cases",
                color_continuous_scale="Reds"
            )
            fig_cases.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_cases, use_container_width=True)
        
        with col_g2:
            # CFR by country
            fig_cfr = px.bar(
                country_data[country_data["cfr"] > 0].sort_values("cfr", ascending=True).tail(10),
                x="cfr",
                y="country",
                orientation="h",
                title="Top 10 Countries by CFR (%)",
                color="cfr",
                color_continuous_scale="Oranges"
            )
            fig_cfr.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_cfr, use_container_width=True)
        
        # Geographic insights
        st.markdown("**Geographic Insights:**")
        col_gi1, col_gi2, col_gi3 = st.columns(3)
        
        with col_gi1:
            high_burden = country_data.nlargest(3, "confirmed_cases")
            st.markdown("**High Burden Countries:**")
            for _, row in high_burden.iterrows():
                st.write(f"• {row['country']}: {int(row['confirmed_cases']):,} cases")
        
        with col_gi2:
            high_cfr = country_data[country_data["cfr"] > 0].nlargest(3, "cfr")
            st.markdown("**High CFR Countries:**")
            for _, row in high_cfr.iterrows():
                st.write(f"• {row['country']}: {row['cfr']:.1f}%")
        
        with col_gi3:
            low_coverage = country_data[country_data["chw_per_case"] > 0].nsmallest(3, "chw_per_case")
            st.markdown("**Low CHW Coverage:**")
            for _, row in low_coverage.iterrows():
                st.write(f"• {row['country']}: {row['chw_per_case']:.3f} CHWs/case")


def _create_response_analysis(df: pd.DataFrame):
    """Create response capacity and effectiveness analysis"""
    st.markdown("## 🚨 Response Capacity & Effectiveness")
    st.caption("Healthcare system response and resource allocation")
    
    if "country" in df.columns:
        # Response metrics by country
        response_data = df.groupby("country").agg({
            "deployed_chws": "sum",
            "confirmed_cases": "sum",
            "vaccinations_administered": "sum",
            "active_surveillance_sites": "sum"
        }).reset_index()
        
        # Calculate response ratios
        response_data["chw_per_case"] = response_data["deployed_chws"] / response_data["confirmed_cases"]
        response_data["vaccination_per_case"] = response_data["vaccinations_administered"] / response_data["confirmed_cases"]
        
        # Create response dashboard
        col_r1, col_r2 = st.columns(2)
        
        with col_r1:
            # CHW coverage heatmap
            fig_chw = px.scatter(
                response_data,
                x="confirmed_cases",
                y="deployed_chws",
                size="active_surveillance_sites",
                color="chw_per_case",
                hover_data=["country"],
                title="CHW Deployment vs Case Burden",
                color_continuous_scale="Viridis"
            )
            fig_chw.update_layout(height=400)
            st.plotly_chart(fig_chw, use_container_width=True)
        
        with col_r2:
            # Vaccination efficiency
            fig_vacc = px.scatter(
                response_data,
                x="confirmed_cases",
                y="vaccinations_administered",
                size="active_surveillance_sites",
                color="vaccination_per_case",
                hover_data=["country"],
                title="Vaccination Coverage vs Case Burden",
                color_continuous_scale="Plasma"
            )
            fig_vacc.update_layout(height=400)
            st.plotly_chart(fig_vacc, use_container_width=True)
        
        # Response insights
        st.markdown("**Response Insights:**")
        
        # Identify gaps
        gaps = response_data[
            (response_data["chw_per_case"] < 0.5) | 
            (response_data["vaccination_per_case"] < 0.1)
        ].copy()
        
        if not gaps.empty:
            st.warning("**Resource Gaps Identified:**")
            for _, row in gaps.iterrows():
                issues = []
                if row["chw_per_case"] < 0.5:
                    issues.append(f"Low CHW coverage ({row['chw_per_case']:.3f})")
                if row["vaccination_per_case"] < 0.1:
                    issues.append(f"Low vaccination rate ({row['vaccination_per_case']:.3f})")
                
                st.write(f"• **{row['country']}**: {', '.join(issues)}")


def _create_data_quality_report(df: pd.DataFrame):
    """Create comprehensive data quality assessment"""
    st.markdown("## 🔍 Data Quality Assessment")
    st.caption("Completeness, consistency, and reliability analysis")
    
    # Data completeness analysis
    completeness = {}
    for col in df.columns:
        completeness[col] = {
            "total": len(df),
            "missing": df[col].isnull().sum(),
            "completeness_pct": round((1 - df[col].isnull().sum() / len(df)) * 100, 1)
        }
    
    # Create completeness visualization
    completeness_df = pd.DataFrame(completeness).T.reset_index()
    completeness_df.columns = ["Field", "Total", "Missing", "Completeness_%"]
    
    fig_completeness = px.bar(
        completeness_df,
        x="Field",
        y="Completeness_%",
        color="Completeness_%",
        title="Data Completeness by Field (%)",
        color_continuous_scale="RdYlGn"
    )
    fig_completeness.update_layout(height=400, xaxis_tickangle=-45)
    st.plotly_chart(fig_completeness, use_container_width=True)
    
    # Data quality insights
    col_dq1, col_dq2 = st.columns(2)
    
    with col_dq1:
        st.markdown("**Completeness Summary:**")
        high_complete = completeness_df[completeness_df["Completeness_%"] >= 90]
        medium_complete = completeness_df[(completeness_df["Completeness_%"] >= 70) & (completeness_df["Completeness_%"] < 90)]
        low_complete = completeness_df[completeness_df["Completeness_%"] < 70]
        
        st.success(f"✅ **High Quality** ({completeness_df['Completeness_%'].mean():.1f}% avg)")
        st.info(f"📊 **Complete Fields**: {len(high_complete)}")
        st.warning(f"⚠️ **Partial Fields**: {len(medium_complete)}")
        st.error(f"❌ **Poor Fields**: {len(low_complete)}")
    
    with col_dq2:
        st.markdown("**Data Freshness:**")
        if "report_date" in df.columns:
            try:
                max_date = pd.to_datetime(df["report_date"]).max()
                if pd.notnull(max_date):
                    days_old = (pd.Timestamp.now(tz=max_date.tz) - max_date).days
                    
                    if days_old <= 7:
                        st.success(f"🟢 **Current**: Data is {days_old} days old")
                    elif days_old <= 30:
                        st.warning(f"🟡 **Recent**: Data is {days_old} days old")
                    else:
                        st.error(f"🔴 **Stale**: Data is {days_old} days old")
                        
                    st.metric("Last Update", max_date.strftime("%B %d, %Y"))
            except Exception:
                st.info("📅 Date information not available")


def _create_recommendations_summary(df: pd.DataFrame):
    """Create actionable recommendations based on findings"""
    st.markdown("## 🎯 Strategic Recommendations")
    st.caption("Evidence-based action items and priority interventions")
    
    recommendations = []
    
    # High CFR countries
    if {"country", "confirmed_cases", "deaths"}.issubset(df.columns):
        country_cfr = df.groupby("country").agg({
            "confirmed_cases": "sum",
            "deaths": "sum"
        }).reset_index()
        country_cfr["cfr"] = (country_cfr["deaths"] / country_cfr["confirmed_cases"]) * 100
        high_cfr = country_cfr[country_cfr["cfr"] > 3]
        
        if not high_cfr.empty:
            recommendations.append({
                "priority": "High",
                "category": "Clinical Care",
                "recommendation": f"Immediate clinical intervention needed in {len(high_cfr)} countries with CFR >3%",
                "countries": high_cfr["country"].tolist(),
                "metric": f"CFR range: {high_cfr['cfr'].min():.1f}% - {high_cfr['cfr'].max():.1f}%"
            })
    
    # Low vaccine coverage
    if {"country", "vaccine_dose_allocated", "vaccinations_administered"}.issubset(df.columns):
        uptake = df.groupby("country").agg({
            "vaccine_dose_allocated": "sum",
            "vaccinations_administered": "sum"
        }).reset_index()
        uptake["uptake_pct"] = (uptake["vaccinations_administered"] / uptake["vaccine_dose_allocated"]) * 100
        low_uptake = uptake[uptake["uptake_pct"] < 70]
        
        if not low_uptake.empty:
            recommendations.append({
                "priority": "Medium",
                "category": "Vaccination",
                "recommendation": f"Vaccine rollout optimization needed in {len(low_uptake)} countries",
                "countries": low_uptake["country"].tolist(),
                "metric": f"Uptake range: {low_uptake['uptake_pct'].min():.1f}% - {low_uptake['uptake_pct'].max():.1f}%"
            })
    
    # Workforce gaps
    if {"country", "deployed_chws", "confirmed_cases"}.issubset(df.columns):
        workforce = df.groupby("country").agg({
            "deployed_chws": "sum",
            "confirmed_cases": "sum"
        }).reset_index()
        workforce["chw_per_case"] = workforce["deployed_chws"] / workforce["confirmed_cases"]
        low_coverage = workforce[workforce["chw_per_case"] < 0.5]
        
        if not low_coverage.empty:
            recommendations.append({
                "priority": "High",
                "category": "Workforce",
                "recommendation": f"CHW deployment expansion needed in {len(low_coverage)} countries",
                "countries": low_coverage["country"].tolist(),
                "metric": f"Coverage range: {low_coverage['chw_per_case'].min():.3f} - {low_coverage['chw_per_case'].max():.3f} CHWs/case"
            })
    
    # Display recommendations
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            priority_color = "#EF4444" if rec["priority"] == "High" else "#F59E0B" if rec["priority"] == "Medium" else "#10B981"
            
            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(135deg, {priority_color}08, {priority_color}15);
                    border-left: 4px solid {priority_color};
                    border-radius: 8px;
                    padding: 20px;
                    margin: 16px 0;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <h4 style="margin: 0; color: {priority_color}; font-weight: 600;">{rec['category']}</h4>
                        <span style="
                            background: {priority_color};
                            color: white;
                            padding: 4px 12px;
                            border-radius: 20px;
                            font-size: 0.8rem;
                            font-weight: 600;
                        ">{rec['priority']} Priority</span>
                    </div>
                    <p style="margin: 8px 0; color: #374151; font-size: 1rem; line-height: 1.5;">{rec['recommendation']}</p>
                    <div style="margin-top: 12px;">
                        <strong>Affected Countries:</strong> {', '.join(rec['countries'][:5])}{'...' if len(rec['countries']) > 5 else ''}
                    </div>
                    <div style="color: #64748B; font-size: 0.9rem; margin-top: 8px;">{rec['metric']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.success("✅ No critical issues identified. Current response appears adequate.")


def findings_tab(df: pd.DataFrame, context_note: str):
    """Main findings tab with professional data analysis structure"""
    
    # Page header
    st.markdown("# 🔍 Mpox Outbreak Analysis - Executive Findings")
    st.caption(f"Comprehensive analysis report | {context_note} | Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
    
    # Executive Summary Dashboard
    summary = _compute_executive_summary(df)
    _create_executive_dashboard(summary)
    
    st.markdown("---")
    
    # Trend Analysis
    _create_trend_analysis(df)
    
    st.markdown("---")
    
    # Geographic Insights
    _create_geographic_insights(df)
    
    st.markdown("---")
    
    # Response Analysis
    _create_response_analysis(df)
    
    st.markdown("---")
    
    # Data Quality Report
    _create_data_quality_report(df)
    
    st.markdown("---")
    
    # Strategic Recommendations
    _create_recommendations_summary(df)
    
    st.markdown("---")
    
    # Export Section
    st.markdown("## 📤 Export & Documentation")
    
    col_exp1, col_exp2, col_exp3 = st.columns(3)
    
    with col_exp1:
        # Export summary metrics
        if summary:
            summary_df = pd.DataFrame(list(summary.items()), columns=["Metric", "Value"])
            st.download_button(
                "📊 Executive Summary (CSV)",
                data=summary_df.to_csv(index=False).encode("utf-8"),
                file_name=f"mpox_executive_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with col_exp2:
        # Export data quality report
        if "report_date" in df.columns:
            dq_report = {
                "Total Records": len(df),
                "Countries": df["country"].nunique() if "country" in df.columns else 0,
                "Data Completeness": f"{df.notna().sum().sum() / (len(df) * len(df.columns)) * 100:.1f}%",
                "Last Update": df["report_date"].max() if "report_date" in df.columns else "Unknown"
            }
            dq_df = pd.DataFrame(list(dq_report.items()), columns=["Metric", "Value"])
            st.download_button(
                "🔍 Data Quality Report (CSV)",
                data=dq_df.to_csv(index=False).encode("utf-8"),
                file_name=f"mpox_data_quality_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with col_exp3:
        # Export filtered dataset
        st.download_button(
            "📁 Filtered Dataset (CSV)",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"mpox_filtered_data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #64748B; font-size: 0.9rem; padding: 20px;">
            📊 <strong>Mpox Africa Dashboard</strong> | Professional Data Analysis Report<br>
            Generated using industry-standard analytical methods and visualization techniques
        </div>
        """,
        unsafe_allow_html=True
    )
