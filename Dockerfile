FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml uv.lock ./
COPY src/ src/

RUN uv sync --no-dev

CMD ["uv", "run", "open-medicine-mcp"]
