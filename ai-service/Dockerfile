FROM python:3.11-slim
ARG INSTALL_ML=false
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY requirements.txt requirements-ml.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$INSTALL_ML" = "true" ]; then pip install --no-cache-dir -r requirements-ml.txt; fi
COPY app ./app
EXPOSE 8001
HEALTHCHECK --interval=15s --timeout=5s --retries=10 CMD curl -fs http://localhost:8001/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
