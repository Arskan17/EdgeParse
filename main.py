import edgeparse_wasm_adapter as edgeparse
import json
import os


INPUT_PDF = "input_files/xyz.pdf"
INPUT_IMG = "input_files/abc.png"
OUTPUT_DIR = "output_files"

# --- PDF → JSON ---
doc = json.loads(edgeparse.convert(INPUT_PDF, format="json", table_method="cluster"))
os.makedirs(OUTPUT_DIR, exist_ok=True)
with open(f"{OUTPUT_DIR}/xyz.json", "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)

# --- Image → OCR (WASM) → Markdown ---
for img in [INPUT_IMG]:
    if os.path.exists(img):
        result = edgeparse.convert(img, format="markdown")
        name = os.path.splitext(os.path.basename(img))[0]
        with open(f"{OUTPUT_DIR}/{name}.md", "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Extracted {img} -> {OUTPUT_DIR}/{name}.md")

# --- PDF → Markdown (preview) ---
md = edgeparse.convert(INPUT_PDF, format="markdown")
print(md[:500])
