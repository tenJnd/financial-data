"""Stateless wrapper around the finviz screener scraper.

Accepts either a finviz screener URL (the kind you paste from the browser) or
an explicit (filters, order) pair. Returns a list of row dicts keyed by
ticker so an LLM tool consumer doesn't need to handle pandas.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd

from src.financial_data import stocks_screener


def _parse_url(url: str) -> tuple[str, str]:
    qs = parse_qs(urlparse(url).query)
    filters = qs.get("f", [""])[0]
    order = qs.get("o", ["-roa"])[0]
    return filters, order


def run_finviz_screener(
    url: str | None = None,
    filters: str | None = None,
    order: str = "-roa",
    limit: int | None = 50,
) -> dict[str, Any]:
    """Run a finviz screen and return its rows.

    One of `url` or `filters` must be provided. `url` takes precedence and
    overrides `filters`/`order`.
    """
    if url:
        filters, order = _parse_url(url)
    if not filters:
        raise ValueError("Provide a finviz URL or a filters string")

    frames = [
        stocks_screener.fetch_view_data(view, filters, order)
        for view in stocks_screener.VIEWS
    ]
    merged = stocks_screener.merge_dataframes(frames)
    merged = _coerce_numeric(merged)
    if limit:
        merged = merged.head(limit)

    rows = [
        {"ticker": idx, **{k: _clean(v) for k, v in row.items()}}
        for idx, row in merged.iterrows()
    ]
    return {
        "filters": filters,
        "order": order,
        "count": len(rows),
        "rows": rows,
    }


def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    for col in df.columns:
        if df[col].dtype != "object":
            continue
        s = df[col].astype(str).str.strip()
        s = s.replace({"-": np.nan, "": np.nan})
        has_pct = s.str.endswith("%").any()
        if has_pct:
            s = s.str.rstrip("%")
        coerced = pd.to_numeric(s, errors="coerce")
        if coerced.notna().sum() >= df[col].notna().sum() * 0.5:
            df[col] = coerced
    return df


def _clean(v: Any) -> Any:
    if isinstance(v, float) and pd.isna(v):
        return None
    if hasattr(v, "item"):
        try:
            return v.item()
        except Exception:
            return v
    return v
