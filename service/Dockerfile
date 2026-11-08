# Build from the repository root:  docker build -f service/Dockerfile -t cmd-parser:1.0 .
# CPU-only PyTorch wheels (no GPU libraries) keep the image well under 2 GB. No model weights are copied in:
# the service downloads them from object storage at start-up.
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 TOKENIZERS_PARALLELISM=false
WORKDIR /app
COPY service/requirements.txt service/requirements.txt
RUN pip install -r service/requirements.txt
COPY common/ common/
COPY service/ service/
RUN useradd -u 10001 -m app && chown -R app /app
USER app
EXPOSE 8000
CMD ["uvicorn", "service.app:app", "--host", "0.0.0.0", "--port", "8000"]
