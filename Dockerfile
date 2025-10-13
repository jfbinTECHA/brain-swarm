# Brain Swarm API Dockerfile
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set work directory
WORKDIR /app

# Install system dependencies for C++ compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    g++ \
    cmake \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install deps from repo root (build context MUST be the repo root)
COPY requirements*.txt /tmp/

# Guard: prove networkx pin exists in the file we install
RUN grep -i '^networkx==3\.3$' /tmp/requirements.txt

RUN pip install --no-cache-dir -r /tmp/requirements.txt \
 && pip install --no-cache-dir -r /tmp/requirements-bridge.txt \
 && pip install --no-cache-dir -r /tmp/requirements-cortex.txt \
 && pip install --no-cache-dir -r /tmp/requirements-dev.txt

# Import guard
COPY scripts/import_guard.py /tmp/import_guard.py
RUN python /tmp/import_guard.py

# Copy project
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn","backend.main:app","--host","0.0.0.0","--port","8000"]