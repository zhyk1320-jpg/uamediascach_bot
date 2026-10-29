"""Завантаження медіа: yt-dlp + FFmpeg, плюс розпізнавання Spotify-треків."""
import asyncio
import base64
import html
import logging
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import aiohttp
import yt_dlp

import config

log = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class MediaError(Exception):
    """Помилка з людським поясненням — показується користувачу як є."""


# --------------------------------------------------------------------------- #
#  Визначення платформи
# --------------------------------------------------------------------------- #
PLATFORM_HOSTS = {
    "youtube": ("youtube.com", "youtu.be", "youtube-nocookie.com"),
    "tiktok": ("tiktok.com",),
    "soundcloud": ("soundcloud.com",),
    "spotify": ("spotify.com", "spotify.link"),
}


def detect_platform(url: str) -> str | None:
    host = (urlparse(url).hostname or "").lower()
    for name, domains in PLATFORM_HOSTS.items():
        if any(host == d or host.endswith("." + d) for d in domains):
            return name
    return None


# --------------------------------------------------------------------------- #
#  Прогрес (оновлюється з потоку yt-dlp, читається з асинхронного таска)
# --------------------------------------------------------------------------- #
class Progress:
    def __init__(self) -> None:
        self.stage = "prepare"  # prepare -> download -> convert
        self.streams = 1  # скільки потоків качаємо (відео+аудіо = 2)
        self.finished = 0
        self.frac = 0.0
        self._max = 0.0

    @property
    def percent(self) -> float:
        if self.stage == "prepare":
            return 0.0
        if self.stage == "convert":
            value = 95.0
        else:
            value = min((self.finished + self.frac) / self.streams, 1.0) * 90
        self._max = max(self._max, value)  # смужка ніколи не відкочується назад
        return self._max


@dataclass
class Result:
    path: Path
    title: str
    performer: str | None
    duration: int | None
    kind: str  # "audio" | "video"


# --------------------------------------------------------------------------- #
#  Spotify -> (назва, виконавець)
# --------------------------------------------------------------------------- #
def _meta(page: str, prop: str) -> str | None:
    for pattern in (
        rf'<meta[^>]+property="{prop}"[^>]+content="([^"]*)"',
        rf'<meta[^>]+content="([^"]*)"[^>]+property="{prop}"',
    ):
        m = re.search(pattern, page)
        if m:
            return html.unescape(m.group(1)).strip()
    return None


async def _spotify_api(session: aiohttp.ClientSession, track_id: str) -> tuple[str, str | None]:
    creds = f"{config.SPOTIFY_CLIENT_ID}:{config.SPOTIFY_CLIENT_SECRET}".encode()
    async with session.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "client_credentials"},
        headers={"Authorization": "Basic " + base64.b64encode(creds).decode()},
    ) as r:
        r.raise_for_status()
        token = (await r.json())["access_token"]
    async with session.get(
        f"https://api.spotify.com/v1/tracks/{track_id}",
        headers={"Authorization": f"Bearer {token}"},
    ) as r:
        r.raise_for_status()
        data = await r.json()
    artists = ", ".join(a["name"] for a in data.get("artists", [])[:2]) or None
    return data["name"], artists


async def _spotify_scrape(session: aiohttp.ClientSession, track_id: str) -> tuple[str, str | None]:
    async with session.get(f"https://open.spotify.com/track/{track_id}") as r:
        page = await r.text()
    title = _meta(page, "og:title")
    if not title:
        raise MediaError("🟢 Не вдалося прочитати цей трек зі Spotify. Спробуй інше посилання.")
    artist = None
    desc = _meta(page, "og:description")
    if desc:
        parts = [p.strip() for p in desc.split("·")]
        parts = [
            p
            for p in parts
            if p
            and p.lower() not in (title.lower(), "song")
            and not re.fullmatch(r"\d{4}", p)
            and not p.lower().startswith("listen to")
        ]
        artist = parts[0] if parts else None
    return title, artist


