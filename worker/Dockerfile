# Build from the repository root:  docker build -f worker/Dockerfile -t labeler-worker:1.0 .
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN pip install boto3==1.35.68 requests==2.32.3
COPY common/ common/
COPY worker/ worker/
COPY prompts/ prompts/
RUN useradd -u 10001 -m app && chown -R app /app
USER app
CMD ["python", "-m", "worker.worker"]
