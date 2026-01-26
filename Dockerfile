FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml /app/
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir .

COPY . /app

EXPOSE 8001

CMD ["python", "-m", "uvicorn", "apps.web.main:app", "--host", "0.0.0.0", "--port", "8001"]