async def resolve_spotify(url: str) -> tuple[str, str | None]:
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout, headers={"User-Agent": UA}) as session:
        host = urlparse(url).hostname or ""
        if host.endswith("spotify.link"):  # коротке посилання -> повне
            try:
                async with session.get(url, allow_redirects=True) as r:
                    url = str(r.url)
            except aiohttp.ClientError:
                raise MediaError("🟢 Не вдалося відкрити коротке посилання Spotify.")
        m = re.search(r"/track/([A-Za-z0-9]+)", url)
        if not m:
            raise MediaError(
                "🟢 Поки що я працюю лише з посиланнями на окремі треки Spotify "
                "(не альбоми й не плейлисти)."
            )
        track_id = m.group(1)
        if config.SPOTIFY_CLIENT_ID and config.SPOTIFY_CLIENT_SECRET:
            try:
                return await _spotify_api(session, track_id)
            except Exception as exc:  # падаємо назад на парсинг сторінки
                log.warning("Spotify API не спрацювало: %s", exc)
        try:
            return await _spotify_scrape(session, track_id)
        except aiohttp.ClientError:
            raise MediaError("🟢 Spotify зараз не відповідає. Спробуй трохи пізніше.")


# --------------------------------------------------------------------------- #
#  yt-dlp
# --------------------------------------------------------------------------- #
def _prepare_cookies() -> str | None:
    src = Path(config.COOKIES_FILE)
    if src.is_file():
        dst = Path(tempfile.gettempdir()) / "yt_cookies.txt"
        shutil.copyfile(src, dst)  # копія, щоб yt-dlp міг її перезаписувати
        return str(dst)
    return None


_COOKIES = _prepare_cookies()


def _base_opts() -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 20,
        "retries": 3,
        "restrictfilenames": True,
        "concurrent_fragment_downloads": 4,
        "max_filesize": 250 * 1024 * 1024,
    }
    if _COOKIES:
        opts["cookiefile"] = _COOKIES
    if config.PROXY:
        opts["proxy"] = config.PROXY
    return opts


def _map_error(err: Exception) -> MediaError:
    log.warning("yt-dlp помилка: %s", err)
    msg = str(err).lower()
    if "sign in to confirm" in msg or "not a bot" in msg:
        return MediaError(
            "🤖 YouTube тимчасово блокує сервер бота. Спробуй пізніше "
            "(власник бота може додати cookies або проксі)."
        )
    if "private" in msg:
        return MediaError("🔒 Це приватне відео — до нього я не маю доступу.")
    if "age" in msg and "restrict" in msg:
        return MediaError("🔞 Це відео з віковим обмеженням, завантажити його не вдасться.")
    if "unavailable" in msg or "removed" in msg or "not available" in msg or "404" in msg:
        return MediaError("🫥 Це відео недоступне: його видалили або закрили в твоєму регіоні.")
    if "unsupported url" in msg:
        return MediaError("🤔 Не впізнав це посилання. Перевір, що воно веде на конкретне відео чи трек.")
    if "429" in msg or "too many requests" in msg:
        return MediaError("🚦 Забагато запитів до сервісу. Зачекай хвилинку й спробуй ще раз.")
    return MediaError("😕 Не вдалося завантажити. Перевір посилання або спробуй трохи пізніше.")


def _extract_info(target: str) -> dict:
    opts = _base_opts()
    opts["skip_download"] = True
    if target.startswith("ytsearch"):
        opts["extract_flat"] = True  # швидкий пошук без зайвих запитів
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(target, download=False)
    except yt_dlp.utils.DownloadError as err:
        raise _map_error(err)


