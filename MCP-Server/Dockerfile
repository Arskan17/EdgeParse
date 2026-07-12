FROM python:3.11-slim

RUN pip install uv --quiet

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project --quiet

COPY edgeparse_wasm_adapter/ ./edgeparse_wasm_adapter/
COPY package/ ./package/
COPY MCP-Server/md-document-parser.py ./MCP-Server/
RUN uv sync --no-dev --quiet

EXPOSE 8000

ENV TRANSPORT=streamable-http

CMD ["uv", "run", "python", "MCP-Server/md-document-parser.py"]
