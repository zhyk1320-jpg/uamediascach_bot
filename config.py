"""
Налаштування бота.

Усі секрети й параметри беруться зі ЗМІННИХ СЕРЕДОВИЩА (Environment Variables).
На хостингу (Render, Koyeb тощо) ти додаєш їх у розділі "Environment".

Обов'язкова:
    BOT_TOKEN          — токен від @BotFather (виглядає як 123456789:AAH...)

Необов'язкові:
    SUPPORT_CONTACT    — твій @username для підтримки (показується у /paysupport)
    ADMIN_IDS          — твій Telegram ID (або кілька через кому) для /stats, /broadcast, /promo_on
    PRICE_DAY / PRICE_WEEK / PRICE_MONTH / PRICE_QUARTER — ціни у зірках (35 / 90 / 170 / 420)
    PROMO_PRICE        — ціна акційного дня для нових користувачів (за замовчуванням 1 ⭐)
    PROMO_DAYS         — тривалість акції у днях при /promo_on (за замовчуванням 7)
    LOCAL_API_URL      — адреса власного Bot API сервера (для файлів до 2 ГБ), напр. http://host:8081
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
import re
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
PRICE_WEEK = _int("PRICE_WEEK", 90)  # ⭐ за 7 днів
PRICE_MONTH = _int("PRICE_MONTH", 170)  # ⭐ за 30 днів безліміту
PRICE_QUARTER = _int("PRICE_QUARTER", 420)  # ⭐ за 90 днів
PROMO_PRICE = _int("PROMO_PRICE", 1)  # ⭐ акційний день для нових користувачів
PROMO_DAYS = _int("PROMO_DAYS", 7)  # скільки днів триває акція після /promo_on
DONATE_MIN = 1
DONATE_MAX = 5000

# --- Бонуси та рефералка ------------------------------------------------------
REF_BONUS = 2  # +скачування кожному, коли друг запустив бота за посиланням
SHARE_BONUS = 1  # +скачування за "поділитись ботом" (1 раз на добу)
BONUS_CAP = 50  # максимум бонусних завантажень на балансі
MAX_REFERRALS = 100  # максимум нагороджених запрошень на одного користувача

ADMIN_IDS = {int(x) for x in re.split(r"[,\s]+", os.getenv("ADMIN_IDS", "")) if x.strip().isdigit()}
TZ_NAME = os.getenv("TZ_NAME", "Europe/Kyiv")

# --- Файли та БД --------------------------------------------------------------
DB_PATH = os.getenv("DB_PATH", "data/bot.db")
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "downloads"))

# --- Обмеження завантажень ----------------------------------------------------
MAX_PARALLEL = _int("MAX_PARALLEL", 2)
# Якщо задано LOCAL_API_URL (свій Bot API сервер) — файли до ~2 ГБ, інакше ліміт Telegram — 50 МБ
LOCAL_API_URL = os.getenv("LOCAL_API_URL") or None
MAX_FILE_BYTES = 1900 * 1024 * 1024 if LOCAL_API_URL else 49 * 1024 * 1024
MAX_TRIM_SEC = 180  # максимальна довжина вирізаного фрагмента
MAX_GIF_SEC = 15
MAX_COLLECTION = 10  # скільки треків з альбому/плейлиста Spotify за раз
MAX_AUDIO_SEC = 30 * 60  # MP3 192 kbps за 30 хв ≈ 43 МБ
MAX_VIDEO_SEC = 15 * 60

# --- yt-dlp / Spotify ---------------------------------------------------------
COOKIES_FILE = os.getenv("COOKIES_FILE", "cookies.txt")
PROXY = os.getenv("PROXY") or None
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()
