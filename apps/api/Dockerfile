FROM python:3.11-slim
WORKDIR /app
COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api/app ./app
COPY apps/api/scripts ./scripts
COPY apps/api/scripts ./scripts
COPY legacy ./legacy
COPY config ./config
COPY data ./data
ENV PYTHONPATH=/app:/app/legacy
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
