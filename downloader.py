"""Завантаження медіа: yt-dlp + FFmpeg, пошук, Spotify-метадані, обрізка та GIF."""
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
from yt_dlp.utils import download_range_func

import config

log = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class MediaError(Exception):
    """
    Помилка зі зрозумілим поясненням. code — ключ тексту "e_<code>" у texts.py,
    params — підстановки в цей текст. Мову обирає той, хто показує помилку.
    """

    def __init__(self, code: str, **params):
        super().__init__(code)
        self.code = code
        self.params = params


# --------------------------------------------------------------------------- #
#  Платформи
# --------------------------------------------------------------------------- #
PLATFORM_HOSTS = {
    "youtube": ("youtube.com", "youtu.be", "youtube-nocookie.com"),
    "tiktok": ("tiktok.com",),
    "soundcloud": ("soundcloud.com",),
    "spotify": ("spotify.com", "spotify.link"),
    "instagram": ("instagram.com", "instagr.am"),
    "twitter": ("twitter.com", "x.com"),
    "pinterest": ("pinterest.com", "pin.it"),
    "facebook": ("facebook.com", "fb.watch", "fb.com"),
}


def detect_platform(url: str) -> str | None:
    host = (urlparse(url).hostname or "").lower()
    for name, domains in PLATFORM_HOSTS.items():
        if any(host == d or host.endswith("." + d) for d in domains):
            return name
    return None


# --------------------------------------------------------------------------- #
#  Параметри завдання
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Options:
    fmt: str = "mp4"  # mp3 | mp4 | gif
    height: int = 720  # 360 / 720 / 1080
    trim: tuple[float, float] | None = None  # (початок, кінець) у секундах


@dataclass
class Prepared:
    url: str  # що саме качаємо
    key: str | None  # ключ кешу file_id (None — не кешуємо)
    title: str
    performer: str | None
    duration: int | None
    kind: str  # audio | video | gif
    trim: tuple[float, float] | None
    height: int


@dataclass
class SearchItem:
    url: str
    title: str
    duration: int | None
    uploader: str | None


class Progress:
    """Оновлюється з потоку yt-dlp, читається асинхронним таском, що малює статус-бар."""

    def __init__(self) -> None:
        self.stage = "prepare"  # prepare | queue | download | convert | send | cached
        self.streams = 1
        self.finished = 0
        self.frac = 0.0
        self._max = 0.0

    @property
    def percent(self) -> float:
        if self.stage in ("prepare", "queue", "cached"):
            return 0.0
        if self.stage == "send":
            return 100.0
        if self.stage == "convert":
            value = 95.0
        else:
            value = min((self.finished + self.frac) / self.streams, 1.0) * 90
        self._max = max(self._max, value)  # смужка ніколи не відкочується назад
        return self._max


# --------------------------------------------------------------------------- #
#  Spotify
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


async def _spotify_token(session: aiohttp.ClientSession) -> str:
    creds = f"{config.SPOTIFY_CLIENT_ID}:{config.SPOTIFY_CLIENT_SECRET}".encode()
    async with session.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "client_credentials"},
        headers={"Authorization": "Basic " + base64.b64encode(creds).decode()},
    ) as r:
        r.raise_for_status()
        return (await r.json())["access_token"]


async def _spotify_api_track(session: aiohttp.ClientSession, track_id: str) -> tuple[str, str | None]:
    token = await _spotify_token(session)
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
        raise MediaError("spotify_read")
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


def _new_session() -> aiohttp.ClientSession:
    return aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=15), headers={"User-Agent": UA}
    )


async def spotify_expand(url: str) -> str:
    """Розгортає короткі посилання spotify.link у повні."""
    if (urlparse(url).hostname or "").endswith("spotify.link"):
        async with _new_session() as session:
            try:
                async with session.get(url, allow_redirects=True) as r:
                    return str(r.url)
            except aiohttp.ClientError:
                raise MediaError("spotify_open")
    return url


async def resolve_spotify(url: str) -> tuple[str, str | None]:
    """Посилання на трек Spotify -> (назва, виконавець)."""
    url = await spotify_expand(url)
    m = re.search(r"/track/([A-Za-z0-9]+)", url)
    if not m:
        raise MediaError("spotify_type")
    track_id = m.group(1)
    async with _new_session() as session:
        if config.SPOTIFY_CLIENT_ID and config.SPOTIFY_CLIENT_SECRET:
            try:
                return await _spotify_api_track(session, track_id)
            except Exception as exc:  # падаємо назад на парсинг сторінки
                log.warning("Spotify API не спрацювало: %s", exc)
        try:
            return await _spotify_scrape(session, track_id)
        except aiohttp.ClientError:
            raise MediaError("spotify_down")


