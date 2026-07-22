FROM python:3.12-slim

WORKDIR /app
COPY . .
ENV PYTHONPATH=/app/src
EXPOSE 8080
CMD ["python", "-m", "money_maker.http_api", "--host", "0.0.0.0", "--port", "8080"]
