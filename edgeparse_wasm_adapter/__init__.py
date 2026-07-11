import os
import sys
import io
import struct
import traceback
import json
import img2pdf
import wasmtime
from pathlib import Path
from typing import Optional, Union

PathLike = Union[str, os.PathLike]

_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif', '.webp'}

class WasmContext:
    def __init__(self):
        self.reset()

    def reset(self):
        self.heap = [None] * 1024
        self.heap.extend([None, None, True, False])
        self.free_list = []

    def add_heap_object(self, obj):
        if self.free_list:
            idx = self.free_list.pop()
            self.heap[idx] = obj
            return idx
        idx = len(self.heap)
        self.heap.append(obj)
        return idx

    def get_object(self, idx):
        if 0 <= idx < len(self.heap):
            return self.heap[idx]
        return None

    def drop_object(self, idx):
        if idx >= 1028 and idx < len(self.heap):
            self.heap[idx] = None
            self.free_list.append(idx)

    def take_object(self, idx):
        obj = self.get_object(idx)
        self.drop_object(idx)
        return obj

engine = wasmtime.Engine()
store = wasmtime.Store(engine)
linker = wasmtime.Linker(engine)
ctx = WasmContext()
exports = {}

adapter_dir = Path(__file__).parent.resolve()
wasm_path = adapter_dir / "package" / "edgeparse_wasm_bg.wasm"
if not wasm_path.exists():
    wasm_path = adapter_dir.parent / "package" / "edgeparse_wasm_bg.wasm"
if not wasm_path.exists():
    wasm_path = adapter_dir / "edgeparse_wasm_bg.wasm"

if not wasm_path.exists():
    raise FileNotFoundError(
        f"Could not locate 'edgeparse_wasm_bg.wasm' in {adapter_dir}, {adapter_dir}/package/, or {adapter_dir.parent}/package/"
    )

def get_string_from_wasm(caller, ptr, length):
    memory = caller.get_export("memory")
    if not memory:
        return ""
    data = memory.read(caller, ptr, ptr + length)
    return data.decode("utf-8")

def pass_string_to_wasm(store_or_caller, s):
    if s is None:
        return 0, 0
    utf8_bytes = s.encode('utf-8')
    malloc_func = exports["__wbindgen_export"]
    ptr = malloc_func(store_or_caller, len(utf8_bytes), 1)
    memory = exports["memory"]
    memory.write(store_or_caller, utf8_bytes, ptr)
    return ptr, len(utf8_bytes)

def pass_bytes_to_wasm(store_or_caller, b):
    malloc_func = exports["__wbindgen_export"]
    ptr = malloc_func(store_or_caller, len(b), 1)
    memory = exports["memory"]
    memory.write(store_or_caller, b, ptr)
    return ptr, len(b)

def __wbindgen_object_drop_ref(caller, idx):
    ctx.drop_object(idx)

def __wbg_set_282384002438957f(caller, obj_idx, index, val_idx):
    obj = ctx.get_object(obj_idx)
    val = ctx.take_object(val_idx)
    if isinstance(obj, list):
        while len(obj) <= index:
            obj.append(None)
        obj[index] = val

def __wbindgen_object_clone_ref(caller, idx):
    obj = ctx.get_object(idx)
    return ctx.add_heap_object(obj)

def __wbg_set_6be42768c690e380(caller, obj_idx, key_idx, val_idx):
    obj = ctx.get_object(obj_idx)
    key = ctx.take_object(key_idx)
    val = ctx.take_object(val_idx)
    if isinstance(obj, dict):
        obj[key] = val

def __wbg_String_8564e559799eccda(caller, retptr, obj_idx):
    obj = ctx.get_object(obj_idx)
    s = str(obj)
    ptr, length = pass_string_to_wasm(caller, s)
    memory = caller.get_export("memory")
    data = struct.pack("<II", ptr, length)
    memory.write(caller, data, retptr)

def _log_objs(level, arg0, arg1, arg2, arg3):
    objs = [ctx.get_object(x) for x in (arg0, arg1, arg2, arg3)]
    print(f"[{level}]", " ".join(str(o) for o in objs if o is not None), file=sys.stderr)

