"""
Custom wrapper that adds ASR (audio transcription) support to docling-serve.
Runs alongside docling-serve and proxies document requests to it,
while handling audio files directly using docling's AsrPipeline.
"""
import os
import json
import tempfile
import httpx
from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, File, Header
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

app = FastAPI(title="Docling + ASR Wrapper")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac'}
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov'}
DOCLING_INTERNAL = "http://localhost:5001"

# Lazy-loaded ASR converter
_asr_converter = None

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
    """
    Accepts file uploads. Routes audio files to ASR pipeline,
    everything else to the internal docling-serve.
    """
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" not in content_type:
        return JSONResponse({"error": "Expected multipart/form-data"}, status_code=400)

    # Parse the multipart form
    form = await request.form()
    files_field = form.get("files")

    if files_field is None:
        return JSONResponse({"error": "No 'files' field in form data"}, status_code=400)

    filename = files_field.filename or "unknown"
    file_bytes = await files_field.read()

    if is_audio_file(filename):
        # Handle audio with ASR pipeline
        return await handle_audio(file_bytes, filename)
    else:
        # Proxy to internal docling-serve
        return await proxy_to_docling(file_bytes, filename, request)


async def handle_audio(file_bytes: bytes, filename: str):
    """Process audio file using docling's ASR pipeline."""
    try:
        # Write to temp file (docling needs a file path)
        with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        converter = get_asr_converter()
        result = converter.convert(Path(tmp_path))

        # Export to markdown
        md_content = result.document.export_to_markdown()

        # Clean up
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
            "processing_time": 0,
            "timings": {},
        })
    except Exception as e:
        # Clean up on error
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
            "errors": [{"component_type": "asr", "module_name": "AsrPipeline", "error_message": str(e)}],
            "processing_time": 0,
            "timings": {},
        }, status_code=500)


async def proxy_to_docling(file_bytes: bytes, filename: str, request: Request):
    """Proxy non-audio files to the internal docling-serve instance."""
    try:
        auth_header = request.headers.get("authorization", "")
        async with httpx.AsyncClient(timeout=120.0) as client:
            files = {"files": (filename, file_bytes)}
            headers = {}
            if auth_header:
                headers["Authorization"] = auth_header

            resp = await client.post(
                f"{DOCLING_INTERNAL}/v1/convert/file",
                files=files,
                headers=headers,
            )
            return JSONResponse(
                content=resp.json(),
                status_code=resp.status_code,
            )
    except Exception as e:
        return JSONResponse({"error": f"Proxy to docling failed: {str(e)}"}, status_code=502)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="::", port=8080)
