FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    MCP_TRANSPORT=http \
    GAMEMASTER_STORAGE_DIR=/data

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

RUN mkdir -p /data
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:%s/health' % os.getenv('PORT','8000'))"

CMD ["gamemaster-mcp"]
