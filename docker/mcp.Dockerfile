FROM python:3.12-slim
WORKDIR /srv
COPY mcp-server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mcp-server/server.py .
ENV MCP_TRANSPORT=sse
CMD ["python", "server.py"]
