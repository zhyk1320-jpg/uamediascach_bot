"""
🇺🇦 Медіаконвертер-бот (aiogram 3.x)

Платформи: YouTube, TikTok, SoundCloud, Spotify, Instagram, X/Twitter, Pinterest, Facebook.
Монетизація: безплатний ліміт + бонуси (рефералка, "поділитись") + Telegram Stars (XTR).
Запуск:  python main.py   (потрібна змінна середовища BOT_TOKEN — див. config.py)

НАЛАШТУВАННЯ В BOTFATHER (одноразово, для кнопки "Поділитись ботом"):
  /setinline → обрати бота → ввести будь-який підказковий текст (вмикає inline-режим)
  /setinlinefeedback → обрати бота → Enabled (100%)
Без цього бонус за "поділитись" не нараховуватиметься.

ПРО ОПЛАТУ ЗІРКАМИ: для XTR не потрібні платіжні токени, provider_token порожній.
"""
import asyncio
import contextlib
import html
import logging
import os
import re
import shutil
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ChatAction, ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    ChosenInlineResult,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    User,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

import config
import db
import downloader
from downloader import MediaError, Options, Progress
from texts import LANGS, pick_lang, tr

log = logging.getLogger("bot")
router = Router()
router.message.filter(F.chat.type == "private")

BOT_USERNAME = ""

# --------------------------------------------------------------------------- #
#  Тарифи
# --------------------------------------------------------------------------- #
PLANS = {
    "day": {"stars": config.PRICE_DAY, "days": 1},
    "week": {"stars": config.PRICE_WEEK, "days": 7},
    "month": {"stars": config.PRICE_MONTH, "days": 30},
    "quarter": {"stars": config.PRICE_QUARTER, "days": 90},
    "promo": {"stars": config.PROMO_PRICE, "days": 1},  # лише для нових користувачів під час акції
}
REGULAR_PLANS = ("day", "week", "month", "quarter")
DONATE_PRESETS = (25, 50, 100, 250)

# --------------------------------------------------------------------------- #
#  Стан у пам'яті
# --------------------------------------------------------------------------- #
PENDING: "OrderedDict[str, tuple[int, object]]" = OrderedDict()  # токен -> (user_id, дані)
AWAIT: dict[int, tuple[str, float, dict]] = {}  # очікуємо від користувача: суму донату або тайм-коди
ACTIVE: set[int] = set()  # користувачі, у яких зараз іде завантаження
LAST_SEARCH: dict[int, float] = {}
BROADCAST: dict[int, str] = {}
SEM = asyncio.Semaphore(config.MAX_PARALLEL)
URL_RE = re.compile(r"https?://\S+")
AWAIT_TTL = 300  # секунд


@dataclass
class Job:
    url: str
    platform: str
    opts: Options
    spotify_meta: tuple[str, str | None] | None = None


def remember(user_id: int, payload: object) -> str:
    token = uuid.uuid4().hex[:10]
    PENDING[token] = (user_id, payload)
    while len(PENDING) > 500:
        PENDING.popitem(last=False)
    return token


# --------------------------------------------------------------------------- #
#  Допоміжне
# --------------------------------------------------------------------------- #
def esc(value: str) -> str:
    return html.escape(value or "")


def ref_link(user_id: int) -> str:
    return f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"


def fmt_td(lang: str, seconds: float) -> str:
    hours, rest = divmod(int(seconds), 3600)
    return tr(lang, "hm", h=hours, m=rest // 60)


def err_text(lang: str, exc: MediaError) -> str:
    return tr(lang, "e_" + exc.code, **exc.params)


async def get_ctx(user: User) -> tuple[db.Access, str]:
    access = await db.get_access(user.id)
    return access, pick_lang(access.lang, user.language_code)


async def show(msg: Message, text: str, kb: InlineKeyboardMarkup | None = None) -> None:
    """Редагує повідомлення; якщо не вийшло — надсилає нове."""
    try:
        await msg.edit_text(text, reply_markup=kb)
    except TelegramBadRequest as exc:
        if "not modified" in str(exc):
            return
        await msg.answer(text, reply_markup=kb)


async def edit_or_send(
    bot: Bot, chat_id: int, status: Message | None, text: str, kb: InlineKeyboardMarkup | None = None
) -> Message:
    if status:
        try:
            await status.edit_text(text, reply_markup=kb)
            return status
        except TelegramBadRequest as exc:
            if "not modified" in str(exc):
                return status
    return await bot.send_message(chat_id, text, reply_markup=kb)


# --------------------------------------------------------------------------- #
#  Клавіатури
# --------------------------------------------------------------------------- #
def main_menu(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=tr(lang, "b_download"), callback_data="menu:download")
    kb.button(text=tr(lang, "b_premium"), callback_data="menu:premium")
    kb.button(text=tr(lang, "b_profile"), callback_data="menu:profile")
    kb.button(text=tr(lang, "b_help"), callback_data="menu:help")
    kb.button(text=tr(lang, "b_invite"), callback_data="menu:invite")
    kb.button(text=tr(lang, "b_lang"), callback_data="menu:lang")
    kb.adjust(2, 2, 2)
    return kb.as_markup()


def back_kb(lang: str, target: str = "menu:main") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=tr(lang, "b_back"), callback_data=target)
    return kb.as_markup()


