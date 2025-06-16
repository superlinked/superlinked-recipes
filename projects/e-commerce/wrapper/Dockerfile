FROM python:3.11.9 AS python-base

WORKDIR /app
COPY ./endpoint.py .
COPY ./requirements.txt .
## COPY KV DIR AND CONTENT
COPY ./kv /kv
COPY ./config /config
## copy .env
COPY ./.env .

RUN python -m pip install -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "endpoint:app", "--host", "0.0.0.0", "--port", "8000"]