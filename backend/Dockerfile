FROM python:3.11-slim

WORKDIR /app

# Install system runtime dependencies for OpenCV, Pillow, and PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure storage directories exist
RUN mkdir -p uploads cv/models

EXPOSE 8000

CMD ["sh", "-c", "python -m seed.seed_data && uvicorn main:app --host 0.0.0.0 --port 8000"]
