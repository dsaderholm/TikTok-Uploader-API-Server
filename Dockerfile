FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    firefox-esr \
    npm \
    nodejs \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Install Python requirements first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN python -m playwright install

# Find tiktokautouploader package location and install Node.js dependencies
RUN PACKAGE_DIR=$(pip show tiktokautouploader | grep Location | cut -d ' ' -f 2) && \
    cd $PACKAGE_DIR/tiktokautouploader/Js_assets && \
    npm install playwright playwright-extra puppeteer-extra-plugin-stealth && \
    npx playwright install chromium

# Copy application code
COPY app .

# Create directories for uploads and cookies
RUN mkdir -p uploads cookies

CMD ["python", "main.py"]
