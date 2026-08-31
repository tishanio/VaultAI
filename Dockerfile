FROM python:3.11-slim AS base

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY vault/ vault/
COPY services/ services/

EXPOSE 8000

CMD ["uvicorn", "services.api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
