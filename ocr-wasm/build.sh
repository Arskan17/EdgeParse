#!/bin/sh
# Build the OCR engine to WASM and download its models into ../package/.
# Needs: rustup target add wasm32-wasip1. Build scripts need a host C linker;
# set CC / CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER if `cc` is missing.
set -eu
cd "$(dirname "$0")"
cargo build --release --target wasm32-wasip1
cp target/wasm32-wasip1/release/ocr_wasm.wasm ../package/ocr_wasm.wasm
mkdir -p ../package/models
for m in detection recognition; do
  f=../package/models/text-$m.onnx
  [ -f "$f" ] || curl -sSfL -o "$f" "https://ocrs-models.s3-accelerate.amazonaws.com/text-$m.onnx"
done
echo "Built ../package/ocr_wasm.wasm"
