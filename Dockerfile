FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 gcc build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /hive-backend
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh
EXPOSE 8090
CMD ["sh", "entrypoint.sh"]
