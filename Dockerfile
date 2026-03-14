FROM quay.io/docling-project/docling-serve-cpu:latest

USER root

# Base image is UBI/RHEL-based, use dnf/microdnf
RUN microdnf install -y ffmpeg-free curl && microdnf clean all || \
    dnf install -y ffmpeg-free curl && dnf clean all || \
    yum install -y ffmpeg curl && yum clean all || \
    echo "Warning: Could not install ffmpeg via package manager"

# Install ASR dependencies (Whisper for audio transcription) and httpx for proxy
RUN pip install --no-cache-dir "docling[asr]" httpx

# Copy wrapper files
COPY asr_wrapper.py /app/asr_wrapper.py
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

USER default

EXPOSE 8080

CMD ["/app/start.sh"]
