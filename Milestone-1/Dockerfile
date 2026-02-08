# Multi-stage Dockerfile for voice-based assistant with prebuilt face recognition
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (dlib needs build tools)
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY templates/ ./templates/
COPY static/ ./static/

# Create database directory
RUN mkdir -p /app/instance

# Expose Flask port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
