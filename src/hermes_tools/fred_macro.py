"""FRED macro indicator tool.

Returns recent values for the macro series configured in
`src.config.FRED_MACRO_DATA` (M2, consumer sentiment, industrial production by
default). Requires `FRED_API_KEY` in the environment.
"""
from __future__ import annotations

from typing import Any

from src.api_adapters.fred import FredData
from src.config import FRED_API_KEY, FRED_MACRO_DATA


def fetch_fred_macro(
    series: dict[str, str] | None = None,
    look_back_years: int = 2,
    latest_only: bool = False,
) -> dict[str, Any]:
    if not FRED_API_KEY:
        raise RuntimeError("FRED_API_KEY is not set; cannot call FRED API")

    series_ids = series or FRED_MACRO_DATA
    df = FredData(series_ids).get_data(look_back=look_back_years, return_full_data=not latest_only)

    out: dict[str, list[dict[str, Any]]] = {}
    for name in series_ids:
        col = df[name].dropna()
        out[name] = [
            {"date": idx.strftime("%Y-%m-%d"), "value": float(val)}
            for idx, val in col.items()
        ]
    return {
        "series": series_ids,
        "look_back_years": look_back_years,
        "latest_only": latest_only,
        "observations": out,
    }
