FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/* \
    && useradd -r -u 1001 inkgrade && mkdir -p /data/uploads && chown -R inkgrade /data
WORKDIR /srv
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY app ./app
USER inkgrade
ENV STORAGE_ROOT=/data/uploads
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=5s --retries=20 CMD curl -fs http://localhost:8080/actuator/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
