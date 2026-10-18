# Reproducible runtime for the measurement pipeline.
# Build:  docker build -t phishing-study .
# Run:    docker run --rm -v "$(pwd)/results:/app/results" phishing-study
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first → this layer is cached until requirements.txt changes
COPY requirements.txt .
RUN pip install --no-deps -r requirements.txt && pip check

# Only what the pipeline needs (see .dockerignore)
COPY configs/ configs/
COPY data/sample/ data/sample/
COPY src/ src/
COPY tests/ tests/

ENTRYPOINT ["python", "src/benchmark.py"]
CMD ["--config", "configs/config.yaml"]
