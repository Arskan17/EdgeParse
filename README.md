# raphael-edgep

PDF-to-structured-data extraction using the **edgeparse** Rust engine compiled to WebAssembly — with CLI, Python API, MCP server, and opencode skill interfaces.

## Why WASM?

The native `edgeparse` Python package ships a PyO3 native extension — one `.so` per platform. This project uses the `edgeparse-wasm` WebAssembly build instead, loaded via `wasmtime`.

- **Single binary** — the same `.wasm` file works on any OS/arch
- **No native compilation** — no platform-specific wheels, no build tools
- **Sandboxed** — WASM runtime provides memory safety and isolation
- **Deterministic** — same engine, identical output to the native Python SDK

## Features

- **PDF extraction** — Markdown, JSON with bounding boxes, HTML, plain text
- **Image support** — PNG, JPG, WebP, BMP, TIFF auto-converted to PDF via `img2pdf`
- **Table clustering** — `table_method="cluster"` for borderless tables
- **JSON normalization** — WASM output transformed to match the native `edgeparse` JSON schema
- **CLI** — glob patterns, batch processing, `python -m edgeparse_wasm_adapter`
- **MCP server** — URL-based tools for AI agents (`extract_markdown`, `extract_json`, `extract_html`, `extract_text`)
- **Docker** — containerized MCP server for cloud/remote deployment
- **Opencode skill** — registered at `~/.agents/skills/document-parse/SKILL.md`

## Quick start

```bash
uv sync
uv run python main.py
```

## Python API

```python
import edgeparse_wasm_adapter as edgeparse
import json

# Markdown for LLM context
md = edgeparse.convert("report.pdf", format="markdown")

# JSON with bounding boxes for RAG citations
data = json.loads(edgeparse.convert("report.pdf", format="json"))

# Image file (auto-converts to PDF via img2pdf)
md = edgeparse.convert("screenshot.png", format="markdown")

# Table clustering for borderless tables
data = json.loads(edgeparse.convert("report.pdf", format="json", table_method="cluster"))

# Convert and write to file
path = edgeparse.convert_file("report.pdf", output_dir="output/", format="markdown")
```

### `convert(input_path, *, format, pages, password, reading_order, table_method, image_output)`

| Argument       | Default      | Description                              |
|---------------|-------------|------------------------------------------|
| `format`      | `"markdown"` | `"markdown"`, `"json"`, `"html"`, `"text"` |
| `pages`       | `None`       | Page range e.g. `"1,3,5-7"`              |
| `password`    | `None`       | ⚠ Not supported (ignored)                |
| `reading_order`| `"xycut"`   | `"xycut"` or `"off"`                     |
| `table_method`| `"default"`  | `"default"` or `"cluster"`               |

Input can be a PDF (`.pdf`) or image (`.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`, `.tiff`, `.gif`). Images are auto-converted to PDF via `img2pdf` before extraction.

### `convert_file(input_path, output_dir, *, format, pages, password)`

Converts and writes to a file. Returns the output file path.

### `version()`

Returns the edgeparse WASM version string.

## CLI

```bash
# Extract single file
uv run python -m edgeparse_wasm_adapter document.pdf -f json -o output/

# Extract image
uv run python -m edgeparse_wasm_adapter screenshot.png -f markdown

# Batch with glob patterns
uv run python -m edgeparse_wasm_adapter "*.pdf" -f markdown

# With table clustering
uv run python -m edgeparse_wasm_adapter document.pdf -f json -t cluster
```

| Flag | Default | Description |
|------|---------|-------------|
| `-f`, `--format` | `markdown` | Output format (markdown, json, html, text) |
| `-o`, `--output-dir` | `output` | Output directory |
| `-p`, `--pages` | — | Page range e.g. `1,3,5-7` |
| `-t`, `--table-method` | `default` | Table detection (default, cluster) |
| `-r`, `--reading-order` | `xycut` | Reading order (xycut, off) |

## MCP Server

A Model Context Protocol server that exposes 4 URL-based extraction tools for AI agents. Files are downloaded, processed, and cleaned up — no local file paths needed.

### Tools

| Tool | Returns | Description |
|------|---------|-------------|
| `extract_markdown(url, pages, table_method)` | `str` | Extract Markdown from a URL |
| `extract_json(url, pages, table_method)` | `str` | Extract JSON with bounding boxes |
| `extract_html(url, pages, table_method)` | `str` | Extract HTML |
| `extract_text(url, pages, table_method)` | `str` | Extract plain text |

### Local (stdio)

The server is registered in `~/.config/opencode/opencode.json` and ready for use with opencode:

```bash
opencode mcp list  # should show document-parser as connected
```

To start manually:

```bash
TRANSPORT=stdio uv run python MCP-Server/md-document-parser.py
```

### Docker

```bash
# Build and run
cd MCP-Server
docker compose up -d

# Uses streamable-http transport on port 6274
# Add to opencode config:
# "document-parser-remote": {
#   "type": "remote",
#   "url": "http://localhost:6274",
#   "enabled": true
# }
```

## Opencode Skill

The project is available as an opencode skill at `~/.agents/skills/document-parse/SKILL.md`. It triggers on PDF extraction, document parsing, and image-to-text tasks.

## Project structure

```
├── edgeparse_wasm_adapter/    # Python package (wasmtime adapter)
│   ├── __init__.py            # Core WASM adapter + public API
│   └── __main__.py            # CLI entry point
├── package/
│   └── edgeparse_wasm_bg.wasm # EdgeParse WASM binary (~2.8 MB)
├── MCP-Server/
│   ├── md-document-parser.py  # MCP server with URL-based tools
│   ├── Dockerfile             # Container image
│   └── docker-compose.yml     # Quick container start
├── main.py                    # Usage demo
├── input_files/               # Sample PDFs and images
├── output_files/              # Generated output
├── pyproject.toml
└── README.md
```
