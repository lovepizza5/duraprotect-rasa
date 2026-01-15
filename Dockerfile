FROM python:3.10-slim

WORKDIR /app

# System deps (some wheels may need it)
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x start.sh

CMD ["bash", "-lc", "./start.sh"]
