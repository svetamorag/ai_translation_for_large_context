FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . .

ENV PORT 8080

# CHANGE: Use ENTRYPOINT with main.py
# This allows arguments passed from gcloud to be appended to this command
ENTRYPOINT ["python", "main.py"]