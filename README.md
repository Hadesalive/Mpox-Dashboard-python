# Mpox Africa Dashboard

Interactive Streamlit dashboard built from the provided Excel dataset to explore Mpox outbreak trends, vaccination progress, surveillance, and workforce capacity across African countries.

## Features

- Overview KPIs: Confirmed, deaths, CFR, vaccinations, latest coverage
- Time-series trends (weekly cases, confirmed, deaths)
- Top countries breakdowns
- Africa choropleth by country
- Vaccination allocation → deployment → administration + rates
- Workforce ratios per case (trained/deployed per case)
- Sidebar filters: date range, countries, clades, surveillance notes
- Upload your own `.xlsx` to override the default

## Getting Started

1. Create and activate a virtual environment (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app

```bash
streamlit run app.py
```

Then open the local URL shown in your terminal.

## Data

- By default, the app loads `mpox_africa_dataset.xlsx` in this folder.
- You can upload a replacement Excel file from the sidebar.
- Columns are auto-detected and standardized if they roughly match names used in the included SQL (`Mpox_Hackathon.sql`).

## Notes

- The map uses Plotly's country names with scope set to Africa. Ensure country names are standard English names.
- If date or key columns are missing, corresponding views will be limited.

