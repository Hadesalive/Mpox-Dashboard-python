import plotly.io as pio
import streamlit as st


COLOR_SEQ = ["#16A34A", "#10B981", "#06B6D4", "#0EA5E9", "#64748B", "#65A30D", "#2DD4BF"]


def apply_base_theme():
    pio.templates.default = "plotly_white"
    # Set a consistent colorway for Plotly figures (health-focused palette)
    try:
        pio.templates["plotly_white"].layout.colorway = COLOR_SEQ  # type: ignore
    except Exception:
        pass
    st.markdown(
        """
        <style>
          .block-container {max-width: 1280px; padding-top: 1rem; padding-bottom: 3rem;}
          html, body { background-color: #FAFAFA; }
          h1, h2, h3 { letter-spacing: -0.01em; color: #0F172A; margin-bottom: 0.25rem; }
          h1 { font-weight: 800; font-size: 2rem; line-height: 1.2; }
          h2 { font-weight: 700; font-size: 1.375rem; line-height: 1.3; }
          h3 { font-weight: 600; font-size: 1.125rem; line-height: 1.35; }
          /* Accent underline for headings */
          h1 + p, h2 + p, h3 + p { margin-top: 0.25rem; }
          .stMarkdown h1::after, .stMarkdown h2::after { content: ""; display: block; width: 56px; height: 3px; margin-top: 6px; border-radius: 999px; background: linear-gradient(90deg,#16A34A, #06B6D4); opacity: 0.6; }
          [data-testid="stMetricValue"] { font-weight: 700; }
          [data-testid="stMetricDelta"] span { font-weight: 600; }
          .stMarkdown + div > div > div:has([data-testid="stPlotlyChart"]) {
            border: 1px solid #E5E7EB; border-radius: 12px; padding: 8px; background: #fff;
          }
          details summary {background: #F8FAFC; border-radius: 8px; padding: 6px 8px;}
          details[open] summary {background: #F1F5F9;}
          /* Subtle alert styling */
          div[data-baseweb="notification"] { border-radius: 10px; border: 1px solid #E5E7EB; }
          .stAlert { background: #F8FAFC !important; color: #0F172A !important; border: 1px solid #E5E7EB; border-radius: 10px; }
          /* Tables */
          .stDataFrame, .stDataFrame table { font-size: 0.92rem; }
          .stDataFrame [role="rowgroup"] tr:nth-child(even) { background: #F9FAFB; }
          .stDataFrame [role="gridcell"], .stDataFrame th { border-color: #E5E7EB !important; }
          /* Buttons */
          button[kind="primary"] { background: #10B981 !important; border: 1px solid #10B981; }
          button[kind="secondary"] { border: 1px solid #CBD5E1; }
          /* Tabs */
          .stTabs [data-baseweb="tab"] { font-weight: 600; }
          .stTabs [aria-selected="true"] { color: #065F46; }
          /* Persona badge approximation using emojis already present */
          .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; background: #ECFDF5; color: #065F46; font-size: 0.85rem; }
          /* Sidebar */
          section[data-testid="stSidebar"] { background: linear-gradient(180deg,#FFFFFF 0%, #F8FAFC 100%); border-right: 1px solid #E5E7EB; }
          section[data-testid="stSidebar"] .block-container { padding-top: 0.5rem; }
          section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 { color: #0B5D4A; letter-spacing: 0; }
          section[data-testid="stSidebar"] .stButton>button { width: 100%; border-radius: 10px; }
          /* Sidebar controls */
          section[data-testid="stSidebar"] .stMultiSelect, section[data-testid="stSidebar"] .stSelectbox, section[data-testid="stSidebar"] .stTextInput, section[data-testid="stSidebar"] .stDateInput {
            background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 2px 6px;
          }
          section[data-testid="stSidebar"] [data-baseweb="slider"] div[role="slider"] { background: #10B981; box-shadow: 0 0 0 3px rgba(16,185,129,0.15); }
          section[data-testid="stSidebar"] details summary { background: #ECFDF5; border: 1px solid #A7F3D0; }
          section[data-testid="stSidebar"] details[open] summary { background: #D1FAE5; }
          /* File uploader */
          section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] { border: 1px dashed #93C5FD; background: #F8FAFC; border-radius: 12px; }
          /* Captions as tooltips */
          .stCaption, .css-1q7e5u2 { color: #475569 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


