# financial-data

MCP tool server for the external **Hermes** LLM agent harness. The repo's
only job is to expose stock-research tools Hermes can call over the
[Model Context Protocol](https://modelcontextprotocol.io). Hermes pulls the
Docker image, runs it, and consumes the tools — no database, no in-repo
agent code.

## Tools

| Tool | What it does |
| --- | --- |
| `finviz_screener` | Runs a Finviz screen and returns matching tickers with overview, valuation, financial and ownership columns merged. Accepts either a screener `url` pasted from the browser or an explicit `filters` string (plus optional `order`, `limit`). |
| `gurufocus_summary` | Scrapes the public GuruFocus `/stock/<TICKER>/summary` page via `curl_cffi` Chrome impersonation. Returns ~90 metrics including Moat Score, Piotroski / Altman / Beneish, all P/E and P/B variants, and the `Price-to-GF-Value`, `Price-to-Graham-Number`, `Price-to-Peter-Lynch-Fair-Value` ratios. Insider transactions and guru trades are paywalled and intentionally not returned — use the Finviz `sh_insidertrans_pos` filter column for insider signal. |
| `fred_macro` | Fetches FRED macro indicators (M2 money supply, UMich consumer sentiment, industrial production by default). Requires `FRED_API_KEY`. |

Tool descriptions and JSON schemas are advertised to the client during MCP
`list_tools`, so Hermes' LLM can pick the right one without extra prompting.

## Quick start (local)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# stdio (what Hermes typically uses):
PYTHONPATH=. python -m src.hermes_tools.server

# HTTP SSE on :8000:
PYTHONPATH=. python -m src.hermes_tools.server --transport sse
```

Smoke-test through a real MCP stdio client:

```bash
PYTHONPATH=. python scripts/smoke_mcp_stdio.py
```

## Docker

```bash
docker compose build
docker compose up           # SSE mode on :8000 (per docker-compose.yml)
```

For stdio integration, Hermes should `docker run -i` against the image and
let the entrypoint default to stdio:

```bash
docker run --rm -i --env-file prod.env tenjnd/financial-data:latest
```

## Configuration

Environment variables (loaded from `prod.env` / `dev.env`, gitignored):

- `FRED_API_KEY` — required only if the agent calls `fred_macro`.

The Finviz scraper and GuruFocus scraper need no credentials. GuruFocus
relies on `curl_cffi`'s `chrome` impersonation; if the site eventually
rotates its bot-detection, bump `IMPERSONATE` in
`src/hermes_tools/gurufocus.py` to a newer profile.

## Layout

```
src/
  hermes_tools/        # MCP server + tool wrappers (the public surface)
    server.py          # FastMCP entrypoint
    finviz.py
    gurufocus.py
    fred_macro.py
  api_adapters/        # Backend HTTP/SDK adapters used by the tools
    fred.py
    yahoo.py
  financial_data/      # Existing finviz scraper + pure valuation calcs
    stocks_screener.py
    stocks_financial_data.py   # graham/lynch/magic-formula fallbacks
  config.py
scripts/
  smoke_mcp_stdio.py   # real MCP client that drives the server over stdio
Dockerfile
docker-compose.yml
requirements.txt
```

## Adding a tool

1. Add a module under `src/hermes_tools/` exposing one pure function that
   takes JSON-friendly arguments and returns a JSON-friendly dict.
2. Wire it in `src/hermes_tools/server.py` with `@mcp.tool(description=...)`.
   Type-annotate parameters — FastMCP derives the JSON schema from them.
3. Rebuild the Docker image. Hermes picks the new tool up via `list_tools`
   on its next connection.
