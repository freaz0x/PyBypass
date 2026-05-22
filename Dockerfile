# Image officielle Playwright — tout est déjà installé (Chromium + dépendances)
FROM mcr.microsoft.com/playwright/python:v1.52.0-noble

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY main.py .

# Port exposé par Render
ENV PORT=8000

CMD ["python", "main.py"]
