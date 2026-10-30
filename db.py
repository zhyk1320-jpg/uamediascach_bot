"""Робота з базою даних (SQLite через aiosqlite)."""
import datetime as dt
import os
import uuid
from dataclasses import dataclass
from zoneinfo import ZoneInfo

import aiosqlite

import config

TZ = ZoneInfo(config.TZ_NAME)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY,
    free_used     INTEGER NOT NULL DEFAULT 0,
    last_reset    TEXT    NOT NULL,
    premium_until TEXT,
    created_at    TEXT    NOT NULL
);
CREATE TABLE IF NOT EXISTS payments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    charge_id  TEXT UNIQUE NOT NULL,
    user_id    INTEGER NOT NULL,
    plan       TEXT NOT NULL,
    stars      INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cache (
    key        TEXT PRIMARY KEY,
    file_id    TEXT NOT NULL,
    kind       TEXT NOT NULL,
    title      TEXT,
    performer  TEXT,
    duration   INTEGER,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS downloads (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    platform   TEXT NOT NULL,
    fmt        TEXT NOT NULL,
    cached     INTEGER NOT NULL DEFAULT 0,
    day        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""

# Колонки, яких не було у першій версії бота — додаються автоматично (міграція)
USER_COLUMNS = {
    "bonus": "INTEGER NOT NULL DEFAULT 0",
    "lang": "TEXT",
    "referred_by": "INTEGER",
    "ref_count": "INTEGER NOT NULL DEFAULT 0",
    "promo_used": "INTEGER NOT NULL DEFAULT 0",
    "last_share": "TEXT",
    "last_seen": "TEXT",
    "promo_campaign": "TEXT",  # id останньої акції, якою скористався користувач
    "tg_lang": "TEXT",  # мова Telegram користувача (для локалізованих анонсів)
    "source": "TEXT",  # звідки прийшов користувач (тег із посилання ?start=src_ТЕГ)
}


# Адміни мають вічний безліміт. /asuser тимчасово вимикає його (до перезапуску) — щоб протестувати
# бота "очима звичайного користувача".
LIFETIME_OFF: set[int] = set()


def is_lifetime(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS and user_id not in LIFETIME_OFF


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _today() -> str:
    return dt.datetime.now(TZ).date().isoformat()


def time_to_reset() -> dt.timedelta:
    """Скільки лишилось до найближчої півночі (за TZ_NAME)."""
    now = dt.datetime.now(TZ)
    nxt = (now + dt.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return nxt - now


def fmt_dt(value: dt.datetime) -> str:
    return value.astimezone(TZ).strftime("%d.%m.%Y %H:%M")


@dataclass
class Access:
    user_id: int
    free_used: int
    bonus: int
    premium_until: dt.datetime | None
    lang: str | None
    created_at: dt.datetime
    ref_count: int
    last_share: str | None
    promo_campaign: str | None
    tg_lang: str | None

    @property
    def is_lifetime(self) -> bool:
        return is_lifetime(self.user_id)

    @property
    def is_premium(self) -> bool:
        return self.is_lifetime or bool(self.premium_until and self.premium_until > _now_utc())

    @property
    def daily_left(self) -> int:
        return max(config.FREE_LIMIT - self.free_used, 0)

    @property
    def free_left(self) -> int:
        return self.daily_left + self.bonus

    @property
    def allowed(self) -> bool:
        return self.is_premium or self.free_left > 0

    @property
    def can_share(self) -> bool:
        return self.last_share != _today()


@dataclass
class CacheEntry:
    file_id: str
    kind: str
    title: str | None
    performer: str | None
    duration: int | None


# --------------------------------------------------------------------------- #
#  Ініціалізація
# --------------------------------------------------------------------------- #
async def init_db() -> None:
    folder = os.path.dirname(config.DB_PATH)
    if folder:
        os.makedirs(folder, exist_ok=True)
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.executescript(SCHEMA)
        cur = await db.execute("PRAGMA table_info(users)")
        existing = {row[1] for row in await cur.fetchall()}
        for name, ddl in USER_COLUMNS.items():
            if name not in existing:
                await db.execute(f"ALTER TABLE users ADD COLUMN {name} {ddl}")
        await db.commit()


async def _ensure_user(db: aiosqlite.Connection, user_id: int) -> bool:
    """Створює користувача (якщо нема), скидає добовий ліміт. True — якщо щойно створений."""
    today = _today()
    cur = await db.execute(
        "INSERT OR IGNORE INTO users (user_id, free_used, last_reset, created_at, last_seen) "
        "VALUES (?, 0, ?, ?, ?)",
        (user_id, today, _now_utc().isoformat(), today),
    )
    created = cur.rowcount == 1
    await db.execute(
        "UPDATE users SET free_used = 0, last_reset = ? WHERE user_id = ? AND last_reset != ?",
        (today, user_id, today),
    )
    await db.execute(
        "UPDATE users SET last_seen = ? WHERE user_id = ? AND (last_seen IS NULL OR last_seen != ?)",
        (today, user_id, today),
    )
    return created


# --------------------------------------------------------------------------- #
#  Користувачі й ліміти
# --------------------------------------------------------------------------- #
async def get_access(user_id: int) -> Access:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await _ensure_user(db, user_id)
        await db.commit()
        cur = await db.execute(
            "SELECT free_used, bonus, premium_until, lang, created_at, ref_count, last_share, "
            "promo_campaign, tg_lang "
            "FROM users WHERE user_id = ?",
            (user_id,),
        )
        (free_used, bonus, pu, lang, created, ref_count, last_share,
         promo_campaign, tg_lang) = await cur.fetchone()
    return Access(
        user_id=user_id,
        free_used=free_used,
        bonus=bonus,
        premium_until=dt.datetime.fromisoformat(pu) if pu else None,
        lang=lang,
        created_at=dt.datetime.fromisoformat(created),
        ref_count=ref_count,
        last_share=last_share,
        promo_campaign=promo_campaign,
        tg_lang=tg_lang,
    )


async def set_lang(user_id: int, lang: str) -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await _ensure_user(db, user_id)
        await db.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
        await db.commit()


async def set_tg_lang(user_id: int, code: str) -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("UPDATE users SET tg_lang = ? WHERE user_id = ?", (code, user_id))
        await db.commit()


async def register_download(
    user_id: int, platform: str, fmt: str, cached: bool = False
) -> Access:
    """
    Викликається ПІСЛЯ успішної відправки файлу.
    Спочатку витрачається добовий ліміт, потім бонусні скачування. Преміум нічого не витрачає.
    """
    async with aiosqlite.connect(config.DB_PATH) as db:
        await _ensure_user(db, user_id)
        cur = await db.execute("SELECT premium_until FROM users WHERE user_id = ?", (user_id,))
        (pu,) = await cur.fetchone()
        premium = is_lifetime(user_id) or bool(pu and dt.datetime.fromisoformat(pu) > _now_utc())
        if not premium:
            cur = await db.execute(
                "UPDATE users SET free_used = free_used + 1 WHERE user_id = ? AND free_used < ?",
                (user_id, config.FREE_LIMIT),
            )
            if cur.rowcount == 0:
                await db.execute(
                    "UPDATE users SET bonus = bonus - 1 WHERE user_id = ? AND bonus > 0", (user_id,)
                )
        await db.execute(
            "INSERT INTO downloads (user_id, platform, fmt, cached, day) VALUES (?, ?, ?, ?, ?)",
            (user_id, platform, fmt, 1 if cached else 0, _today()),
        )
        await db.commit()
    return await get_access(user_id)


# --------------------------------------------------------------------------- #
#  Рефералка та "поділитись"
# --------------------------------------------------------------------------- #
async def register_start(
    user_id: int, ref_id: int | None, source: str | None = None
) -> tuple[bool, bool]:
    """
    Викликається на /start. Повертає (новий_користувач, реферальний_бонус_нараховано).
    Бонус отримують обоє, але лише якщо користувач прийшов ВПЕРШЕ і реферер існує.
    """
    applied = False
    async with aiosqlite.connect(config.DB_PATH) as db:
        created = await _ensure_user(db, user_id)
        if created and source:  # джерело фіксуємо лише при першому запуску
            await db.execute("UPDATE users SET source = ? WHERE user_id = ?", (source, user_id))
        if created and ref_id and ref_id != user_id:
            cur = await db.execute("SELECT ref_count FROM users WHERE user_id = ?", (ref_id,))
            row = await cur.fetchone()
            if row and row[0] < config.MAX_REFERRALS:
                await db.execute(
                    "UPDATE users SET referred_by = ?, bonus = MIN(bonus + ?, ?) WHERE user_id = ?",
                    (ref_id, config.REF_BONUS, config.BONUS_CAP, user_id),
                )
                await db.execute(
                    "UPDATE users SET ref_count = ref_count + 1, bonus = MIN(bonus + ?, ?) "
                    "WHERE user_id = ?",
                    (config.REF_BONUS, config.BONUS_CAP, ref_id),
                )
                applied = True
        await db.commit()
    return created, applied


async def grant_share_bonus(user_id: int) -> bool:
    """+бонус за реальну відправку повідомлення-запрошення. Не частіше ніж раз на добу."""
    today = _today()
    async with aiosqlite.connect(config.DB_PATH) as db:
        await _ensure_user(db, user_id)
        cur = await db.execute(
            "UPDATE users SET bonus = MIN(bonus + ?, ?), last_share = ? "
            "WHERE user_id = ? AND (last_share IS NULL OR last_share != ?)",
            (config.SHARE_BONUS, config.BONUS_CAP, today, user_id, today),
        )
        await db.commit()
        return cur.rowcount == 1


# --------------------------------------------------------------------------- #
#  Платежі
# --------------------------------------------------------------------------- #
async def add_payment(
    user_id: int, plan: str, days: int, stars: int, charge_id: str, campaign: str | None = None
) -> tuple[bool, dt.datetime | None]:
    """
    Записує платіж. Якщо days > 0 — нараховує/продовжує преміум.
    Повертає (це_новий_платіж, нова_дата_завершення_преміуму).
    Повторна обробка того самого платежу ігнорується.
    """
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute(
            "INSERT OR IGNORE INTO payments (charge_id, user_id, plan, stars, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (charge_id, user_id, plan, stars, _now_utc().isoformat()),
        )
        if cur.rowcount == 0:
            await db.commit()
            return False, None
        await _ensure_user(db, user_id)
        new_until = None
        if days > 0:
            cur = await db.execute("SELECT premium_until FROM users WHERE user_id = ?", (user_id,))
            (current,) = await cur.fetchone()
            now = _now_utc()
            base = now
            if current:
                existing = dt.datetime.fromisoformat(current)
                if existing > now:
                    base = existing
            new_until = base + dt.timedelta(days=days)
            await db.execute(
                "UPDATE users SET premium_until = ? WHERE user_id = ?",
                (new_until.isoformat(), user_id),
            )
        if plan == "promo" and campaign:
            await db.execute(
                "UPDATE users SET promo_campaign = ? WHERE user_id = ?", (campaign, user_id)
            )
        await db.commit()
    return True, new_until


# --------------------------------------------------------------------------- #
#  Кеш file_id
# --------------------------------------------------------------------------- #
async def get_cache(key: str) -> CacheEntry | None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute(
            "SELECT file_id, kind, title, performer, duration FROM cache WHERE key = ?", (key,)
        )
        row = await cur.fetchone()
    return CacheEntry(*row) if row else None


async def put_cache(
    key: str, file_id: str, kind: str, title: str | None, performer: str | None, duration: int | None
) -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO cache (key, file_id, kind, title, performer, duration, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (key, file_id, kind, title, performer, duration, _now_utc().isoformat()),
        )
        await db.commit()


async def delete_cache(key: str) -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("DELETE FROM cache WHERE key = ?", (key,))
        await db.commit()


# --------------------------------------------------------------------------- #
#  Акції (налаштовувані: тривалість підписки, ціна, аудиторія, строк дії)
# --------------------------------------------------------------------------- #
AUDIENCES = ("new", "all", "free")  # нові | усі | усі без активного преміуму


async def _get_setting(db: aiosqlite.Connection, key: str) -> str | None:
    cur = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = await cur.fetchone()
    return row[0] if row else None


@dataclass
class Promo:
    id: str
    start: dt.datetime
    until: dt.datetime
    days: int  # на скільки днів безліміту
    price: int  # ціна у зірках
    audience: str  # new | all | free


async def promo_window() -> Promo | None:
    """Поточна акція, якщо вона триває."""
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute("SELECT key, value FROM settings WHERE key LIKE 'promo%'")
        data = dict(await cur.fetchall())
    try:
        promo = Promo(
            id=data["promo_id"],
            start=dt.datetime.fromisoformat(data["promo_start"]),
            until=dt.datetime.fromisoformat(data["promo_until"]),
            days=int(data["promo_days"]),
            price=int(data["promo_price"]),
            audience=data.get("promo_aud", "new"),
        )
    except (KeyError, ValueError):
        return None
    return promo if promo.start <= _now_utc() < promo.until else None


def _eligible(
    promo: Promo, created_at: dt.datetime, premium_until: dt.datetime | None, campaign: str | None
) -> bool:
    if campaign == promo.id:  # цією акцією вже користувались
        return False
    if promo.audience == "new" and created_at < promo.start:
        return False
    if promo.audience == "free" and premium_until and premium_until > _now_utc():
        return False
    return True


async def promo_offer(access: Access) -> Promo | None:
    """Акція, доступна САМЕ цьому користувачеві (або None)."""
    promo = await promo_window()
    if promo and _eligible(promo, access.created_at, access.premium_until, access.promo_campaign):
        return promo
    return None


async def start_promo(days: int, price: int, audience: str, hours: int) -> Promo:
    now = _now_utc()
    promo = Promo(
        id=uuid.uuid4().hex[:8],
        start=now,
        until=now + dt.timedelta(hours=hours),
        days=days,
        price=price,
        audience=audience,
    )
    values = {
        "promo_id": promo.id,
        "promo_start": promo.start.isoformat(),
        "promo_until": promo.until.isoformat(),
        "promo_days": str(days),
        "promo_price": str(price),
        "promo_aud": audience,
    }
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("DELETE FROM settings WHERE key LIKE 'promo%'")
        for key, value in values.items():
            await db.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (key, value))
        await db.commit()
    return promo


async def stop_promo() -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("DELETE FROM settings WHERE key LIKE 'promo%'")
        await db.commit()


async def promo_is_announced(promo_id: str) -> bool:
    async with aiosqlite.connect(config.DB_PATH) as db:
        return await _get_setting(db, "promo_announced") == promo_id


async def mark_promo_announced(promo_id: str) -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('promo_announced', ?)", (promo_id,)
        )
        await db.commit()


async def promo_recipients(promo: Promo) -> list[tuple[int, str | None, str | None]]:
    """Кому надсилати анонс: (user_id, збережена мова, мова Telegram) — лише ті, хто має право на акцію."""
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute(
            "SELECT user_id, created_at, premium_until, promo_campaign, lang, tg_lang FROM users"
        )
        rows = await cur.fetchall()
    out = []
    for uid, created, pu, campaign, lang, tg in rows:
        premium_until = dt.datetime.fromisoformat(pu) if pu else None
        if _eligible(promo, dt.datetime.fromisoformat(created), premium_until, campaign):
            out.append((uid, lang, tg))
    return out


async def promo_sales(promo: Promo) -> tuple[int, int]:
    """(кількість покупок, зірок) за акційним тарифом відколи стартувала акція."""
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*), COALESCE(SUM(stars), 0) FROM payments WHERE plan = 'promo' AND created_at >= ?",
            (promo.start.isoformat(),),
        )
        return await cur.fetchone()