def __wbg_log_70972330cfc941dd(caller, arg0, arg1, arg2, arg3):
    _log_objs("LOG", arg0, arg1, arg2, arg3)

def __wbg_info_0194681687b5ab04(caller, arg0, arg1, arg2, arg3):
    _log_objs("INFO", arg0, arg1, arg2, arg3)

def __wbg_warn_809cad1bfc2b3a42(caller, arg0, arg1, arg2, arg3):
    _log_objs("WARN", arg0, arg1, arg2, arg3)

def __wbg_debug_271c16e6de0bc226(caller, arg0, arg1, arg2, arg3):
    _log_objs("DEBUG", arg0, arg1, arg2, arg3)

def __wbg_error_1eece6b0039034ce(caller, arg0, arg1, arg2, arg3):
    _log_objs("ERROR", arg0, arg1, arg2, arg3)

def __wbg_new_a70fbab9066b301f(caller):
    return ctx.add_heap_object([])

def __wbg_new_ab79df5bd7c26067(caller):
    return ctx.add_heap_object({})

def __wbg_new_227d7c05414eb861(caller):
    return ctx.add_heap_object(Exception("JS Error"))

def __wbg_stack_3b0d974bbf31e44f(caller, retptr, obj_idx):
    obj = ctx.get_object(obj_idx)
    if isinstance(obj, Exception):
        s = "".join(traceback.format_exception(type(obj), obj, obj.__traceback__))
    else:
        s = str(obj)
    ptr, length = pass_string_to_wasm(caller, s)
    memory = caller.get_export("memory")
    data = struct.pack("<II", ptr, length)
    memory.write(caller, data, retptr)

def __wbg_error_a6fa202b58aa1cd3(caller, ptr, length):
    s = get_string_from_wasm(caller, ptr, length)
    print("[ERROR]", s, file=sys.stderr)

def __wbg_getRandomValues_3f44b700395062e5(caller, ptr, length):
    random_bytes = os.urandom(length)
    memory = caller.get_export("memory")
    memory.write(caller, random_bytes, ptr)

def __wbg___wbindgen_throw_6ddd609b62940d55(caller, ptr, length):
    s = get_string_from_wasm(caller, ptr, length)
    raise Exception(f"WASM Bindgen Exception: {s}")

def __wbg_Error_83742b46f01ce22d(caller, ptr, length):
    s = get_string_from_wasm(caller, ptr, length)
    return ctx.add_heap_object(Exception(s))

def __wbindgen_cast_0000000000000001(caller, val):
    return ctx.add_heap_object(val)

def __wbindgen_cast_0000000000000002(caller, val):
    return ctx.add_heap_object(val)

def __wbindgen_cast_0000000000000003(caller, ptr, length):
    s = get_string_from_wasm(caller, ptr, length)
    return ctx.add_heap_object(s)

def __wbindgen_cast_0000000000000004(caller, val):
    return ctx.add_heap_object(val)

