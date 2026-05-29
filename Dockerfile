# build stage
FROM python:3.12-slim AS builder

WORKDIR /app

RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt


# app stage
FROM python:3.12-slim

RUN groupadd -g 999 python && useradd -r -u 999 -g python python && \
    mkdir /app && chown python:python /app

WORKDIR /app

COPY --chown=python:python --from=builder /app/venv ./venv
COPY --chown=python:python src /app/src

USER 999
ENV PATH="/app/venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Default to stdio; pass --transport sse to expose over HTTP/SSE.
ENTRYPOINT ["python", "-m", "src.hermes_tools.server"]
