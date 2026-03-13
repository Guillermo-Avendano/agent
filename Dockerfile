FROM python:3.12-slim

WORKDIR /app

# System deps for psycopg2, matplotlib, and healthcheck
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq-dev gcc fonts-dejavu-core curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Charts output directory
RUN mkdir -p /app/charts_output

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
