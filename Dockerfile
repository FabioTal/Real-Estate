FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install playwright && playwright install chromium && playwright install-deps chromium

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ ./backend/

CMD ["python3", "backend/scheduler.py"]
