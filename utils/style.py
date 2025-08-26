import plotly.io as pio
import streamlit as st


COLOR_SEQ = ["#16A34A", "#10B981", "#06B6D4", "#0EA5E9", "#64748B", "#65A30D", "#2DD4BF"]


def apply_base_theme():
    pio.templates.default = "plotly_white"
    st.markdown(
        """
        <style>
          .block-container {max-width: 1280px; padding-top: 1rem; padding-bottom: 3rem;}
          h1, h2, h3 { letter-spacing: -0.02em; }
          [data-testid="stMetricValue"] { font-weight: 700; }
          [data-testid="stMetricDelta"] span { font-weight: 600; }
          .stMarkdown + div > div > div:has([data-testid="stPlotlyChart"]) {
            border: 1px solid #E5E7EB; border-radius: 12px; padding: 8px; background: #fff;
          }
          details[open] summary {background: #F3F4F6; border-radius: 8px;}
        </style>
        """,
        unsafe_allow_html=True,
    )