def _download(url: str, platform: str, fmt: str, job_dir: Path, prog: Progress) -> Path:
    def hook(d: dict) -> None:
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            if total:
                prog.frac = min((d.get("downloaded_bytes") or 0) / total, 1.0)
        elif d["status"] == "finished":
            prog.finished += 1
            prog.frac = 0.0

    def pp_hook(d: dict) -> None:
        if d["status"] == "started":
            prog.stage = "convert"

    opts = _base_opts()
    opts.update(
        outtmpl=str(job_dir / "%(id)s.%(ext)s"),
        progress_hooks=[hook],
        postprocessor_hooks=[pp_hook],
    )

    if fmt == "mp3":
        prog.streams = 1
        opts.update(
            format="bestaudio/best",
            postprocessors=[
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"},
                {"key": "FFmpegMetadata"},
            ],
        )
    elif platform == "tiktok":
        # формат "download" у TikTok — це версія З водяним знаком, тому виключаємо її
        prog.streams = 1
        opts.update(
            format="best[format_id!=download][vcodec^=h264]/best[format_id!=download]/best",
            merge_output_format="mp4",
        )
    else:  # YouTube відео: до 720p, mp4 (H.264 + AAC) — відтворюється скрізь
        prog.streams = 2
        opts.update(
            format=(
                "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/"
                "bv*[height<=720]+ba/b[height<=720]/b"
            ),
            merge_output_format="mp4",
        )

    prog.stage = "download"
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as err:
        raise _map_error(err)

    wanted = ".mp3" if fmt == "mp3" else ".mp4"
    files = [p for p in job_dir.iterdir() if p.is_file() and p.suffix.lower() == wanted]
    if not files:
        files = [
            p
            for p in job_dir.iterdir()
            if p.is_file() and p.suffix.lower() in {".mp4", ".mkv", ".webm", ".m4a", ".mp3"}
        ]
    if not files:
        raise MediaError("😕 Файл не вдалося створити. Спробуй інше посилання.")
    return max(files, key=lambda p: p.stat().st_size)


# --------------------------------------------------------------------------- #
#  Головна функція
# --------------------------------------------------------------------------- #
async def fetch_and_download(
    url: str, platform: str, fmt: str, job_dir: Path, prog: Progress
) -> Result:
    kind = "audio" if fmt == "mp3" else "video"
    max_sec = config.MAX_AUDIO_SEC if kind == "audio" else config.MAX_VIDEO_SEC

    meta_title = meta_artist = None
    target = url
    is_search = False
    if platform == "spotify":
        meta_title, meta_artist = await resolve_spotify(url)
        query = f"{meta_artist} - {meta_title}" if meta_artist else meta_title
        target = f"ytsearch3:{query}"
        is_search = True

    info = await asyncio.to_thread(_extract_info, target)

    if is_search:
        entries = [e for e in (info.get("entries") or []) if e]
        if not entries:
            raise MediaError("🔍 Не вдалося знайти цей трек на YouTube. Спробуй інший.")
        info = next(
            (e for e in entries if e.get("duration") and e["duration"] <= max_sec), entries[0]
        )
        download_url = info.get("url") or info.get("webpage_url") or ""
        if not download_url.startswith("http"):
            download_url = f"https://www.youtube.com/watch?v={info.get('id')}"
    else:
        if info.get("_type") == "playlist" or info.get("entries"):
            raise MediaError("📃 Плейлисти й альбоми поки не підтримуються — надішли посилання на одне відео чи трек.")
        download_url = info.get("webpage_url") or url

    if info.get("is_live"):
        raise MediaError("🔴 Це пряма трансляція — завантажити її неможливо.")
    duration = info.get("duration")
    if duration and duration > max_sec:
        raise MediaError(
            f"⏱ Це занадто довго: максимум {max_sec // 60} хв для "
            f"{'аудіо' if kind == 'audio' else 'відео'} (інакше файл не влізе в ліміт Telegram)."
        )

    path = await asyncio.to_thread(_download, download_url, platform, fmt, job_dir, prog)

    if path.stat().st_size > config.MAX_FILE_BYTES:
        raise MediaError(
            "📦 Файл завеликий для Telegram (ліміт ботів — 50 МБ). "
            "Спробуй коротше відео або обери MP3 🎵"
        )

    return Result(
        path=path,
        title=meta_title or info.get("track") or info.get("title") or "Без назви",
        performer=meta_artist or info.get("artist") or info.get("uploader") or info.get("channel"),
        duration=int(duration) if duration else None,
        kind=kind,
    )
