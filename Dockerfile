# ponytail: single stage, uv for fast installs. Multi-stage only if the image gets heavy.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/usr/local

# system libs InsightFace / onnxruntime / opencv need at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 tesseract-ocr tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# install deps first (cached layer) from the lockfile, then the project
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --all-extras
COPY . .
RUN uv sync --frozen --all-extras

CMD ["python", "-c", "import facefinder; print('facefinder ready')"]
