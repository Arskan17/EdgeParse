"""Image OCR through the ``ocr_wasm.wasm`` engine (ocrs compiled to WASI).

The WASM module is loaded lazily on first use, so importing the adapter for
PDF-only work doesn't pay the model-loading cost.
"""
import html
import json
import statistics
import struct
import threading
from pathlib import Path

import wasmtime

_package_dir = Path(__file__).resolve().parent.parent / "package"

_lock = threading.Lock()
_runtime = None


class _OcrRuntime:
    def __init__(self, wasm_path: Path, models_dir: Path):
        engine = wasmtime.Engine()
        self.store = wasmtime.Store(engine)
        self.store.set_wasi(wasmtime.WasiConfig())
        linker = wasmtime.Linker(engine)
        linker.define_wasi()
        module = wasmtime.Module.from_file(engine, str(wasm_path))
        self.exports = linker.instantiate(self.store, module).exports(self.store)
        self.memory = self.exports["memory"]
        if "_initialize" in self.exports:
            self.exports["_initialize"](self.store)

        det = self._put((models_dir / "text-detection.onnx").read_bytes())
        rec = self._put((models_dir / "text-recognition.onnx").read_bytes())
        if self.exports["ocr_init"](self.store, *det, *rec) != 0:
            raise RuntimeError(self._last_error())

    def _put(self, data: bytes):
        ptr = self.exports["alloc"](self.store, len(data))
        self.memory.write(self.store, data, ptr)
        return ptr, len(data)

    def _take_string(self, ptr: int) -> str:
        (length,) = struct.unpack("<I", self.memory.read(self.store, ptr, ptr + 4))
        s = self.memory.read(self.store, ptr + 4, ptr + 4 + length).decode("utf-8")
        self.exports["free_result"](self.store, ptr)
        return s

    def _last_error(self) -> str:
        return self._take_string(self.exports["last_error"](self.store))

    def ocr(self, image_bytes: bytes) -> dict:
        ptr = self.exports["ocr_image"](self.store, *self._put(image_bytes))
        if not ptr:
            raise RuntimeError(f"OCR failed: {self._last_error()}")
        return json.loads(self._take_string(ptr))


def ocr_image(image_bytes: bytes) -> dict:
    """Run OCR and return ``{width, height, lines: [{text, bbox, words}]}``.

    Bounding boxes are ``[left, top, right, bottom]`` in pixels, origin top-left.
    """
    global _runtime
    with _lock:
        if _runtime is None:
            _runtime = _OcrRuntime(_package_dir / "ocr_wasm.wasm", _package_dir / "models")
        return _runtime.ocr(image_bytes)


def _paragraphs(lines: list) -> list:
    """Group lines into paragraphs where the vertical gap exceeds the norm."""
    if not lines:
        return []
    heights = [l["bbox"][3] - l["bbox"][1] for l in lines]
    threshold = statistics.median(heights) * 0.75
    paras = [[lines[0]]]
    for prev, line in zip(lines, lines[1:]):
        if line["bbox"][1] - prev["bbox"][3] > threshold:
            paras.append([])
        paras[-1].append(line)
    return paras


def render(result: dict, format: str) -> str:
    """Render an OCR result in the same output formats as the PDF engine."""
    paras = _paragraphs(result["lines"])

    if format in ("markdown", "text"):
        return "\n\n".join("\n".join(l["text"] for l in p) for p in paras) + "\n"

    if format == "html":
        body = "\n".join(
            "<p>" + "<br>\n".join(html.escape(l["text"]) for l in p) + "</p>" for p in paras
        )
        return f"<!DOCTYPE html>\n<html>\n<body>\n{body}\n</body>\n</html>\n"

    if format == "json":
        height = result["height"]
        kids = []
        for i, p in enumerate(paras):
            left = min(l["bbox"][0] for l in p)
            top = min(l["bbox"][1] for l in p)
            right = max(l["bbox"][2] for l in p)
            bottom = max(l["bbox"][3] for l in p)
            kids.append({
                "type": "paragraph",
                "id": i,
                "page number": 1,
                # PDF-style coordinates: origin bottom-left.
                "bounding box": [left, height - bottom, right, height - top],
                "font": "",
                "font size": 0,
                "text color": "",
                "content": "\n".join(l["text"] for l in p),
            })
        doc = {
            "number of pages": 1,
            "source": "ocr",
            "page size": [result["width"], height],
            "kids": kids,
        }
        return json.dumps(doc, ensure_ascii=False, indent=2)

    raise ValueError(f"Unsupported format: {format!r}")
