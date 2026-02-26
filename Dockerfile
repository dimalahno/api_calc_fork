FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    REFERENCE_FILE_PATH=/app/справочник_УК_обновленный_2025_06_07_1.txt

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY tests ./tests
COPY scripts ./scripts
COPY справочник_УК_обновленный_2025_06_07_1.txt ./

RUN pip install --upgrade pip && pip install .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
