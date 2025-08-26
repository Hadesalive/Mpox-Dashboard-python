import os
from datetime import datetime
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd


EXPECTED_COLUMNS = {
    "country": ["country", "Country"],
    "report_date": ["report_date", "date", "Date", "reportDate"],
    "confirmed_cases": ["confirmed_cases", "Confirmed", "confirmed", "cases"],
    "deaths": ["deaths", "Deaths", "fatalities"],
    "vaccinations_administered": ["vaccinations_administered", "vax_administered", "administered"],
    "active_surveillance_sites": ["active_surveillance_sites", "active_sites", "surveillance_sites"],
    "suspected_cases": ["suspected_cases", "suspected"],
    "case_fatality_rate": ["case_fatality_rate", "cfr", "cfr_percent"],
    "clade": ["clade", "strain"],
    "weekly_new_cases": ["weekly_new_cases", "weekly_cases"],
    "vaccine_dose_allocated": ["vaccine_dose_allocated", "allocated"],
    "vaccine_dose_deployed": ["vaccine_dose_deployed", "deployed"],
    "vaccine_coverage": ["vaccine_coverage", "coverage_percent", "coverage"],
    "testing_laboratries": ["testing_laboratries", "testing_labs", "laboratories", "labs"],
    "trained_chws": ["trained_chws", "trained_chw"],
    "deployed_chws": ["deployed_chws", "deployed_chw"],
    "surveillance_notes": ["surveillance_notes", "notes", "surveillance_note"],
}


def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {}
    lower_cols = {c.lower(): c for c in df.columns}
    for canonical, candidates in EXPECTED_COLUMNS.items():
        for candidate in candidates:
            candidate_lower = candidate.lower()
            if candidate_lower in lower_cols:
                mapping[lower_cols[candidate_lower]] = canonical
                break
    return df.rename(columns=mapping)


def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    if "report_date" in df.columns:
        df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
    numeric_fields = [
        "confirmed_cases",
        "deaths",
        "vaccinations_administered",
        "active_surveillance_sites",
        "suspected_cases",
        "case_fatality_rate",
        "weekly_new_cases",
        "vaccine_dose_allocated",
        "vaccine_dose_deployed",
        "vaccine_coverage",
        "testing_laboratries",
        "trained_chws",
        "deployed_chws",
    ]
    for col in numeric_fields:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_data(default_path: str, uploaded_file: Optional[bytes]) -> pd.DataFrame:
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file, engine="openpyxl")
    else:
        df = pd.read_excel(default_path, engine="openpyxl")
    df = _standardize_columns(df)
    df = _coerce_types(df)
    if "report_date" in df.columns and not df["report_date"].isna().all():
        df["date"] = df["report_date"].dt.date
        df["year_week"] = df["report_date"].dt.to_period("W-SUN").astype(str)
        df["year_month"] = df["report_date"].dt.to_period("M").astype(str)
    if "case_fatality_rate" not in df.columns and {"deaths", "confirmed_cases"}.issubset(df.columns):
        df["case_fatality_rate"] = (df["deaths"] / df["confirmed_cases"]).replace([np.inf, -np.inf], np.nan) * 100
    return df


def filter_data(
    df: pd.DataFrame,
    date_range: Optional[Tuple[datetime, datetime]],
    countries: List[str],
    clades: List[str],
    notes: List[str],
) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    if date_range and "report_date" in df.columns:
        start_dt, end_dt = date_range
        mask &= df["report_date"].between(start_dt, end_dt, inclusive="both")
    if countries and "country" in df.columns:
        mask &= df["country"].isin(countries)
    if clades and "clade" in df.columns:
        mask &= df["clade"].isin(clades)
    if notes and "surveillance_notes" in df.columns:
        mask &= df["surveillance_notes"].isin(notes)
    return df[mask].copy()


def make_filter_note(
    date_range: Optional[Tuple[datetime, datetime]],
    countries: List[str],
    clades: List[str],
    notes: List[str],
) -> str:
    parts: List[str] = []
    if date_range:
        parts.append(f"Date: {date_range[0].date()} → {date_range[1].date()}")
    if countries:
        parts.append(f"Countries: {', '.join(countries[:5])}{'…' if len(countries) > 5 else ''}")
    if clades:
        parts.append(f"Clades: {', '.join(map(str, clades[:5]))}{'…' if len(clades) > 5 else ''}")
    if notes:
        parts.append("Surveillance notes filter applied")
    if not parts:
        return "Showing all data (no filters applied)."
    return "Filters → " + " | ".join(parts)


