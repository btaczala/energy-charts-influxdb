FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim
RUN mkdir /app
WORKDIR /app
COPY pyproject.toml .
COPY uv.lock .
RUN uv sync
COPY import_prices_to_influx.py .
COPY energy_prices_script.py .
CMD ["uv", "run", "python", "import_prices_to_influx.py", "--loop"]