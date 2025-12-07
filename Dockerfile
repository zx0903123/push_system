FROM python:3.11-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 安裝 debugpy 與 uvicorn[standard]（支援 reload）
RUN pip install debugpy uvicorn[standard] fastapi

# COPY . /app
COPY . .

# 直接啟動 server，非 debug 模式
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
