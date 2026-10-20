# TheHealthTracker — one container: FastAPI + the static app, site, admin and partner portals.
# Runs the same on Cloud Run, any container host, or locally:  docker build -t tht . && docker run -p 8080:8080 tht
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PORT=8080
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN useradd --create-home --uid 10001 tht && mkdir -p /app/data && chown -R tht:tht /app/data
USER tht

EXPOSE 8080
# one worker on purpose: video-call rooms and the daily jobs live in this process (see GOOGLE_CLOUD.md)
CMD ["sh", "-c", "exec uvicorn server:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --no-access-log --proxy-headers --forwarded-allow-ips='*'"]
