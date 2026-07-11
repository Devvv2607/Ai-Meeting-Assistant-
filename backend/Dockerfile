# Backend Dockerfile — FastAPI on Cloud Run
#
# Build (from the backend/ directory):
#   docker build -t ai-meeting-backend .
# Cloud Run injects $PORT (default 8080); the CMD binds to it.

FROM python:3.11-slim

WORKDIR /app

# System deps:
#   ffmpeg      — pydub/audio decoding fallback (imageio-ffmpeg is also bundled)
#   libsndfile1 — soundfile (WAV I/O for diarization)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    gcc \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install the CPU-only torch wheel first (the default PyPI wheel bundles CUDA
# and adds ~2GB); requirements.txt then sees torch as already satisfied.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Writable dirs for uploaded/recorded audio (ephemeral on Cloud Run — files
# live only for the instance's lifetime, which covers a live session).
RUN mkdir -p uploads/live_audio backend/uploads/live_audio

ENV PYTHONUNBUFFERED=1 \
    PORT=8080

EXPOSE 8080

# Shell form so ${PORT} expands (Cloud Run sets it; 8080 is the fallback).
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
