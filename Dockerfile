FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV HOST=0.0.0.0 PORT=9000
EXPOSE 9000
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","9000"]
