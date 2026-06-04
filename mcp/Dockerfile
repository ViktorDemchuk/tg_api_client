FROM python:3.12-slim

WORKDIR /app

COPY mcp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp/ .

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