async def spotify_collection(url: str) -> list[tuple[str, str | None]]:
    """Альбом або плейлист Spotify -> список (назва, виконавець). Потрібен офіційний API."""
    if not (config.SPOTIFY_CLIENT_ID and config.SPOTIFY_CLIENT_SECRET):
        raise MediaError("spotify_keys")
    m = re.search(r"/(album|playlist)/([A-Za-z0-9]+)", url)
    if not m:
        raise MediaError("spotify_type")
    kind, cid = m.groups()
    async with _new_session() as session:
        try:
            token = await _spotify_token(session)
            headers = {"Authorization": f"Bearer {token}"}
            if kind == "album":
                api = f"https://api.spotify.com/v1/albums/{cid}/tracks"
                params = {"limit": config.MAX_COLLECTION}
            else:
                api = f"https://api.spotify.com/v1/playlists/{cid}/tracks"
                params = {"limit": config.MAX_COLLECTION, "fields": "items(track(name,artists(name)))"}
            async with session.get(api, headers=headers, params=params) as r:
                r.raise_for_status()
                data = await r.json()
        except (aiohttp.ClientError, KeyError) as exc:
            log.warning("Spotify колекція: %s", exc)
            raise MediaError("spotify_read")
    out: list[tuple[str, str | None]] = []
    for item in data.get("items", []):
        track = item.get("track") if kind == "playlist" else item
        if not track or not track.get("name"):
            continue
        artists = ", ".join(a["name"] for a in track.get("artists", [])[:2]) or None
        out.append((track["name"], artists))
    if not out:
        raise MediaError("spotify_read")
    return out[: config.MAX_COLLECTION]


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
        "max_filesize": 2000 * 1024 * 1024 if config.LOCAL_API_URL else 250 * 1024 * 1024,
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
        return MediaError("block")
    if "private" in msg:
        return MediaError("private")
    if "age" in msg and "restrict" in msg:
        return MediaError("age")
    if "unavailable" in msg or "removed" in msg or "not available" in msg or "404" in msg:
        return MediaError("unavailable")
    if "unsupported url" in msg:
        return MediaError("unsupported")
    if "429" in msg or "too many requests" in msg:
        return MediaError("rate")
    return MediaError("generic")


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


def _search_sync(query: str, n: int) -> list[SearchItem]:
    try:
        info = _extract_info(f"ytsearch{n + 3}:{query}")
    except MediaError:
        raise MediaError("search")
    items: list[SearchItem] = []
    for e in info.get("entries") or []:
        if not e or not e.get("id"):
            continue
        d = e.get("duration")
        if d and d > config.MAX_AUDIO_SEC:
            continue
        items.append(
            SearchItem(
                url=f"https://www.youtube.com/watch?v={e['id']}",
                title=e.get("title") or "—",
                duration=int(d) if d else None,
                uploader=e.get("uploader") or e.get("channel"),
            )
        )
    return items[:n]


async def search(query: str, n: int = 5) -> list[SearchItem]:
    return await asyncio.to_thread(_search_sync, query, n)


