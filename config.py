"""
Налаштування бота.

Усі секрети й параметри беруться зі ЗМІННИХ СЕРЕДОВИЩА (Environment Variables).
На хостингу (Render, Koyeb тощо) ти додаєш їх у розділі "Environment".

Обов'язкова:
    BOT_TOKEN          — токен від @BotFather (виглядає як 123456789:AAH...)

Необов'язкові:
    SUPPORT_CONTACT    — твій @username для підтримки (показується у /paysupport)
    PRICE_DAY          — ціна дня безліміту у зірках (за замовчуванням 35)
    PRICE_MONTH        — ціна місяця безліміту у зірках (за замовчуванням 170)
    TZ_NAME            — часовий пояс для "півночі" (за замовчуванням Europe/Kyiv)
    DB_PATH            — шлях до файлу бази (за замовчуванням data/bot.db)
    MAX_PARALLEL       — скільки завантажень одночасно (за замовчуванням 2)
    PROXY              — проксі для yt-dlp, напр. http://user:pass@host:port
    COOKIES_FILE       — шлях до cookies.txt (допомагає, коли YouTube блокує сервер)
    SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET — за бажанням, для офіційного Spotify API
    PORT               — хостинг зазвичай задає сам; бот піднімає крихітний
                         "health-сервер", щоб безкоштовні плани не вимикали його
"""
import os
from pathlib import Path

try:  # локально можна покласти файл .env поруч із main.py
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@your_username")

# --- Ліміти та ціни -----------------------------------------------------------
FREE_LIMIT = 3  # безплатних завантажень на добу
PRICE_DAY = _int("PRICE_DAY", 35)  # ⭐ за день безліміту
PRICE_MONTH = _int("PRICE_MONTH", 170)  # ⭐ за 30 днів безліміту
TZ_NAME = os.getenv("TZ_NAME", "Europe/Kyiv")

# --- Файли та БД --------------------------------------------------------------
DB_PATH = os.getenv("DB_PATH", "data/bot.db")
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "downloads"))

# --- Обмеження завантажень ----------------------------------------------------
MAX_PARALLEL = _int("MAX_PARALLEL", 2)
MAX_FILE_BYTES = 49 * 1024 * 1024  # ліміт Telegram Bot API на відправку — 50 МБ
MAX_AUDIO_SEC = 30 * 60  # MP3 192 kbps за 30 хв ≈ 43 МБ
MAX_VIDEO_SEC = 15 * 60

# --- yt-dlp / Spotify ---------------------------------------------------------
COOKIES_FILE = os.getenv("COOKIES_FILE", "cookies.txt")
PROXY = os.getenv("PROXY") or None
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()
