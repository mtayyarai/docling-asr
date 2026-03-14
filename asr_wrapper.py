"""
Single-process Docling API with ASR support.
Uses docling Python library directly for all file types.
"""
import os
import json
import time
import tempfile
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

app = FastAPI(title="Docling + ASR API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac'}
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov'}

# Lazy-loaded converters
_doc_converter = None
_asr_converter = None


def get_doc_converter():
    global _doc_converter
    if _doc_converter is None:
        from docling.document_converter import DocumentConverter, PdfFormatOption, ImageFormatOption
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions

        # Use EasyOCR for better English/Arabic text extraction (RapidOCR uses Chinese models)
        ocr_options = EasyOcrOptions(lang=["en", "ar"])
        pipeline_options = PdfPipelineOptions()
        pipeline_options.ocr_options = ocr_options
        pipeline_options.do_ocr = True

        _doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
                InputFormat.IMAGE: ImageFormatOption(pipeline_options=pipeline_options),
            }
        )
    return _doc_converter


def get_asr_converter():
    global _asr_converter
    if _asr_converter is None:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel import asr_model_specs
        from docling.datamodel.pipeline_options import AsrPipelineOptions
        from docling.document_converter import AudioFormatOption, DocumentConverter
        from docling.pipeline.asr_pipeline import AsrPipeline

        pipeline_options = AsrPipelineOptions()
        pipeline_options.asr_options = asr_model_specs.WHISPER_TINY

        _asr_converter = DocumentConverter(
            format_options={
                InputFormat.AUDIO: AudioFormatOption(
                    pipeline_cls=AsrPipeline,
                    pipeline_options=pipeline_options,
                )
            }
        )
    return _asr_converter


def is_audio_file(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in AUDIO_EXTENSIONS or ext in VIDEO_EXTENSIONS


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/v1/convert/file")
async def convert_file(request: Request):
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" not in content_type:
        return JSONResponse({"error": "Expected multipart/form-data"}, status_code=400)

    form = await request.form()
    files_field = form.get("files")
    if files_field is None:
        return JSONResponse({"error": "No 'files' field in form data"}, status_code=400)

    filename = files_field.filename or "unknown"
    file_bytes = await files_field.read()

    tmp_path = None
    try:
        start = time.time()

        # Write to temp file
        suffix = Path(filename).suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        # Choose converter based on file type
        if is_audio_file(filename):
            converter = get_asr_converter()
        else:
            converter = get_doc_converter()

        result = converter.convert(Path(tmp_path))
        md_content = result.document.export_to_markdown()
        elapsed = time.time() - start

        os.unlink(tmp_path)

        return JSONResponse({
            "document": {
                "filename": filename,
                "md_content": md_content,
                "json_content": None,
                "html_content": None,
                "text_content": None,
                "doctags_content": None,
            },
            "status": "success",
            "errors": [],
            "processing_time": elapsed,
            "timings": {},
        })

    except Exception as e:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except:
                pass
        return JSONResponse({
            "document": {
                "filename": filename,
                "md_content": None,
            },
            "status": "failure",
            "errors": [{"component_type": "converter", "module_name": "", "error_message": str(e)}],
            "processing_time": 0,
            "timings": {},
        }, status_code=500)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "5001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
