FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# FFmpeg потрібен для конвертації в MP3 та склеювання відео з аудіо
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Deno — JavaScript-рушій, який сучасний yt-dlp використовує для YouTube
COPY --from=denoland/deno:bin /deno /usr/local/bin/deno

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN mkdir -p /app/data /app/downloads

# BOT_TOKEN передається змінною середовища (на хостингу або через docker run -e)
CMD ["python", "main.py"]
