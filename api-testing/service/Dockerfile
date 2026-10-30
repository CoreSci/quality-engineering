# Bookshelf service image. The base image is pinned by digest (python:3.12-slim,
# multi-architecture index, recorded 2026-10-26); dependencies are pinned in
# requirements.txt.
FROM python:3.12-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --only-binary=:all: -r requirements.txt
COPY app.py isbn.py ./

RUN useradd --create-home --uid 10001 bookshelf
USER bookshelf

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

# Inside the container the server listens on all of the container's own interfaces:
# Docker's port publishing forwards traffic to the container's network interface,
# not to its loopback. compose.yaml publishes the port on the host's 127.0.0.1 only.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