import_callbacks = {
    "__wbindgen_object_drop_ref": __wbindgen_object_drop_ref,
    "__wbg_set_282384002438957f": __wbg_set_282384002438957f,
    "__wbindgen_object_clone_ref": __wbindgen_object_clone_ref,
    "__wbg_set_6be42768c690e380": __wbg_set_6be42768c690e380,
    "__wbg_String_8564e559799eccda": __wbg_String_8564e559799eccda,
    "__wbg_log_70972330cfc941dd": __wbg_log_70972330cfc941dd,
    "__wbg_info_0194681687b5ab04": __wbg_info_0194681687b5ab04,
    "__wbg_warn_809cad1bfc2b3a42": __wbg_warn_809cad1bfc2b3a42,
    "__wbg_debug_271c16e6de0bc226": __wbg_debug_271c16e6de0bc226,
    "__wbg_error_1eece6b0039034ce": __wbg_error_1eece6b0039034ce,
    "__wbg_new_a70fbab9066b301f": __wbg_new_a70fbab9066b301f,
    "__wbg_new_ab79df5bd7c26067": __wbg_new_ab79df5bd7c26067,
    "__wbg_new_227d7c05414eb861": __wbg_new_227d7c05414eb861,
    "__wbg_stack_3b0d974bbf31e44f": __wbg_stack_3b0d974bbf31e44f,
    "__wbg_error_a6fa202b58aa1cd3": __wbg_error_a6fa202b58aa1cd3,
    "__wbg_getRandomValues_3f44b700395062e5": __wbg_getRandomValues_3f44b700395062e5,
    "__wbg___wbindgen_throw_6ddd609b62940d55": __wbg___wbindgen_throw_6ddd609b62940d55,
    "__wbg_Error_83742b46f01ce22d": __wbg_Error_83742b46f01ce22d,
    "__wbindgen_cast_0000000000000001": __wbindgen_cast_0000000000000001,
    "__wbindgen_cast_0000000000000002": __wbindgen_cast_0000000000000002,
    "__wbindgen_cast_0000000000000003": __wbindgen_cast_0000000000000003,
    "__wbindgen_cast_0000000000000004": __wbindgen_cast_0000000000000004,
}

module = wasmtime.Module.from_file(engine, str(wasm_path))
for imp in module.imports:
    callback = import_callbacks.get(imp.name)
    if callback:
        linker.define_func(imp.module, imp.name, imp.type, callback, access_caller=True)

instance = linker.instantiate(store, module)

for exp in module.exports:
    exports[exp.name] = instance.exports(store)[exp.name]

exports["__wbindgen_start"](store)


def convert(
    input_path: PathLike,
    *,
    format: str = "markdown",
    pages: Optional[str] = None,
    password: Optional[str] = None,
    reading_order: str = "xycut",
    table_method: str = "default",
    image_output: str = "off"
) -> str:
    if password is not None:
        print("[WARN] Password decryption is not supported in the WebAssembly version.", file=sys.stderr)

    ctx.reset()

    p = Path(input_path)
    ext = p.suffix.lower()
    if ext in _IMAGE_EXTS:
        with open(input_path, "rb") as f:
            image_bytes = f.read()
        pdf_bytes = img2pdf.convert(image_bytes)
    else:
        with open(input_path, "rb") as f:
            pdf_bytes = f.read()

    pdf_ptr, pdf_len = pass_bytes_to_wasm(store, pdf_bytes)
    format_ptr, format_len = pass_string_to_wasm(store, format)
    pages_ptr, pages_len = pass_string_to_wasm(store, pages)

    wasm_reading_order = "auto" if reading_order == "xycut" else reading_order
    reading_ptr, reading_len = pass_string_to_wasm(store, wasm_reading_order)

    table_ptr, table_len = pass_string_to_wasm(store, table_method)

    retptr = exports["__wbindgen_add_to_stack_pointer"](store, -16)

    try:
        exports["convert_to_string"](
            store, retptr,
            pdf_ptr, pdf_len,
            format_ptr, format_len,
            pages_ptr, pages_len,
            reading_ptr, reading_len,
            table_ptr, table_len
        )

        memory = exports["memory"]
        result_bytes = memory.read(store, retptr, retptr + 16)
        r0, r1, r2, r3 = struct.unpack("<iiii", result_bytes)

        if r3 != 0:
            err = ctx.take_object(r2)
            raise err if isinstance(err, Exception) else Exception(str(err))

        result_str = memory.read(store, r0, r0 + r1).decode("utf-8")
        exports["__wbindgen_export3"](store, r0, r1, 1)

        if format == "json":
            result_str = _normalize_wasm_json(result_str)

        return result_str

    finally:
        exports["__wbindgen_add_to_stack_pointer"](store, 16)


_TYPE_MAP = {
    "Paragraph": "paragraph",
    "Heading": "heading",
    "Table": "table",
    "List": "list",
    "Image": "image",
    "Caption": "caption",
    "Header": "header",
    "Footer": "footer",
    "Figure": "figure",
    "Line": "line",
    "Span": "span",
    "Text": "text",
}


