FROM quay.io/docling-project/docling-serve-cpu:latest

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl && rm -rf /var/lib/apt/lists/*

# Install ASR + wrapper dependencies
RUN pip install --no-cache-dir "docling[asr]" httpx

# Copy wrapper files
COPY asr_wrapper.py /app/asr_wrapper.py
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

USER default

EXPOSE 8080

CMD ["/app/start.sh"]
