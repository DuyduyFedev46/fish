# Cảng cá Lộc — Django core trên Cloud Run.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# psycopg[binary] không cần build tool; giữ image gọn.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Gom static của Admin vào STATIC_ROOT để WhiteNoise phục vụ.
# DJANGO_DEBUG=1 lúc build chỉ để tránh yêu cầu cấu hình prod; không ảnh hưởng runtime.
RUN DJANGO_DEBUG=1 python manage.py collectstatic --noinput

# Cloud Run cấp $PORT (mặc định 8080). Shell form để expand biến.
CMD exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
