# Use Python 3.11 slim as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    pkg-config \
    build-essential \
    python3-dev \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# # Install Chrome and its dependencies
# RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
#     && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
#     && apt-get update \
#     && apt-get install -y --no-install-recommends \
#     google-chrome-stable \
#     fonts-ipafont-gothic \
#     fonts-wqy-zenhei \
#     fonts-thai-tlwg \
#     fonts-kacst \
#     fonts-symbola \
#     fonts-noto \
#     fonts-freefont-ttf \
#     && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# # Install Playwright browsers
# RUN playwright install chromium \
#     && playwright install-deps chromium

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /tmp/logs \
    && mkdir -p /app/certs

# Set permissions
RUN chmod -R 755 /app

# Create a non-root user
# RUN useradd -m -u 1000 appuser \
#     && chown -R appuser:appuser /app /tmp/logs
# USER appuser

# Command to run the application
CMD ["python", "fetch_csls.py"] 