FROM python:3.9-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Ensure data directory exists
RUN mkdir -p data
# Data file must be mounted or present in data/ during this step
RUN python3 import_data_v3.py
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
