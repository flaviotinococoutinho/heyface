FROM python:3.12-slim-bookworm AS base
COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 PATH="/app/.venv/bin:$PATH" \
    TORCH_FORCE_WEIGHTS_ONLY_LOAD=1 HF_HUB_OFFLINE=1
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --no-cache

FROM base AS runtime
RUN useradd --uid 10001 --no-log-init --create-home vision
COPY app ./app
USER vision
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--limit-concurrency", "12", "--timeout-keep-alive", "5", "--no-access-log"]

FROM base AS test
RUN uv sync --frozen --no-install-project --no-cache
COPY app ./app
COPY tests ./tests
CMD ["pytest", "-q"]
