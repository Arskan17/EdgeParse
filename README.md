# raphael-edgep

PDF-to-structured-data extraction using the **edgeparse** Rust engine compiled to WebAssembly.

## Why WASM?

The native `edgeparse` Python package ships a PyO3 native extension — one `.so` per platform. This project uses the `edgeparse-wasm` WebAssembly build instead, loaded via `wasmtime`. Benefits:

- **Single binary** — the same `.wasm` file works on any OS/arch
- **No native compilation** — no platform-specific wheels, no build tools
- **Sandboxed** — WASM runtime provides memory safety and isolation
- **Deterministic** — same engine, identical output to the native Python SDK

## Quick start

```bash
# Install dependencies
uv sync

# Run extraction
uv run python main.py
```

## Usage

```python
import edgeparse_wasm_adapter as edgeparse
import json

# Markdown
md = edgeparse.convert("document.pdf", format="markdown")

# JSON with bounding boxes
data = json.loads(edgeparse.convert("document.pdf", format="json"))

# Table clustering for borderless tables
data = json.loads(edgeparse.convert("document.pdf", format="json", table_method="cluster"))
```

## API

### `convert(input_path, *, format, pages, password, reading_order, table_method, image_output)`

Converts a PDF to a formatted string. Supports the same arguments as the native `edgeparse.convert()`.

| Argument     | Default      | Description                           |
|-------------|-------------|---------------------------------------|
| `format`    | `"markdown"` | `"markdown"`, `"json"`, `"html"`, `"text"` |
| `pages`     | `None`       | Page range, e.g. `"1,3,5-7"` or `"all"` |
| `password`  | `None`       | Not supported in WASM (ignored)       |
| `reading_order` | `"xycut"` | `"xycut"` or `"off"`               |
| `table_method` | `"default"` | `"default"` or `"cluster"`          |
| `image_output` | `"off"`    | Not supported in WASM (ignored)       |

### `convert_file(input_path, output_dir, *, format, pages, password)`

Converts and writes to a file. Returns the output file path.

### `version()`

Returns the edgeparse version string.

## Project structure

```
├── edgeparse_wasm_adapter.py   # Python WASM adapter (wasmtime)
├── package/
│   └── edgeparse_wasm_bg.wasm  # EdgeParse WASM binary
├── main.py                     # Usage example
├── input_files/                # Sample PDFs
├── output_files/               # Generated output
├── pyproject.toml
└── README.md
```
