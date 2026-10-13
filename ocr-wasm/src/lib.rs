//! OCR engine for EdgeParse, compiled to `wasm32-wasip1`.
//!
//! Exposes a plain C ABI (no wasm-bindgen) so any WASM host can drive it:
//!
//! * `alloc(len) -> ptr` / `dealloc(ptr, len)` — host-side buffers.
//! * `ocr_init(det_ptr, det_len, rec_ptr, rec_len) -> i32` — load the
//!   detection and recognition models (ONNX or `.rten`). 0 on success.
//! * `ocr_image(ptr, len) -> ptr` — OCR an encoded image (PNG, JPEG, WebP,
//!   BMP, TIFF, GIF). Returns a length-prefixed UTF-8 JSON string, or 0 on
//!   error (see `last_error`).
//! * `last_error() -> ptr` — length-prefixed UTF-8 error message.
//! * `free_result(ptr)` — release a string returned by the above.
//!
//! Length-prefixed strings are a little-endian `u32` byte length followed by
//! the bytes.

use std::cell::RefCell;

use ocrs::{ImageSource, OcrEngine, OcrEngineParams, TextItem};
use rten::Model;
use serde::Serialize;

thread_local! {
    static ENGINE: RefCell<Option<OcrEngine>> = const { RefCell::new(None) };
    static LAST_ERROR: RefCell<String> = const { RefCell::new(String::new()) };
}

#[derive(Serialize)]
pub struct Word {
    pub text: String,
    /// `[left, top, right, bottom]` in image pixels, origin top-left.
    pub bbox: [i32; 4],
}

#[derive(Serialize)]
pub struct Line {
    pub text: String,
    pub bbox: [i32; 4],
    pub words: Vec<Word>,
}

#[derive(Serialize)]
pub struct OcrResult {
    pub width: u32,
    pub height: u32,
    pub lines: Vec<Line>,
}

fn rect_to_bbox(r: rten_imageproc::Rect) -> [i32; 4] {
    [r.left(), r.top(), r.right(), r.bottom()]
}

/// Load models and build an engine.
pub fn build_engine(detection: Vec<u8>, recognition: Vec<u8>) -> anyhow::Result<OcrEngine> {
    OcrEngine::new(OcrEngineParams {
        detection_model: Some(Model::load(detection)?),
        recognition_model: Some(Model::load(recognition)?),
        ..Default::default()
    })
}

/// Decode an encoded image and run the full OCR pipeline.
pub fn run_ocr(engine: &OcrEngine, image_bytes: &[u8]) -> anyhow::Result<OcrResult> {
    // Decoding to RGB8 flattens alpha, palettes and greyscale uniformly.
    let img = image::load_from_memory(image_bytes)?.into_rgb8();
    let (width, height) = img.dimensions();

    let source = ImageSource::from_bytes(img.as_raw(), (width, height))?;
    let input = engine.prepare_input(source)?;
    let word_rects = engine.detect_words(&input)?;
    let line_rects = engine.find_text_lines(&input, &word_rects);
    let texts = engine.recognize_text(&input, &line_rects)?;

    let lines = texts
        .iter()
        .flatten()
        .filter(|l| !l.to_string().trim().is_empty())
        .map(|l| Line {
            text: l.to_string(),
            bbox: rect_to_bbox(l.bounding_rect()),
            words: l
                .words()
                .map(|w| Word {
                    text: w.to_string(),
                    bbox: rect_to_bbox(w.bounding_rect()),
                })
                .collect(),
        })
        .collect();

    Ok(OcrResult { width, height, lines })
}

// ---------------------------------------------------------------------------
// C ABI
// ---------------------------------------------------------------------------

fn set_error(msg: impl ToString) {
    LAST_ERROR.with(|e| *e.borrow_mut() = msg.to_string());
}

fn into_prefixed(s: &str) -> *mut u8 {
    let mut buf = Vec::with_capacity(4 + s.len());
    buf.extend_from_slice(&(s.len() as u32).to_le_bytes());
    buf.extend_from_slice(s.as_bytes());
    Box::into_raw(buf.into_boxed_slice()) as *mut u8
}

/// # Safety
/// Host must read `len` bytes from a pointer it obtained from `alloc`.
unsafe fn take_bytes(ptr: *mut u8, len: usize) -> Vec<u8> {
    unsafe { Vec::from_raw_parts(ptr, len, len) }
}

#[unsafe(no_mangle)]
pub extern "C" fn alloc(len: usize) -> *mut u8 {
    let mut buf = Vec::<u8>::with_capacity(len);
    let ptr = buf.as_mut_ptr();
    std::mem::forget(buf);
    ptr
}

/// # Safety
/// `ptr`/`len` must come from `alloc` and not have been passed elsewhere.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn dealloc(ptr: *mut u8, len: usize) {
    drop(unsafe { Vec::from_raw_parts(ptr, 0, len) });
}

/// # Safety
/// `ptr` must come from `ocr_image` or `last_error`.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn free_result(ptr: *mut u8) {
    if ptr.is_null() {
        return;
    }
    let len = u32::from_le_bytes(unsafe { *(ptr as *const [u8; 4]) }) as usize;
    drop(unsafe { Box::from_raw(std::ptr::slice_from_raw_parts_mut(ptr, 4 + len)) });
}

/// Takes ownership of both buffers.
///
/// # Safety
/// Buffers must come from `alloc` with the given lengths, fully written.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn ocr_init(det_ptr: *mut u8, det_len: usize, rec_ptr: *mut u8, rec_len: usize) -> i32 {
    let det = unsafe { take_bytes(det_ptr, det_len) };
    let rec = unsafe { take_bytes(rec_ptr, rec_len) };
    match build_engine(det, rec) {
        Ok(engine) => {
            ENGINE.with(|e| *e.borrow_mut() = Some(engine));
            0
        }
        Err(err) => {
            set_error(format!("failed to load models: {err:#}"));
            1
        }
    }
}

/// Takes ownership of the image buffer.
///
/// # Safety
/// Buffer must come from `alloc` with the given length, fully written.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn ocr_image(ptr: *mut u8, len: usize) -> *mut u8 {
    let bytes = unsafe { take_bytes(ptr, len) };
    let result = ENGINE.with(|e| {
        let engine = e.borrow();
        let engine = engine
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("ocr_init has not been called"))?;
        let res = run_ocr(engine, &bytes)?;
        Ok::<_, anyhow::Error>(serde_json::to_string(&res)?)
    });
    match result {
        Ok(json) => into_prefixed(&json),
        Err(err) => {
            set_error(format!("{err:#}"));
            std::ptr::null_mut()
        }
    }
}

#[unsafe(no_mangle)]
pub extern "C" fn last_error() -> *mut u8 {
    LAST_ERROR.with(|e| into_prefixed(&e.borrow()))
}
