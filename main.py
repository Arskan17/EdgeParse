import edgeparse_wasm_adapter as edgeparse
import json
import os

# --- PDF → JSON ---
doc = json.loads(edgeparse.convert("input_files/Gelbdruck_page6.pdf", format="json", table_method="cluster"))
os.makedirs("output_files", exist_ok=True)
with open("output_files/GD_p2.json", "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)

# --- Image → PDF (auto via img2pdf) → Markdown ---
for img in ["input_files/testimage.jpg"]:
    if os.path.exists(img):
        result = edgeparse.convert(img, format="markdown")
        name = os.path.splitext(os.path.basename(img))[0]
        with open(f"output_files/{name}.md", "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Extracted {img} -> output_files/{name}.md")

# --- PDF → Markdown (preview) ---
md = edgeparse.convert("input_files/Gelbdruck_page6.pdf", format="markdown")
print(md[:500])
