FROM python:3.13-slim

RUN useradd -r -s /bin/false botuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R botuser:botuser /app

USER botuser

CMD ["sh", "-c", "alembic upgrade head && python main.py"]
