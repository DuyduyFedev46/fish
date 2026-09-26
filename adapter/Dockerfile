# Cảng cá Lộc — Adapter FastAPI trên Cloud Run (cangca-adapter).
# Lớp MỎNG: không đụng DB/ORM. Chỉ dùng requirements.txt (runtime), KHÔNG cài
# requirements-dev.txt (pytest/respx) vào image production.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Cloud Run cấp $PORT (mặc định 8080). Shell form để expand biến.
# Secret (SEPAY_SECRET_KEY, INTERNAL_SERVICE_TOKEN, ...) lấy từ biến môi trường/Secret
# Manager lúc chạy — KHÔNG copy .env vào image (xem .dockerignore).
CMD exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2
