# Use Python 3.9 slim image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    nodejs \
    firefox-esr \
    npm \
    xvfb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies with upgraded pip
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN python -m playwright install --with-deps firefox chromium

# Create directory for cookies
RUN mkdir -p /data/cookies

# Copy application code
COPY app/ /app/

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["xvfb-run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]