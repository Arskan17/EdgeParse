import io
import json

import pytest
from PIL import Image, ImageDraw, ImageFont

import edgeparse_wasm_adapter as edgeparse
from edgeparse_wasm_adapter import _is_image, ocr

WORDS = ["Stellar", "Release", "Package"]


def _text_image(mode: str, fmt: str) -> bytes:
    bg = (255, 255, 255, 0) if mode == "RGBA" else "white"
    img = Image.new(mode, (900, 320), bg)
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=56)
    draw.text((40, 40), f"{WORDS[0]} {WORDS[1]}", fill="black", font=font)
    draw.text((40, 200), WORDS[2], fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def _minimal_pdf(text: str) -> bytes:
    stream = f"BT /F1 24 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(out)


@pytest.mark.parametrize(
    "mode,fmt,ext",
    [("RGBA", "PNG", ".png"), ("RGB", "JPEG", ".jpg"), ("RGB", "WEBP", ".webp")],
)
def test_image_ocr_markdown(tmp_path, mode, fmt, ext):
    path = tmp_path / f"img{ext}"
    path.write_bytes(_text_image(mode, fmt))
    md = edgeparse.convert(path, format="markdown")
    for word in WORDS:
        assert word.lower() in md.lower(), md


def test_image_detected_by_magic_bytes_without_extension(tmp_path):
    path = tmp_path / "noext"
    path.write_bytes(_text_image("RGB", "PNG"))
    assert "stellar" in edgeparse.convert(path, format="text").lower()


def test_image_json_schema(tmp_path):
    path = tmp_path / "img.png"
    path.write_bytes(_text_image("RGB", "PNG"))
    doc = json.loads(edgeparse.convert(path, format="json"))
    assert doc["kids"], doc
    # Large vertical gap between the two text rows → two paragraphs.
    assert len(doc["kids"]) == 2
    for kid in doc["kids"]:
        assert kid["type"] == "paragraph"
        assert kid["page number"] == 1
        l, b, r, t = kid["bounding box"]
        assert 0 <= l < r and 0 <= b < t <= 320


def test_image_html_escapes(tmp_path):
    result = {"width": 10, "height": 10, "lines": [{"text": "a<b", "bbox": [0, 0, 5, 5], "words": []}]}
    assert "a&lt;b" in ocr.render(result, "html")


def test_pdf_still_uses_edgeparse(tmp_path):
    path = tmp_path / "doc.pdf"
    path.write_bytes(_minimal_pdf("Hello EdgeParse"))
    assert "Hello EdgeParse" in edgeparse.convert(path, format="markdown")


def test_is_image():
    assert _is_image(b"\x89PNG\r\n\x1a\n....", "")
    assert _is_image(b"RIFF\x00\x00\x00\x00WEBPVP8 ", "")
    assert not _is_image(b"%PDF-1.7", ".png")
    assert not _is_image(b"%PDF-1.7", ".pdf")
