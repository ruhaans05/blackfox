# resume-agent — production image (bundles the Tectonic LaTeX engine)
FROM python:3.12-slim

# System deps Tectonic needs at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

# Install Tectonic (self-contained binary) into the image
RUN curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net | sh \
    && mv tectonic /usr/local/bin/tectonic \
    && tectonic --version

WORKDIR /app

# Install Python deps first for better layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Install the app
COPY . .
RUN pip install --no-cache-dir .

# Persistent data lives here (Render mounts a disk at /data). HOME is set so
# Tectonic's package cache also lands on the persistent disk.
ENV RESUME_AGENT_ENV=production \
    RESUME_AGENT_HOME=/data \
    HOME=/data \
    PORT=8000
RUN mkdir -p /data

EXPOSE 8000

# One worker (keeps the in-process build threads alive), several threads for
# concurrent requests. Binds to Render's injected $PORT.
CMD ["sh", "-c", "gunicorn --workers 1 --threads 8 --timeout 120 --bind 0.0.0.0:${PORT:-8000} 'resume_agent.webapp:create_app()'"]
