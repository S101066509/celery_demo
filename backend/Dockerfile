# --- Build Stage ---
FROM python:3.12-slim AS builder

WORKDIR /app

# Prevent Python from writing .pyc files & buffering output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for psycopg and other libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 🚀 建立並啟動虛擬環境 (Virtual Environment)
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install python dependencies inside the venv
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Final Stage ---
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# 複製整個虛擬環境資料夾，確保所有二進位檔案都完整轉移
COPY --from=builder /opt/venv /opt/venv

# 在最終階段啟用虛擬環境
ENV PATH="/opt/venv/bin:$PATH"

# Set Python environment variables for runtime
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy project files
COPY . .

# Expose port for internal communication (Gunicorn)
EXPOSE 8000

# Metadata / Version (Optional)
LABEL maintainer="Antigravity Trader"
LABEL version="1.0"

# Command to sync and run (default entrypoint)
CMD ["sh", "-c", "python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000"]