# --------------------------------------------------------------------------- #
#  Статистика та розсилка (для адміна)
# --------------------------------------------------------------------------- #
async def all_recipients() -> list[tuple[int, str | None, str | None]]:
    """Усі користувачі для розсилки: (user_id, збережена мова, мова Telegram)."""
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute("SELECT user_id, lang, tg_lang FROM users")
        return [tuple(row) for row in await cur.fetchall()]


async def get_sources() -> list[tuple[str, int, int]]:
    """Топ джерел: (тег, користувачів, з них платних). Без тегу — '—' (органіка/невідомо)."""
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute(
            "SELECT COALESCE(u.source, '—') AS src, COUNT(DISTINCT u.user_id), COUNT(DISTINCT p.user_id) "
            "FROM users u LEFT JOIN payments p ON p.user_id = u.user_id AND p.plan != 'donate' "
            "GROUP BY src ORDER BY 2 DESC LIMIT 10"
        )
        return [tuple(row) for row in await cur.fetchall()]


async def get_growth(days: int = 7) -> list[tuple[str, int]]:
    """Нові користувачі по днях (дата за UTC): [(дата, кількість)], найновіші першими."""
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute(
            "SELECT substr(created_at, 1, 10) AS d, COUNT(*) FROM users GROUP BY d ORDER BY d DESC LIMIT ?",
            (days,),
        )
        return [tuple(row) for row in await cur.fetchall()]


