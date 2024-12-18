# Use Python 3.9 slim image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    nodejs \
    npm \
    firefox-esr \
    xvfb \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    xdg-utils \
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
RUN mkdir -p /data/cookies && \
    chmod 777 /data/cookies

# Set up Xvfb
RUN printf '#!/bin/bash\nXvfb :99 -screen 0 1024x768x16 &\nexec "$@"' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Copy application code
COPY app/ /app/

# Expose port
EXPOSE 8000

# Use entrypoint script to start Xvfb before the application
ENTRYPOINT ["/entrypoint.sh"]

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]