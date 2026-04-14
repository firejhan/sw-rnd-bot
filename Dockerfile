FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    fonts-liberation \
    libgbm1 \
    libnss3 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libxss1 \
    libasound2 \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

ENV PLAYWRIGHT_BROWSERS_PATH=/usr/bin
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium --with-deps

COPY . .

CMD ["python", "main.py"]
