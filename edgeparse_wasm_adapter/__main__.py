import argparse
import glob
import sys
# from pathlib import Path

from . import convert_file


def main():
    parser = argparse.ArgumentParser(
        prog="python -m edgeparse_wasm_adapter",
        description="Extract structured data from PDFs and images via the edgeparse WASM engine",
    )
    parser.add_argument("input", nargs="+", help="Input file(s) — PDF, PNG, JPG — or glob pattern")
    parser.add_argument("-f", "--format", choices=["markdown", "json", "html", "text"], default="markdown")
    parser.add_argument("-o", "--output-dir", default="output")
    parser.add_argument("-p", "--pages", default=None, help="Page range e.g. 1,3,5-7")
    parser.add_argument("-t", "--table-method", choices=["default", "cluster"], default="default")
    parser.add_argument("-r", "--reading-order", choices=["xycut", "off"], default="xycut")
    args = parser.parse_args()

    files = []
    for pat in args.input:
        files.extend(glob.glob(pat))
    if not files:
        print("No files matched", file=sys.stderr)
        sys.exit(1)

    for f in files:
        out = convert_file(
            f,
            output_dir=args.output_dir,
            format=args.format,
            pages=args.pages,
        )
        print(out)


if __name__ == "__main__":
    main()