def _plan_buttons(kb: InlineKeyboardBuilder, lang: str, promo_until) -> None:
    if promo_until:
        kb.button(text=tr(lang, "b_promo", price=config.PROMO_PRICE), callback_data="buy:promo")
    for pid in REGULAR_PLANS:
        kb.button(
            text=f"{tr(lang, 'plan_' + pid)} — {PLANS[pid]['stars']} ⭐", callback_data=f"buy:{pid}"
        )


def premium_kb(lang: str, promo_until=None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    _plan_buttons(kb, lang, promo_until)
    kb.button(text=tr(lang, "b_donate"), callback_data="menu:donate")
    kb.button(text=tr(lang, "b_back"), callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()


def paywall_kb(lang: str, access: db.Access, promo_until=None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    _plan_buttons(kb, lang, promo_until)
    if access.can_share:
        kb.button(text=tr(lang, "b_share", n=config.SHARE_BONUS), switch_inline_query="share")
    kb.button(text=tr(lang, "b_back"), callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()


def invite_kb(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=tr(lang, "b_share", n=config.SHARE_BONUS), switch_inline_query="share")
    kb.button(text=tr(lang, "b_back"), callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()


def donate_kb(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for amount in DONATE_PRESETS:
        kb.button(text=f"{amount} ⭐", callback_data=f"don:{amount}")
    kb.button(text=tr(lang, "b_other"), callback_data="don:other")
    kb.button(text=tr(lang, "b_back"), callback_data="menu:premium")
    kb.adjust(4, 1, 1)
    return kb.as_markup()


def lang_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🇺🇦 Українська", callback_data="lang:uk")
    kb.button(text="🇷🇺 Русский", callback_data="lang:ru")
    kb.button(text="🇬🇧 English", callback_data="lang:en")
    kb.adjust(1)
    return kb.as_markup()


def format_kb(lang: str, token: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 360p", callback_data=f"dl:{token}:v360")
    kb.button(text="🎬 720p", callback_data=f"dl:{token}:v720")
    kb.button(text="🎬 1080p 💎", callback_data=f"dl:{token}:v1080")
    kb.button(text=tr(lang, "b_audio"), callback_data=f"dl:{token}:mp3")
    kb.button(text=tr(lang, "b_cut"), callback_data=f"dl:{token}:cut")
    kb.button(text=tr(lang, "b_cancel"), callback_data=f"dl:{token}:x")
    kb.adjust(3, 1, 1, 1)
    return kb.as_markup()


def search_kb(token: str, items: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i, item in enumerate(items):
        dur = ""
        if item.duration:
            dur = f"{item.duration // 60}:{item.duration % 60:02d} · "
        kb.button(text=f"{dur}{item.title}"[:60], callback_data=f"sr:{token}:{i}")
    kb.adjust(1)
    return kb.as_markup()


# --------------------------------------------------------------------------- #
#  Тексти екранів
# --------------------------------------------------------------------------- #
def promo_banner(lang: str, until) -> str:
    return tr(lang, "promo_banner", price=config.PROMO_PRICE, until=db.fmt_dt(until))


def profile_text(lang: str, access: db.Access, name: str) -> str:
    if access.is_premium:
        return tr(lang, "profile_prem", name=esc(name), until=db.fmt_dt(access.premium_until))
    return tr(
        lang, "profile_free",
        name=esc(name), daily=access.daily_left, limit=config.FREE_LIMIT, bonus=access.bonus,
        reset=fmt_td(lang, db.time_to_reset().total_seconds()), refs=access.ref_count,
    )


def premium_text(lang: str, promo_until=None) -> str:
    lines = "\n".join(
        f"{tr(lang, 'plan_' + pid)} — <b>{PLANS[pid]['stars']} ⭐</b>" for pid in REGULAR_PLANS
    )
    text = tr(lang, "premium_text", lines=lines)
    return f"{promo_banner(lang, promo_until)}\n\n{text}" if promo_until else text


def paywall_text(lang: str, access: db.Access, promo_until=None) -> str:
    text = tr(lang, "paywall", reset=fmt_td(lang, db.time_to_reset().total_seconds()))
    if access.can_share:
        text += "\n\n" + tr(lang, "paywall_share", n=config.SHARE_BONUS)
    if promo_until:
        text = promo_banner(lang, promo_until) + "\n\n" + text
    return text


def done_text(lang: str, access: db.Access) -> str:
    if access.is_premium:
        tail = tr(lang, "tail_prem", until=db.fmt_dt(access.premium_until))
    else:
        tail = tr(lang, "tail_free", daily=access.daily_left, limit=config.FREE_LIMIT)
        if access.bonus:
            tail += tr(lang, "tail_bonus", bonus=access.bonus)
    return tr(lang, "done", tail=tail)


async def send_paywall(bot: Bot, chat_id: int, lang: str, access: db.Access, status=None) -> None:
    promo = await db.promo_offer(access)
    await edit_or_send(
        bot, chat_id, status, paywall_text(lang, access, promo), paywall_kb(lang, access, promo)
    )


# --------------------------------------------------------------------------- #
#  Прогрес
# --------------------------------------------------------------------------- #
def bar(percent: int) -> str:
    filled = max(0, min(10, percent // 10))
    return "▓" * filled + "░" * (10 - filled)


def progress_text(lang: str, prog: Progress) -> str:
    p = int(prog.percent)
    if prog.stage == "prepare":
        return tr(lang, "p_prepare")
    if prog.stage == "queue":
        return tr(lang, "p_queue")
    if prog.stage == "cached":
        return tr(lang, "p_cached")
    if prog.stage == "send":
        return tr(lang, "p_send", bar=bar(100))
    if prog.stage == "convert":
        return tr(lang, "p_conv", bar=bar(p), p=p)
    return tr(lang, "p_dl", bar=bar(p), p=p)


async def progress_updater(msg: Message, prog: Progress, lang: str, label: str) -> None:
    last = ""
    while True:
        text = progress_text(lang, prog)
        if label:
            text = f"{label}\n{text}"
        if text != last:
            try:
                await msg.edit_text(text)
                last = text
            except TelegramRetryAfter as exc:
                await asyncio.sleep(exc.retry_after)
                continue
            except TelegramBadRequest:
                last = text
        await asyncio.sleep(1.5)


# --------------------------------------------------------------------------- #
#  Відправка файлу та головний конвеєр
# --------------------------------------------------------------------------- #
def build_caption(lang: str, kind: str, title: str) -> str:
    emoji = {"audio": "🎵", "gif": "🎞"}.get(kind, "🎬")
    text = f"{emoji} <b>{esc(title[:200])}</b>"
    if BOT_USERNAME:
        text += "\n\n" + tr(lang, "caption_via", bot=BOT_USERNAME)
    return text


async def send_media(
    bot: Bot, chat_id: int, lang: str, media, kind: str,
    title: str, performer: str | None, duration: int | None,
) -> str:
    """Надсилає файл (FSInputFile або file_id з кешу) і повертає file_id для кешування."""
    caption = build_caption(lang, kind, title)
    if kind == "audio":
        await bot.send_chat_action(chat_id, ChatAction.UPLOAD_VOICE)
        msg = await bot.send_audio(
            chat_id, media, caption=caption, title=title[:100],
            performer=(performer or "")[:100] or None, duration=duration,
        )
        return msg.audio.file_id
    await bot.send_chat_action(chat_id, ChatAction.UPLOAD_VIDEO)
    if kind == "gif":
        msg = await bot.send_animation(chat_id, media, caption=caption, duration=duration)
        return msg.animation.file_id
    msg = await bot.send_video(
        chat_id, media, caption=caption, duration=duration, supports_streaming=True
    )
    return msg.video.file_id


async def deliver(
    bot: Bot, chat_id: int, user_id: int, lang: str, job: Job, status: Message, label: str = ""
) -> db.Access:
    """Один файл: перевірки -> кеш -> завантаження -> відправка -> списання ліміту."""
    prog = Progress()
    updater = asyncio.create_task(progress_updater(status, prog, lang, label))
    job_dir = config.DOWNLOAD_DIR / uuid.uuid4().hex
    try:
        prep = await downloader.prepare(job.url, job.platform, job.opts, job.spotify_meta)

        if prep.key:  # цей файл уже надсилали раніше — віддаємо миттєво по file_id
            hit = await db.get_cache(prep.key)
            if hit:
                prog.stage = "cached"
                try:
                    await send_media(
                        bot, chat_id, lang, hit.file_id, hit.kind,
                        hit.title or prep.title, hit.performer, hit.duration,
                    )
                    return await db.register_download(user_id, job.platform, job.opts.fmt, cached=True)
                except TelegramBadRequest:  # file_id застарів — качаємо заново
                    await db.delete_cache(prep.key)
                    prog.stage = "prepare"

        if SEM.locked():
            prog.stage = "queue"
        async with SEM:
            job_dir.mkdir(parents=True, exist_ok=True)
            path = await downloader.download(prep, job.platform, job_dir, prog)
            prog.stage = "send"
            file_id = await send_media(
                bot, chat_id, lang, FSInputFile(path), prep.kind,
                prep.title, prep.performer, prep.duration,
            )
        if prep.key:
            await db.put_cache(prep.key, file_id, prep.kind, prep.title, prep.performer, prep.duration)
        return await db.register_download(user_id, job.platform, job.opts.fmt)
    finally:
        updater.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await updater
        shutil.rmtree(job_dir, ignore_errors=True)  # тимчасові файли видаляємо ЗАВЖДИ


async def run_job(
    bot: Bot, chat_id: int, user_id: int, lang: str, job: Job,
    status: Message | None = None, tracks: list | None = None,
) -> None:
    if user_id in ACTIVE:
        await edit_or_send(bot, chat_id, status, tr(lang, "busy"), main_menu(lang))
        return
    ACTIVE.add(user_id)
    try:
        access = await db.get_access(user_id)
        if tracks is None and not access.allowed:
            await send_paywall(bot, chat_id, lang, access, status)
            return

        status = await edit_or_send(bot, chat_id, status, tr(lang, "p_prepare"))

        if tracks is None:
            access = await deliver(bot, chat_id, user_id, lang, job, status)
            with contextlib.suppress(Exception):
                await status.delete()
            await bot.send_message(chat_id, done_text(lang, access), reply_markup=main_menu(lang))
            return

        # --- альбом / плейлист Spotify (лише преміум) ---
        sent = 0
        for i, meta in enumerate(tracks, 1):
            track_job = Job(job.url, "spotify", Options(fmt="mp3"), spotify_meta=meta)
            label = tr(lang, "col_label", i=i, n=len(tracks))
            try:
                await deliver(bot, chat_id, user_id, lang, track_job, status, label)
                sent += 1
            except MediaError as exc:
                log.info("Трек %s пропущено: %s", meta, exc.code)
            except Exception:
                log.exception("Помилка під час завантаження треку з колекції")
        with contextlib.suppress(Exception):
            await status.delete()
        await bot.send_message(
            chat_id, tr(lang, "col_done", ok=sent, n=len(tracks)), reply_markup=main_menu(lang)
        )

    except MediaError as exc:
        await edit_or_send(bot, chat_id, status, err_text(lang, exc), main_menu(lang))
    except Exception:
        log.exception("Непередбачена помилка під час завантаження")
        await edit_or_send(bot, chat_id, status, tr(lang, "unexpected"), main_menu(lang))
    finally:
        ACTIVE.discard(user_id)


# --------------------------------------------------------------------------- #
#  Команди
# --------------------------------------------------------------------------- #
@router.message(CommandStart())
async def cmd_start(m: Message, command: CommandObject, bot: Bot) -> None:
    uid = m.from_user.id
    AWAIT.pop(uid, None)
    ref_match = re.fullmatch(r"ref_(\d+)", command.args or "")
    ref_id = int(ref_match.group(1)) if ref_match else None
    _, applied = await db.register_start(uid, ref_id)
    access, lang = await get_ctx(m.from_user)

    promo = await db.promo_offer(access)
    text = tr(lang, "welcome", name=esc(m.from_user.full_name), limit=config.FREE_LIMIT)
    if promo:
        text = promo_banner(lang, promo) + "\n\n" + text
    await m.answer(text, reply_markup=main_menu(lang))

    if applied and ref_id:
        await m.answer(tr(lang, "ref_new", bonus=config.REF_BONUS))
        ref_access = await db.get_access(ref_id)
        with contextlib.suppress(TelegramForbiddenError, TelegramBadRequest):
            await bot.send_message(
                ref_id, tr(pick_lang(ref_access.lang, None), "ref_reward", bonus=config.REF_BONUS)
            )


@router.message(Command("menu"))
async def cmd_menu(m: Message) -> None:
    AWAIT.pop(m.from_user.id, None)
    _, lang = await get_ctx(m.from_user)
    await m.answer(tr(lang, "menu_title"), reply_markup=main_menu(lang))


@router.message(Command("profile"))
async def cmd_profile(m: Message) -> None:
    access, lang = await get_ctx(m.from_user)
    await m.answer(profile_text(lang, access, m.from_user.full_name), reply_markup=main_menu(lang))


@router.message(Command("premium"))
async def cmd_premium(m: Message) -> None:
    access, lang = await get_ctx(m.from_user)
    promo = await db.promo_offer(access)
    await m.answer(premium_text(lang, promo), reply_markup=premium_kb(lang, promo))


@router.message(Command("help"))
async def cmd_help(m: Message) -> None:
    _, lang = await get_ctx(m.from_user)
    await m.answer(
        tr(lang, "help", limit=config.FREE_LIMIT, contact=esc(config.SUPPORT_CONTACT)),
        reply_markup=main_menu(lang),
    )


@router.message(Command("invite"))
async def cmd_invite(m: Message) -> None:
    access, lang = await get_ctx(m.from_user)
    await m.answer(
        tr(lang, "invite", bonus=config.REF_BONUS, link=ref_link(m.from_user.id), count=access.ref_count),
        reply_markup=invite_kb(lang),
    )


@router.message(Command("donate"))
async def cmd_donate(m: Message) -> None:
    _, lang = await get_ctx(m.from_user)
    await m.answer(
        tr(lang, "donate_menu", min=config.DONATE_MIN, max=config.DONATE_MAX), reply_markup=donate_kb(lang)
    )


@router.message(Command("lang"))
async def cmd_lang(m: Message) -> None:
    _, lang = await get_ctx(m.from_user)
    await m.answer(tr(lang, "lang_choose"), reply_markup=lang_kb())


@router.message(Command("privacy"))
async def cmd_privacy(m: Message) -> None:
    _, lang = await get_ctx(m.from_user)
    await m.answer(tr(lang, "privacy", contact=esc(config.SUPPORT_CONTACT)), reply_markup=main_menu(lang))


@router.message(Command("paysupport"))
async def cmd_paysupport(m: Message) -> None:
    _, lang = await get_ctx(m.from_user)
    await m.answer(
        tr(lang, "paysupport", contact=esc(config.SUPPORT_CONTACT)), reply_markup=main_menu(lang)
    )


# --------------------------------------------------------------------------- #
#  Меню та мова (inline-кнопки)
# --------------------------------------------------------------------------- #
@router.callback_query(F.data.startswith("menu:"))
async def on_menu(cb: CallbackQuery) -> None:
    await cb.answer()
    AWAIT.pop(cb.from_user.id, None)
    action = cb.data.split(":", 1)[1]
    access, lang = await get_ctx(cb.from_user)
    if action == "main":
        await show(cb.message, tr(lang, "menu_title"), main_menu(lang))
    elif action == "download":
        await show(cb.message, tr(lang, "download_hint"), main_menu(lang))
    elif action == "premium":
        promo = await db.promo_offer(access)
        await show(cb.message, premium_text(lang, promo), premium_kb(lang, promo))
    elif action == "profile":
        await show(cb.message, profile_text(lang, access, cb.from_user.full_name), main_menu(lang))
    elif action == "help":
        await show(
            cb.message,
            tr(lang, "help", limit=config.FREE_LIMIT, contact=esc(config.SUPPORT_CONTACT)),
            main_menu(lang),
        )
    elif action == "invite":
        await show(
            cb.message,
            tr(lang, "invite", bonus=config.REF_BONUS, link=ref_link(cb.from_user.id), count=access.ref_count),
            invite_kb(lang),
        )
    elif action == "donate":
        await show(
            cb.message,
            tr(lang, "donate_menu", min=config.DONATE_MIN, max=config.DONATE_MAX),
            donate_kb(lang),
        )
    elif action == "lang":
        await show(cb.message, tr(lang, "lang_choose"), lang_kb())


@router.callback_query(F.data.startswith("lang:"))
async def on_lang(cb: CallbackQuery) -> None:
    code = cb.data.split(":", 1)[1]
    if code not in LANGS:
        await cb.answer()
        return
    await db.set_lang(cb.from_user.id, code)
    await cb.answer()
    await show(cb.message, tr(code, "lang_set") + "\n\n" + tr(code, "menu_title"), main_menu(code))


# --------------------------------------------------------------------------- #
#  Оплата Telegram Stars (тарифи, акція, донати)
# --------------------------------------------------------------------------- #
async def send_invoice(
    target: Message, title: str, description: str, payload: str, stars: int
) -> None:
    await target.answer_invoice(
        title=title[:32],
        description=description[:255],
        payload=payload,
        currency="XTR",  # Telegram Stars
        prices=[LabeledPrice(label=title[:32], amount=stars)],
    )


@router.callback_query(F.data.startswith("buy:"))
async def on_buy(cb: CallbackQuery) -> None:
    pid = cb.data.split(":", 1)[1]
    plan = PLANS.get(pid)
    access, lang = await get_ctx(cb.from_user)
    if not plan:
        await cb.answer(tr(lang, "pre_fail"), show_alert=True)
        return
    if pid == "promo" and not await db.promo_offer(access):
        await cb.answer(tr(lang, "promo_closed"), show_alert=True)
        return
    await cb.answer()
    await send_invoice(
        cb.message, tr(lang, f"plan_{pid}"), tr(lang, "plan_desc", days=plan["days"]),
        f"plan:{pid}", plan["stars"],
    )


@router.callback_query(F.data.startswith("don:"))
async def on_donate(cb: CallbackQuery) -> None:
    _, lang = await get_ctx(cb.from_user)
    value = cb.data.split(":", 1)[1]
    await cb.answer()
    if value == "other":
        AWAIT[cb.from_user.id] = ("donate", time.time(), {})
        await show(
            cb.message,
            tr(lang, "donate_ask", min=config.DONATE_MIN, max=config.DONATE_MAX),
            back_kb(lang, "menu:donate"),
        )
        return
    if value.isdigit() and config.DONATE_MIN <= int(value) <= config.DONATE_MAX:
        await send_invoice(
            cb.message, tr(lang, "donate_title"), tr(lang, "donate_desc"), "donate", int(value)
        )


@router.pre_checkout_query()
async def on_pre_checkout(q: PreCheckoutQuery) -> None:
    payload = q.invoice_payload
    ok = q.currency == "XTR"
    if payload == "donate":
        ok = ok and config.DONATE_MIN <= q.total_amount <= config.DONATE_MAX
    elif payload.startswith("plan:") and payload[5:] in PLANS:
        if payload == "plan:promo":
            access = await db.get_access(q.from_user.id)
            ok = ok and bool(await db.promo_offer(access))
    else:
        ok = False
    if ok:
        await q.answer(ok=True)
    else:
        lang = pick_lang(None, q.from_user.language_code)
        await q.answer(ok=False, error_message=tr(lang, "pre_fail"))


@router.message(F.successful_payment)
async def on_paid(m: Message) -> None:
    sp = m.successful_payment
    uid = m.from_user.id
    _, lang = await get_ctx(m.from_user)

    if sp.invoice_payload == "donate":
        is_new, _ = await db.add_payment(uid, "donate", 0, sp.total_amount, sp.telegram_payment_charge_id)
        if is_new:
            await m.answer(tr(lang, "donate_thanks"), reply_markup=main_menu(lang))
        return

    pid = sp.invoice_payload.split(":")[-1]
    plan = PLANS.get(pid)
    if not plan:
        log.error("Оплата з невідомим тарифом: %s", sp.invoice_payload)
        await m.answer(tr(lang, "paid_unknown", contact=esc(config.SUPPORT_CONTACT)))
        return
    is_new, until = await db.add_payment(
        uid, pid, plan["days"], sp.total_amount, sp.telegram_payment_charge_id
    )
    if not is_new:  # цей платіж уже оброблено
        return
    await m.answer(
        tr(lang, "paid_thanks", plan=tr(lang, f"plan_{pid}"), until=db.fmt_dt(until)),
        reply_markup=main_menu(lang),
    )


# --------------------------------------------------------------------------- #
#  "Поділитись ботом" через inline-режим (бонус лише за реальну відправку)
# --------------------------------------------------------------------------- #
@router.inline_query()
async def on_inline(q: InlineQuery) -> None:
    access = await db.get_access(q.from_user.id)
    lang = pick_lang(access.lang, q.from_user.language_code)
    link = ref_link(q.from_user.id)
    open_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=tr(lang, "share_open"), url=link)]]
    )
    result = InlineQueryResultArticle(
        id="share",
        title=tr(lang, "share_title"),
        description=tr(lang, "share_desc", n=config.SHARE_BONUS),
        input_message_content=InputTextMessageContent(message_text=tr(lang, "share_message", link=link)),
        reply_markup=open_kb,
    )
    await q.answer([result], cache_time=0, is_personal=True)


@router.chosen_inline_result()
async def on_chosen(chosen: ChosenInlineResult, bot: Bot) -> None:
    if chosen.result_id != "share":
        return
    if await db.grant_share_bonus(chosen.from_user.id):
        access = await db.get_access(chosen.from_user.id)
        lang = pick_lang(access.lang, chosen.from_user.language_code)
        with contextlib.suppress(TelegramForbiddenError, TelegramBadRequest):
            await bot.send_message(chosen.from_user.id, tr(lang, "share_rewarded", n=config.SHARE_BONUS))


# --------------------------------------------------------------------------- #
#  Обрізка / GIF: розбір тайм-кодів
# --------------------------------------------------------------------------- #
CUT_RE = re.compile(
    r"^\s*(\d+(?::\d{1,2}){0,2})\s*[-–—]\s*(\d+(?::\d{1,2}){0,2})(?:\s+(mp3|mp4|gif))?\s*$", re.I
)


def _to_seconds(value: str) -> int:
    total = 0
    for part in value.split(":"):
        total = total * 60 + int(part)
    return total


def parse_cut(text: str) -> tuple[float, float, str] | None:
    m = CUT_RE.match(text)
    if not m:
        return None
    start, end = _to_seconds(m.group(1)), _to_seconds(m.group(2))
    if end <= start:
        return None
    return float(start), float(end), (m.group(3) or "mp4").lower()


# --------------------------------------------------------------------------- #
#  Адмінські команди (працюють лише для ID зі змінної ADMIN_IDS)
# --------------------------------------------------------------------------- #
ADMIN = F.from_user.id.in_(config.ADMIN_IDS)


@router.message(Command("stats"), ADMIN)
async def cmd_stats(m: Message) -> None:
    s = await db.get_stats()
    window = await db.promo_window()
    promo = f"🔥 Акція триває до {db.fmt_dt(window[1])}" if window else "Акція вимкнена"
    await m.answer(
        "📊 <b>Статистика</b>\n\n"
        f"👥 Користувачів: <b>{s['users']}</b> (нових сьогодні: {s['new_today']}, активних сьогодні: {s['active_today']})\n"
        f"💎 Преміум зараз: <b>{s['premium_now']}</b>\n"
        f"🤝 Запрошень: <b>{s['referrals']}</b>\n"
        f"📥 Завантажень: сьогодні <b>{s['dl_today']}</b>, усього <b>{s['dl_total']}</b> "
        f"(миттєво з кешу: {s['dl_cached']}, файлів у кеші: {s['cache_items']})\n"
        f"⭐ Платежів: <b>{s['payments']}</b>, зірок усього: <b>{s['stars_total']}</b> "
        f"(з них донати: {s['stars_donate']})\n\n{promo}"
    )


@router.message(Command("promo"), ADMIN)
async def cmd_promo(m: Message) -> None:
    window = await db.promo_window()
    if window:
        await m.answer(f"🔥 Акція триває до {db.fmt_dt(window[1])}. Вимкнути: /promo_off")
    else:
        await m.answer(f"Акція вимкнена. Увімкнути на {config.PROMO_DAYS} дн.: /promo_on (або /promo_on 3)")


@router.message(Command("promo_on"), ADMIN)
async def cmd_promo_on(m: Message, command: CommandObject) -> None:
    days = int(command.args) if command.args and command.args.strip().isdigit() else config.PROMO_DAYS
    until = await db.start_promo(max(1, min(days, 60)))
    await m.answer(
        f"🔥 Акцію запущено до {db.fmt_dt(until)}: день безліміту за {config.PROMO_PRICE} ⭐ "
        "для нових користувачів. Не забудь анонсувати її (/broadcast)!"
    )


@router.message(Command("promo_off"), ADMIN)
async def cmd_promo_off(m: Message) -> None:
    await db.stop_promo()
    await m.answer("Акцію вимкнено.")


@router.message(Command("broadcast"), ADMIN)
async def cmd_broadcast(m: Message, command: CommandObject) -> None:
    if not command.args:
        await m.answer("Використання: /broadcast текст повідомлення (підтримується HTML)")
        return
    BROADCAST[m.from_user.id] = command.args
    total = len(await db.all_user_ids())
    await m.answer(
        f"📣 <b>Попередній перегляд</b> (отримувачів: {total}):\n\n{command.args}\n\n"
        "Підтвердити відправку: /broadcast_confirm"
    )


async def _broadcast(bot: Bot, admin_chat: int, text: str) -> None:
    ok = fail = 0
    for uid in await db.all_user_ids():
        try:
            await bot.send_message(uid, text)
            ok += 1
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            try:
                await bot.send_message(uid, text)
                ok += 1
            except Exception:
                fail += 1
        except Exception:  # користувач заблокував бота тощо
            fail += 1
        await asyncio.sleep(0.05)  # ~20 повідомлень/сек — безпечно для лімітів Telegram
    await bot.send_message(admin_chat, f"📣 Розсилку завершено: доставлено {ok}, не вдалося {fail}.")


@router.message(Command("broadcast_confirm"), ADMIN)
async def cmd_broadcast_confirm(m: Message, bot: Bot) -> None:
    text = BROADCAST.pop(m.from_user.id, None)
    if not text:
        await m.answer("Немає тексту для розсилки. Спочатку: /broadcast текст")
        return
    await m.answer("🚀 Розсилку запущено…")
    asyncio.create_task(_broadcast(bot, m.chat.id, text))


# --------------------------------------------------------------------------- #
#  Пошук за назвою
# --------------------------------------------------------------------------- #
async def do_search(m: Message, lang: str, query: str) -> None:
    uid = m.from_user.id
    if len(query) < 2:
        await m.answer(tr(lang, "search_short"), reply_markup=main_menu(lang))
        return
    now = time.time()
    if now - LAST_SEARCH.get(uid, 0) < 2:
        await m.answer(tr(lang, "search_slow"))
        return
    LAST_SEARCH[uid] = now
    query = query[:100]
    status = await m.answer(tr(lang, "search_wait", q=esc(query)))
    try:
        items = await downloader.search(query)
    except MediaError as exc:
        await show(status, err_text(lang, exc), main_menu(lang))
        return
    if not items:
        await show(status, tr(lang, "search_none"), main_menu(lang))
        return
    token = remember(uid, items)
    await show(status, tr(lang, "search_results", q=esc(query)), search_kb(token, items))


@router.callback_query(F.data.startswith("sr:"))
async def on_search_pick(cb: CallbackQuery, bot: Bot) -> None:
    _, token, idx = cb.data.split(":")
    _, lang = await get_ctx(cb.from_user)
    entry = PENDING.get(token)
    if not entry or entry[0] != cb.from_user.id or not idx.isdigit() or int(idx) >= len(entry[1]):
        await cb.answer(tr(lang, "expired"), show_alert=True)
        return
    await cb.answer()
    item = entry[1][int(idx)]
    await run_job(
        bot, cb.message.chat.id, cb.from_user.id, lang,
        Job(item.url, "youtube", Options(fmt="mp3")), status=cb.message,
    )


# --------------------------------------------------------------------------- #
#  Вибір формату для YouTube
# --------------------------------------------------------------------------- #
QUALITY = {"v360": 360, "v720": 720, "v1080": 1080}


@router.callback_query(F.data.startswith("dl:"))
async def on_format(cb: CallbackQuery, bot: Bot) -> None:
    _, token, code = cb.data.split(":")
    uid = cb.from_user.id
    access, lang = await get_ctx(cb.from_user)
    entry = PENDING.get(token)
    if not entry or entry[0] != uid:
        await cb.answer(tr(lang, "expired"), show_alert=True)
        return
    url = entry[1]
    await cb.answer()

    if code == "x":
        PENDING.pop(token, None)
        await show(cb.message, tr(lang, "cancelled"), main_menu(lang))
        return
    if code in ("v1080", "cut") and not access.is_premium:
        promo = await db.promo_offer(access)
        await show(cb.message, tr(lang, "premium_only"), premium_kb(lang, promo))
        return
    PENDING.pop(token, None)
    if code == "cut":
        AWAIT[uid] = ("cut", time.time(), {"url": url, "platform": "youtube"})
        await show(
            cb.message,
            tr(lang, "cut_prompt", gif=config.MAX_GIF_SEC, max=config.MAX_TRIM_SEC),
            back_kb(lang),
        )
        return
    opts = Options(fmt="mp3") if code == "mp3" else Options(fmt="mp4", height=QUALITY.get(code, 720))
    await run_job(bot, cb.message.chat.id, uid, lang, Job(url, "youtube", opts), status=cb.message)


# --------------------------------------------------------------------------- #
#  Текст від користувача: очікувані відповіді, посилання, пошук
# --------------------------------------------------------------------------- #
async def handle_awaited(
    m: Message, bot: Bot, access: db.Access, lang: str, pending: tuple[str, float, dict]
) -> bool:
    """Обробляє відповідь на питання бота (сума донату / тайм-коди). True — повідомлення використано."""
    kind, _, data = pending
    text = m.text.strip()
    uid = m.from_user.id
    if URL_RE.search(text):  # людина передумала й надіслала нове посилання
        return False

    if kind == "donate":
        if text.isdigit() and config.DONATE_MIN <= int(text) <= config.DONATE_MAX:
            await send_invoice(
                m, tr(lang, "donate_title"), tr(lang, "donate_desc"), "donate", int(text)
            )
        else:
            AWAIT[uid] = ("donate", time.time(), {})
            await m.answer(tr(lang, "donate_bad", min=config.DONATE_MIN, max=config.DONATE_MAX))
        return True

    if kind == "cut":
        parsed = parse_cut(text)
        if not parsed:
            AWAIT[uid] = ("cut", time.time(), data)
            await m.answer(tr(lang, "cut_bad"))
            return True
        if not access.is_premium:
            promo = await db.promo_offer(access)
            await m.answer(tr(lang, "premium_only"), reply_markup=premium_kb(lang, promo))
            return True
        start, end, fmt = parsed
        opts = Options(fmt=fmt, height=720, trim=(start, end))
        await run_job(bot, m.chat.id, uid, lang, Job(data["url"], data["platform"], opts))
        return True
    return False


@router.message(F.text)
async def on_text(m: Message, bot: Bot) -> None:
    uid = m.from_user.id
    text = m.text.strip()
    access, lang = await get_ctx(m.from_user)

    pending = AWAIT.pop(uid, None)
    if pending and time.time() - pending[1] < AWAIT_TTL:
        if await handle_awaited(m, bot, access, lang, pending):
            return

    if text.startswith("/"):  # невідома команда
        await m.answer(tr(lang, "menu_title"), reply_markup=main_menu(lang))
        return

    match = URL_RE.search(text)
    if not match:
        await do_search(m, lang, text)
        return

    url = match.group(0)
    platform = downloader.detect_platform(url)
    if not platform:
        await m.answer(tr(lang, "unsupported"), reply_markup=main_menu(lang))
        return

    # Spotify: альбоми й плейлисти — преміум-функція
    if platform == "spotify":
        try:
            url = await downloader.spotify_expand(url)
        except MediaError as exc:
            await m.answer(err_text(lang, exc), reply_markup=main_menu(lang))
            return
        if re.search(r"/(album|playlist)/", url):
            if not access.is_premium:
                promo = await db.promo_offer(access)
                await m.answer(tr(lang, "premium_only"), reply_markup=premium_kb(lang, promo))
                return
            status = await m.answer(tr(lang, "p_prepare"))
            try:
                tracks = await downloader.spotify_collection(url)
            except MediaError as exc:
                await show(status, err_text(lang, exc), main_menu(lang))
                return
            await show(status, tr(lang, "col_found", n=len(tracks)))
            await run_job(
                bot, m.chat.id, uid, lang, Job(url, "spotify", Options(fmt="mp3")),
                status=status, tracks=tracks,
            )
            return

    if not access.allowed:
        await send_paywall(bot, m.chat.id, lang, access)
        return

    if platform == "youtube":
        token = remember(uid, url)
        await m.answer(tr(lang, "fmt_choose"), reply_markup=format_kb(lang, token))
    elif platform in ("soundcloud", "spotify"):
        await run_job(bot, m.chat.id, uid, lang, Job(url, platform, Options(fmt="mp3")))
    else:  # tiktok, instagram, twitter, pinterest, facebook -> відео одним кліком
        await run_job(bot, m.chat.id, uid, lang, Job(url, platform, Options(fmt="mp4", height=720)))


# --------------------------------------------------------------------------- #
#  Запуск
# --------------------------------------------------------------------------- #
async def start_health_server() -> None:
    """Безкоштовні хостинги часто вимагають відкритий порт — віддаємо просте "OK"."""
    port = os.getenv("PORT")
    if not port:
        return
    app = web.Application()
    app.router.add_get("/", lambda request: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(port)).start()
    log.info("Health-сервер працює на порту %s", port)


async def main() -> None:
    global BOT_USERNAME
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if not config.BOT_TOKEN:
        raise SystemExit("❌ Не знайдено BOT_TOKEN. Додай токен від @BotFather у змінні середовища.")

    await db.init_db()
    config.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    for leftover in Path(config.DOWNLOAD_DIR).iterdir():  # прибираємо сміття після перезапусків
        shutil.rmtree(leftover, ignore_errors=True)

    if config.LOCAL_API_URL:  # власний Bot API сервер -> файли до 2 ГБ
        session = AiohttpSession(
            api=TelegramAPIServer.from_base(config.LOCAL_API_URL, is_local=True), timeout=600
        )
    else:
        session = AiohttpSession(timeout=300)  # великі файли вантажаться довго
    bot = Bot(
        token=config.BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    BOT_USERNAME = (await bot.get_me()).username or ""

    await bot.set_my_commands(
        [
            BotCommand(command="menu", description="🏠 Головне меню"),
            BotCommand(command="profile", description="👤 Мій профіль і ліміти"),
            BotCommand(command="premium", description="💎 Преміум / Тарифи"),
            BotCommand(command="invite", description="🎁 Запросити друзів"),
            BotCommand(command="donate", description="💛 Підтримати проєкт"),
            BotCommand(command="lang", description="🌐 Мова"),
            BotCommand(command="help", description="🤝 Допомога"),
            BotCommand(command="privacy", description="🔒 Конфіденційність"),
            BotCommand(command="paysupport", description="💬 Питання щодо оплати"),
        ]
    )

    dp = Dispatcher()
    dp.include_router(router)
    await start_health_server()
    await bot.delete_webhook(drop_pending_updates=True)
    log.info("Бот @%s запущено ✅", BOT_USERNAME)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
