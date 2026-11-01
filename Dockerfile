FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend ./backend
ENV PYTHONPATH=/app/backend DATA_DIR=/tmp/study MODEL_CACHE=/app/model-cache
RUN uv run python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5',cache_dir='/app/model-cache',threads=1)"
RUN useradd --create-home study && mkdir -p /tmp/study && chown study /tmp/study && chown -R study /app/model-cache
USER study
CMD ["sh", "-c", "uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-access-log"]
