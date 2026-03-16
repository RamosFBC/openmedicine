FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ src/

# Install dependencies (service + graphrag for full capabilities)
RUN uv sync --extra service --extra graphrag --no-dev

EXPOSE 8000

CMD ["uv", "run", "open-medicine-server"]
