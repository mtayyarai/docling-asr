#!/bin/bash
# Start docling-serve on port 5002 (internal only, not exposed)
docling-serve run --host "::" --port 5002 &

# Wait for docling-serve to be ready
echo "Waiting for docling-serve on port 5002..."
for i in $(seq 1 60); do
    if python -c "import urllib.request; urllib.request.urlopen('http://localhost:5002/health')" 2>/dev/null; then
        echo "docling-serve is ready on port 5002"
        break
    fi
    sleep 1
done

# Start ASR wrapper on port 5001 (exposed — same port Caddy proxies to)
echo "Starting ASR wrapper on port 5001..."
exec python /app/asr_wrapper.py
