FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install-deps chromium && playwright install chromium

COPY *.py .

CMD ["python", "main.py"]
