FROM quay.io/docling-project/docling-serve-cpu:latest

USER root

# Install ffmpeg via static binary (package managers not available in this image)
RUN curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -o /tmp/ffmpeg.tar.xz && \
    tar xf /tmp/ffmpeg.tar.xz -C /tmp && \
    cp /tmp/ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ffmpeg && \
    cp /tmp/ffmpeg-*-amd64-static/ffprobe /usr/local/bin/ffprobe && \
    chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe && \
    rm -rf /tmp/ffmpeg* && \
    ffmpeg -version | head -1

# Install ASR + EasyOCR dependencies
RUN pip install --no-cache-dir "docling[asr]" easyocr

# Copy the API
COPY asr_wrapper.py /app/asr_wrapper.py

USER default

EXPOSE 5001

CMD ["python", "/app/asr_wrapper.py"]
