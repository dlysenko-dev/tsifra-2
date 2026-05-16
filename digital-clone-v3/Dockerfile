FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y \
    ffmpeg \
    chromium \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libnss3 \
    libxss1 \
    libasound2 \
    libgbm-dev \
    fonts-noto \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

COPY . .

CMD ["python", "-m", "core.jarvis_v3"]
