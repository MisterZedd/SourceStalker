# Dockerfile for SourceStalker V3
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    libsqlite3-dev \
    tk-dev \
    python3-tk \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/config /app/emoji_assets

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH=/app/data/rank_tracker.db

# Create volume mount points
VOLUME ["/app/data", "/app/config", "/app/emoji_assets"]

# Set the entrypoint
CMD ["python", "main.py"]