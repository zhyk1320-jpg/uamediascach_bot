"""Робота з базою даних (SQLite через aiosqlite)."""
import datetime as dt
import os
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
"""


@dataclass
class Access:
    user_id: int
    free_used: int
    premium_until: dt.datetime | None

    @property
    def is_premium(self) -> bool:
        return bool(self.premium_until and self.premium_until > _now_utc())

    @property
    def free_left(self) -> int:
        return max(config.FREE_LIMIT - self.free_used, 0)

    @property
    def allowed(self) -> bool:
        return self.is_premium or self.free_left > 0


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


async def init_db() -> None:
    folder = os.path.dirname(config.DB_PATH)
    if folder:
        os.makedirs(folder, exist_ok=True)
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def _ensure_user(db: aiosqlite.Connection, user_id: int) -> None:
    today = _today()
    await db.execute(
        "INSERT OR IGNORE INTO users (user_id, free_used, last_reset, created_at) VALUES (?, 0, ?, ?)",
        (user_id, today, _now_utc().isoformat()),
    )
    # новий день -> скидаємо лічильник безплатних завантажень
    await db.execute(
        "UPDATE users SET free_used = 0, last_reset = ? WHERE user_id = ? AND last_reset != ?",
        (today, user_id, today),
    )


async def get_access(user_id: int) -> Access:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await _ensure_user(db, user_id)
        await db.commit()
        cur = await db.execute(
            "SELECT free_used, premium_until FROM users WHERE user_id = ?", (user_id,)
        )
        free_used, premium_until = await cur.fetchone()
    until = dt.datetime.fromisoformat(premium_until) if premium_until else None
    return Access(user_id, free_used, until)


async def register_download(user_id: int) -> Access:
    """Викликається ПІСЛЯ успішної відправки файлу. Преміум не витрачає ліміт."""
    access = await get_access(user_id)
    if access.is_premium:
        return access
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "UPDATE users SET free_used = free_used + 1 WHERE user_id = ?", (user_id,)
        )
        await db.commit()
    return await get_access(user_id)


async def add_premium(
    user_id: int, plan: str, days: int, stars: int, charge_id: str
) -> dt.datetime | None:
    """
    Нараховує преміум після оплати. Якщо преміум ще діє — продовжує його.
    Повертає нову дату завершення або None, якщо цей платіж уже був оброблений.
    """
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute(
            "INSERT OR IGNORE INTO payments (charge_id, user_id, plan, stars, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (charge_id, user_id, plan, stars, _now_utc().isoformat()),
        )
        if cur.rowcount == 0:  # дубль платежу
            await db.commit()
            return None
        await _ensure_user(db, user_id)
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
        await db.commit()
    return new_until
