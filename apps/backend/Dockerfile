FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY apps/backend/requirements.txt apps/backend/requirements-dev.txt ./apps/backend/
RUN pip install --no-cache-dir -r apps/backend/requirements.txt

WORKDIR /app/apps/backend
COPY apps/backend/src ./src

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
