FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY templates/ ./templates/
COPY dashboards.json .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

EXPOSE 8060

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8060"]