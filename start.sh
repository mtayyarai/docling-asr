#!/bin/bash
# Start docling-serve on port 5001 (internal)
docling-serve run --host "::" --port 5001 &

# Wait for docling-serve to be ready
echo "Waiting for docling-serve to start..."
for i in $(seq 1 60); do
    if curl -s http://localhost:5001/health > /dev/null 2>&1; then
        echo "docling-serve is ready"
        break
    fi
    sleep 1
done

# Start ASR wrapper on port 8080 (exposed)
echo "Starting ASR wrapper on port 8080..."
exec python /app/asr_wrapper.py