async def all_user_ids() -> list[int]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users")
        return [row[0] for row in await cur.fetchall()]


async def get_stats() -> dict:
    today = _today()
    now = _now_utc().isoformat()
    async with aiosqlite.connect(config.DB_PATH) as db:

        async def one(sql: str, params: tuple = ()) -> int:
            cur = await db.execute(sql, params)
            (value,) = await cur.fetchone()
            return value or 0

        return {
            "users": await one("SELECT COUNT(*) FROM users"),
            "new_today": await one("SELECT COUNT(*) FROM users WHERE created_at >= ?", (today,)),
            "active_today": await one("SELECT COUNT(*) FROM users WHERE last_seen = ?", (today,)),
            "premium_now": await one("SELECT COUNT(*) FROM users WHERE premium_until > ?", (now,)),
            "referrals": await one("SELECT COALESCE(SUM(ref_count), 0) FROM users"),
            "payments": await one("SELECT COUNT(*) FROM payments"),
            "stars_total": await one("SELECT COALESCE(SUM(stars), 0) FROM payments"),
            "stars_donate": await one(
                "SELECT COALESCE(SUM(stars), 0) FROM payments WHERE plan = 'donate'"
            ),
            "promo_sales": await one("SELECT COUNT(*) FROM payments WHERE plan = 'promo'"),
            "promo_stars": await one("SELECT COALESCE(SUM(stars), 0) FROM payments WHERE plan = 'promo'"),
            "dl_today": await one("SELECT COUNT(*) FROM downloads WHERE day = ?", (today,)),
            "dl_total": await one("SELECT COUNT(*) FROM downloads"),
            "dl_cached": await one("SELECT COUNT(*) FROM downloads WHERE cached = 1"),
            "cache_items": await one("SELECT COUNT(*) FROM cache"),
        }
