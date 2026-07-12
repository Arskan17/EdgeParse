import os
import sys
import tempfile
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP
from edgeparse_wasm_adapter import convert

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


mcp = FastMCP("document-parser")

_DOWNLOAD_TIMEOUT = 120


def _infer_extension(url: str, content_type: str | None) -> str:
    path = Path(url)
    ext = path.suffix.lower()
    if ext in (".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp"):
        return ext
    if content_type:
        ct_map = {
            "application/pdf": ".pdf",
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/gif": ".gif",
            "image/bmp": ".bmp",
            "image/tiff": ".tiff",
            "image/webp": ".webp",
        }
        for key, val in ct_map.items():
            if key in content_type:
                return val
    return ".pdf"


def _download_and_process(url: str, fmt: str, pages: str | None = None, table_method: str = "default") -> str:
    with httpx.Client(timeout=_DOWNLOAD_TIMEOUT, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()

    content_type = resp.headers.get("content-type")
    ext = _infer_extension(url, content_type)

    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    try:
        tmp.write(resp.content)
        tmp.close()
        result = convert(tmp.name, format=fmt, pages=pages, table_method=table_method)
        return result
    finally:
        os.unlink(tmp.name)


@mcp.tool()
def extract_markdown(url: str, pages: str | None = None, table_method: str = "default") -> str:
    """Extract Markdown from a PDF or image at the given URL."""
    return _download_and_process(url, "markdown", pages, table_method)


@mcp.tool()
def extract_json(url: str, pages: str | None = None, table_method: str = "default") -> str:
    """Extract JSON with bounding boxes from a PDF or image at the given URL."""
    return _download_and_process(url, "json", pages, table_method)


@mcp.tool()
def extract_html(url: str, pages: str | None = None, table_method: str = "default") -> str:
    """Extract HTML from a PDF or image at the given URL."""
    return _download_and_process(url, "html", pages, table_method)


@mcp.tool()
def extract_text(url: str, pages: str | None = None, table_method: str = "default") -> str:
    """Extract plain text from a PDF or image at the given URL."""
    return _download_and_process(url, "text", pages, table_method)


if __name__ == "__main__":
    mcp.run()