# --------------------------------------------------------------------------- #
#  Підготовка (метадані, перевірки, ключ кешу)
# --------------------------------------------------------------------------- #
async def prepare(
    url: str,
    platform: str,
    opts: Options,
    spotify_meta: tuple[str, str | None] | None = None,
) -> Prepared:
    kind = {"mp3": "audio", "gif": "gif"}.get(opts.fmt, "video")
    max_sec = config.MAX_AUDIO_SEC if kind == "audio" else config.MAX_VIDEO_SEC
    height = 0 if platform == "tiktok" or kind != "video" else opts.height

    meta_title = meta_artist = None
    target = url
    is_search = False
    if platform == "spotify":
        meta_title, meta_artist = spotify_meta or await resolve_spotify(url)
        query = f"{meta_artist} - {meta_title}" if meta_artist else meta_title
        target = f"ytsearch3:{query}"
        is_search = True

    info = await asyncio.to_thread(_extract_info, target)

    if is_search:
        entries = [e for e in (info.get("entries") or []) if e and e.get("id")]
        if not entries:
            raise MediaError("notfound")
        info = next(
            (e for e in entries if e.get("duration") and e["duration"] <= max_sec), entries[0]
        )
        download_url = f"https://www.youtube.com/watch?v={info['id']}"
        source = "yt"
    else:
        if info.get("_type") == "playlist" or info.get("entries"):
            raise MediaError("playlist")
        download_url = info.get("webpage_url") or url
        ie = (info.get("extractor_key") or "").lower()
        source = "yt" if ie.startswith("youtube") else ie

    if info.get("is_live"):
        raise MediaError("live")

    dur = info.get("duration")
    trim = opts.trim
    if kind == "gif" and not trim:
        trim = (0.0, float(min(dur or 10, 10)))
    out_dur: int | None
    if trim:
        start, end = trim
        if dur and start >= dur:
            raise MediaError("cut_range")
        if dur and end > dur:
            end = float(dur)
        limit = config.MAX_GIF_SEC if kind == "gif" else config.MAX_TRIM_SEC
        if end - start > limit:
            raise MediaError("cut_long", seconds=limit)
        trim = (start, end)
        out_dur = int(end - start)
    else:
        if dur and dur > max_sec:
            raise MediaError("long", minutes=max_sec // 60)
        out_dur = int(dur) if dur else None

    key = None
    vid = info.get("id")
    if not trim and kind != "gif" and vid and source:
        key = f"{source}:{vid}:" + ("mp3" if kind == "audio" else f"v{height}")

    return Prepared(
        url=download_url,
        key=key,
        title=meta_title or info.get("track") or info.get("title") or "—",
        performer=meta_artist or info.get("artist") or info.get("uploader") or info.get("channel"),
        duration=out_dur,
        kind=kind,
        trim=trim,
        height=height,
    )


# --------------------------------------------------------------------------- #
#  Завантаження
# --------------------------------------------------------------------------- #
def _video_format(platform: str, height: int) -> tuple[str, int]:
    """Повертає (селектор формату yt-dlp, кількість потоків для прогрес-бара)."""
    if platform == "tiktok":
        # формат "download" у TikTok — це версія З водяним знаком, тому виключаємо її
        return "best[format_id!=download][vcodec^=h264]/best[format_id!=download]/best", 1
    if platform == "youtube":
        h = height or 720
        return (
            f"bv*[height<={h}][ext=mp4]+ba[ext=m4a]/b[height<={h}][ext=mp4]/"
            f"bv*[height<={h}]+ba/b[height<={h}]/b",
            2,
        )
    h = height or 720
    return f"bv*[height<={h}]+ba/b[height<={h}]/b", 2


def _download_sync(prep: Prepared, platform: str, job_dir: Path, prog: Progress) -> Path:
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

    if prep.kind == "audio":
        prog.streams = 1
        opts.update(
            format="bestaudio/best",
            postprocessors=[
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"},
                {"key": "FFmpegMetadata"},
            ],
        )
    elif prep.kind == "gif":
        prog.streams = 1
        opts.update(format="bv*[height<=480]/b[height<=480]/b")  # звук для GIF не потрібен
    else:
        fmt, streams = _video_format(platform, prep.height)
        prog.streams = streams
        opts.update(format=fmt, merge_output_format="mp4")

    if prep.trim:  # качаємо лише потрібний фрагмент
        opts["download_ranges"] = download_range_func(None, [prep.trim])
        opts["force_keyframes_at_cuts"] = True

    prog.stage = "download"
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([prep.url])
    except yt_dlp.utils.DownloadError as err:
        raise _map_error(err)

    wanted = ".mp3" if prep.kind == "audio" else ".mp4"
    files = [p for p in job_dir.iterdir() if p.is_file() and p.suffix.lower() == wanted]
    if not files:
        files = [
            p
            for p in job_dir.iterdir()
            if p.is_file() and p.suffix.lower() in {".mp4", ".mkv", ".webm", ".m4a", ".mp3"}
        ]
    if not files:
        raise MediaError("nofile")
    return max(files, key=lambda p: p.stat().st_size)


async def _make_gif(src: Path, job_dir: Path) -> Path:
    """Telegram показує беззвучне коротке mp4 як GIF-анімацію — це легше й якісніше за справжній GIF."""
    out = job_dir / "anim.mp4"
    cmd = [
        "ffmpeg", "-y", "-i", str(src), "-t", str(config.MAX_GIF_SEC), "-an",
        "-vf", "scale='min(480,iw)':-2,fps=15",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
    )
    code = await proc.wait()
    if code != 0 or not out.exists():
        raise MediaError("nofile")
    src.unlink(missing_ok=True)
    return out


async def download(
    prep: Prepared, platform: str, job_dir: Path, prog: Progress
) -> Path:
    path = await asyncio.to_thread(_download_sync, prep, platform, job_dir, prog)
    if prep.kind == "gif":
        prog.stage = "convert"
        path = await _make_gif(path, job_dir)
    if path.stat().st_size > config.MAX_FILE_BYTES:
        raise MediaError("toobig")
    return path
