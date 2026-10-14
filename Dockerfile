# ==============================================================================
# AgroNex Root Dockerfile — FastAPI + ONNX Runtime + Sarvam AI
# Enables automated root-level container builds (e.g., Render, Railway, Vercel)
# ==============================================================================

FROM python:3.11-slim

# Prevent python from writing pyc files to disc and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for image processing and C++ ONNX runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies from backend directory
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application code & models into /app
COPY backend/ .

# Create uploads directory
RUN mkdir -p uploads

# Expose default backend port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Launch uvicorn dynamically binding to $PORT (Render/Cloud) or 8000 (Local/Docker)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