def _extract_text(obj, depth=0):
    if depth > 20:
        return ""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, list):
        return "".join(_extract_text(item, depth + 1) for item in obj)
    if isinstance(obj, dict):
        if "value" in obj:
            return str(obj.get("value", ""))
        for key in ("content", "text", "value", "label"):
            if key in obj and isinstance(obj[key], str):
                return obj[key]
        for key in ("text_chunks", "text_lines", "text_blocks", "columns",
                    "contents", "rows", "cells", "children", "items",
                    "base", "lines"):
            if key in obj:
                result = _extract_text(obj[key], depth + 1)
                if result:
                    return result
        for v in obj.values():
            if isinstance(v, (dict, list)):
                result = _extract_text(v, depth + 1)
                if result:
                    return result
    return ""


def _get_nested(obj, *keys, default=None):
    for key in keys:
        if isinstance(obj, dict) and key in obj:
            obj = obj[key]
        else:
            return default
    return obj


def _normalize_wasm_json(wasm_json_str: str) -> str:
    doc = json.loads(wasm_json_str)
    normalized_kids = []
    for kid in doc.get("kids", []):
        if not isinstance(kid, dict):
            normalized_kids.append(kid)
            continue
        keys = list(kid.keys())
        if len(keys) != 1:
            normalized_kids.append(kid)
            continue
        type_key = keys[0]
        inner = kid[type_key]
        base = inner if isinstance(inner, dict) else {}
        if "base" in base:
            base = base["base"]

        entry = {
            "type": _TYPE_MAP.get(type_key, type_key.lower()),
            "id": base.get("index", 0),
        }

        bbox = _get_nested(inner, "bbox") or _get_nested(base, "bbox")
        if isinstance(bbox, dict):
            entry["page number"] = bbox.get("page_number", 1)
            entry["bounding box"] = [
                bbox.get("left_x", 0),
                bbox.get("bottom_y", 0),
                bbox.get("right_x", 0),
                bbox.get("top_y", 0),
            ]
        elif isinstance(bbox, list):
            entry["page number"] = bbox[0] if len(bbox) > 0 else 1
            entry["bounding box"] = bbox[1:5] if len(bbox) >= 5 else bbox

        entry["font"] = base.get("font_name", "") or ""
        entry["font size"] = base.get("font_size", 0)

        tc = base.get("text_color")
        if isinstance(tc, (int, float)):
            entry["text color"] = f"[{tc}]"
        elif isinstance(tc, str):
            entry["text color"] = tc
        else:
            entry["text color"] = ""

        entry["content"] = _extract_text(inner)

        if type_key == "Heading" and "heading_level" in base:
            entry["heading level"] = base["heading_level"]

        normalized_kids.append(entry)

    doc["kids"] = normalized_kids
    return json.dumps(doc, ensure_ascii=False, indent=2)


def convert_file(
    input_path: PathLike,
    output_dir: PathLike = "output",
    *,
    format: str = "markdown",
    pages: Optional[str] = None,
    password: Optional[str] = None
) -> str:
    ext_map = {
        "markdown": ".md",
        "json": ".json",
        "html": ".html",
        "text": ".txt"
    }
    ext = ext_map.get(format, ".md")

    content = convert(
        input_path,
        format=format,
        pages=pages,
        password=password
    )

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    input_name = Path(input_path).stem
    out_file = out_path / f"{input_name}{ext}"

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(content)

    return str(out_file)


def version() -> str:
    ctx.reset()
    retptr = exports["__wbindgen_add_to_stack_pointer"](store, -16)
    try:
        exports["version"](store, retptr)
        memory = exports["memory"]
        result_bytes = memory.read(store, retptr, retptr + 16)
        r0, r1 = struct.unpack("<ii", result_bytes[:8])

        version_str = memory.read(store, r0, r0 + r1).decode("utf-8")
        exports["__wbindgen_export3"](store, r0, r1, 1)

        return version_str
    finally:
        exports["__wbindgen_add_to_stack_pointer"](store, 16)
