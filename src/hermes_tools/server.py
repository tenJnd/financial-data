"""MCP server exposing stock-research tools to the Hermes agent harness.

Run via the package entrypoint::

    python -m src.hermes_tools.server                 # stdio (default)
    python -m src.hermes_tools.server --transport sse # HTTP SSE

Hermes typically launches the stdio variant inside the Docker image.
"""
from __future__ import annotations

import argparse
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from src.hermes_tools.finviz import run_finviz_screener
from src.hermes_tools.fred_macro import fetch_fred_macro
from src.hermes_tools.gurufocus import GuruFocusBlocked, fetch_gurufocus_summary

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

mcp = FastMCP("hermes-stock-research")


@mcp.tool(
    description=(
        "Run a Finviz screener and return matching tickers with fundamental "
        "columns merged from the overview, valuation, financial, and ownership "
        "views. Provide either `url` (paste a finviz screener URL from the "
        "browser, e.g. https://finviz.com/screener?v=351&f=fa_roa_pos,...&o=-roa) "
        "or an explicit `filters` string (comma-separated finviz filter codes). "
        "`order` defaults to '-roa'. `limit` caps the number of rows returned."
    )
)
def finviz_screener(
    url: str | None = None,
    filters: str | None = None,
    order: str = "-roa",
    limit: int = 50,
) -> dict[str, Any]:
    return run_finviz_screener(url=url, filters=filters, order=order, limit=limit)


@mcp.tool(
    description=(
        "Fetch the publicly-visible GuruFocus stock summary for a single ticker. "
        "Returns ~90 metrics including Moat Score, GF Score components, "
        "Piotroski / Altman / Beneish, ROE/ROA/ROIC, all P/E and P/B variants, "
        "and crucially the Price-to-GF-Value / Price-to-Graham-Number / "
        "Price-to-Peter-Lynch-Fair-Value ratios. Insider transactions and guru "
        "trades are NOT included because GuruFocus paywalls those sections."
    )
)
def gurufocus_summary(ticker: str) -> dict[str, Any]:
    try:
        return fetch_gurufocus_summary(ticker)
    except GuruFocusBlocked as exc:
        return {"ticker": ticker.upper(), "error": "blocked", "detail": str(exc)}


@mcp.tool(
    description=(
        "Fetch FRED macro indicators (defaults: M2 money supply, University of "
        "Michigan consumer sentiment, industrial production). Requires the "
        "FRED_API_KEY env var to be set inside the container."
    )
)
def fred_macro(
    series: dict[str, str] | None = None,
    look_back_years: int = 2,
    latest_only: bool = False,
) -> dict[str, Any]:
    return fetch_fred_macro(series=series, look_back_years=look_back_years, latest_only=latest_only)


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes stock-research MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport for the MCP connection (default: stdio)",
    )
    args = parser.parse_args()
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
