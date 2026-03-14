FROM quay.io/docling-project/docling-serve-cpu:latest

USER root

# Install system dependencies for audio
RUN microdnf install -y ffmpeg-free && microdnf clean all || \
    dnf install -y ffmpeg-free && dnf clean all || \
    echo "Warning: Could not install ffmpeg"

# Install ASR dependencies
RUN pip install --no-cache-dir "docling[asr]"

# Copy the single-process API
COPY asr_wrapper.py /app/asr_wrapper.py

USER default

EXPOSE 5001

CMD ["python", "/app/asr_wrapper.py"]
