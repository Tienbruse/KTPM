FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY services/company_search_service ./company_search_service

ENV PYTHONPATH="/app/company_search_service/src:${PYTHONPATH}"

EXPOSE 9010

CMD ["uvicorn", "company_search_service.app:app", "--host", "0.0.0.0", "--port", "9010"]
