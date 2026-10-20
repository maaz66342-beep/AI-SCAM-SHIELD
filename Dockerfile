FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Retrain the model inside the image so it matches the installed scikit-learn version
RUN python train_job_model.py
ENV PORT=10000
CMD gunicorn app:app --bind 0.0.0.0:${PORT} --workers 1 --timeout 120
