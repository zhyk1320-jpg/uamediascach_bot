"""
🇺🇦 Медіаконвертер-бот (aiogram 3.x)

Що вміє: YouTube (MP4/MP3), TikTok без водяних знаків, SoundCloud, Spotify (через пошук на YouTube).
Монетизація: 3 безплатні завантаження на добу + безліміт за Telegram Stars (XTR).

Запуск:  python main.py   (потрібна змінна середовища BOT_TOKEN — див. config.py)

ПРО ОПЛАТУ ЗІРКАМИ:
  • Для валюти XTR НЕ потрібні жодні платіжні токени провайдерів — provider_token порожній.
  • Достатньо створити бота в @BotFather. Telegram сам приймає Stars.
  • Бот зобов'язаний відповідати на /paysupport — це вже реалізовано нижче.
"""
import asyncio
import contextlib
import html
import logging
import re
import shutil
import uuid
from collections import OrderedDict
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ChatAction, ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

import config
import db
import downloader
from downloader import MediaError, Progress

log = logging.getLogger("bot")
router = Router()
router.message.filter(F.chat.type == "private")

BOT_USERNAME = ""

# --------------------------------------------------------------------------- #
#  Тарифи
# --------------------------------------------------------------------------- #
PLANS = {
    "day": {
        "title": "🌟 День безліміту",
        "desc": "Безлімітні завантаження протягом 24 годин",
        "stars": config.PRICE_DAY,
        "days": 1,
    },
    "month": {
        "title": "👑 Місяць безліміту",
        "desc": "Безлімітні завантаження протягом 30 днів",
        "stars": config.PRICE_MONTH,
        "days": 30,
    },
}

# --------------------------------------------------------------------------- #
#  Клавіатури
# --------------------------------------------------------------------------- #


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📥 Завантажити медіа", callback_data="menu:download")
    kb.button(text="💎 Преміум / Тарифи", callback_data="menu:premium")
    kb.button(text="👤 Мій профіль (ліміти)", callback_data="menu:profile")
    kb.button(text="🤝 Допомога", callback_data="menu:help")
    kb.adjust(2, 2)
    return kb.as_markup()


def premium_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=f"🌟 День безліміту — {PLANS['day']['stars']} ⭐", callback_data="buy:day")
    kb.button(text=f"👑 Місяць безліміту — {PLANS['month']['stars']} ⭐", callback_data="buy:month")
    kb.button(text="⬅️ Назад у меню", callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()


def format_kb(token: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Відео (MP4)", callback_data=f"dl:{token}:mp4")
    kb.button(text="🎵 Аудіо (MP3)", callback_data=f"dl:{token}:mp3")
    kb.button(text="✖️ Скасувати", callback_data=f"dl:{token}:x")
    kb.adjust(2, 1)
    return kb.as_markup()


# --------------------------------------------------------------------------- #
#  Тексти
# --------------------------------------------------------------------------- #
def welcome_text(name: str) -> str:
    return (
        f"👋 Привіт, <b>{html.escape(name)}</b>!\n\n"
        "Я — твій кишеньковий медіаконвертер 🎧🎬\n"
        "Кидай посилання, а решту зроблю я:\n\n"
        "▶️ <b>YouTube</b> — відео (MP4) або аудіо (MP3)\n"
        "🎵 <b>TikTok</b> — відео у високій якості, без водяних знаків\n"
        "☁️ <b>SoundCloud</b> — аудіотреки\n"
        "🟢 <b>Spotify</b> — знайду трек і надішлю в MP3\n\n"
        f"🎁 Щодня тобі доступно <b>{config.FREE_LIMIT} безплатні завантаження</b>. "
        "Хочеш більше — є 💎 Преміум.\n\n"
        "Обирай, що робимо далі 👇"
    )


DOWNLOAD_TEXT = (
    "📥 <b>Надсилай посилання!</b>\n\n"
    "Просто встав лінк на YouTube, TikTok, SoundCloud або Spotify — і я одразу візьмуся до роботи ✨"
)

NO_LINK_TEXT = (
    "🤔 Я не бачу тут посилання.\n"
    "Надішли лінк на YouTube, TikTok, SoundCloud або Spotify — і я все завантажу!"
)

UNSUPPORTED_TEXT = (
    "🙈 Це посилання я поки не вмію обробляти.\n"
    "Підтримую: <b>YouTube, TikTok, SoundCloud, Spotify</b>."
)


def help_text() -> str:
    return (
        "🤝 <b>Допомога</b>\n\n"
        "<b>Як користуватись:</b>\n"
        "1️⃣ Скопіюй посилання на відео чи трек\n"
        "2️⃣ Надішли його мені\n"
        "3️⃣ Для YouTube обери формат: MP4 або MP3\n"
        "4️⃣ Отримай файл 🎉\n\n"
        "<b>Що підтримується:</b>\n"
        "▶️ YouTube • 🎵 TikTok (без водяних знаків) • ☁️ SoundCloud • 🟢 Spotify (окремі треки)\n\n"
        "<b>Ліміти:</b>\n"
        f"🎁 {config.FREE_LIMIT} безплатні завантаження на добу (оновлюються опівночі)\n"
        "💎 Преміум — без обмежень\n"
        "📦 Максимальний розмір файлу — 50 МБ (обмеження Telegram для ботів)\n\n"
        "<b>Команди:</b>\n"
        "/menu — головне меню\n"
        "/profile — мій профіль і ліміти\n"
        "/premium — тарифи\n"
        "/paysupport — питання щодо оплати\n\n"
        f"Є питання? Пиши: {html.escape(config.SUPPORT_CONTACT)}"
    )


def fmt_td(seconds: float) -> str:
    hours, rest = divmod(int(seconds), 3600)
    return f"{hours} год {rest // 60} хв"


def profile_text(access: db.Access, name: str) -> str:
    if access.is_premium:
        body = (
            f"💎 Тариф: <b>Преміум</b>\n"
            f"♾ Завантаження без обмежень\n"
            f"⏳ Діє до: <b>{db.fmt_dt(access.premium_until)}</b>"
        )
    else:
        body = (
            "🆓 Тариф: <b>Безкоштовний</b>\n"
            f"🎁 Залишилось сьогодні: <b>{access.free_left} із {config.FREE_LIMIT}</b>\n"
            f"🕛 Ліміт оновиться через {fmt_td(db.time_to_reset().total_seconds())} (опівночі)"
        )
    return f"👤 <b>Профіль: {html.escape(name)}</b>\n\n{body}"


def premium_text() -> str:
    day, month = PLANS["day"]["stars"], PLANS["month"]["stars"]
    saving = max(0, round(100 - month / (day * 30) * 100))
    return (
        "💎 <b>Преміум — завантажуй без меж!</b>\n\n"
        f"🌟 <b>День безліміту</b> — {day} ⭐\n"
        f"👑 <b>Місяць безліміту</b> — {month} ⭐ <i>(це на {saving}% вигідніше, ніж щодня)</i>\n\n"
        "Оплата зірками Telegram — у два дотики, не виходячи з чату. "
        "Преміум вмикається миттєво ✨\n"
        "Якщо вже маєш преміум — новий тариф просто продовжить його."
    )


def paywall_text() -> str:
    return (
        "<b>Твої безплатні завантаження на сьогодні закінчилися</b> 🥲\n"
        "Підтримай проєкт або відкрий безліміт!\n\n"
        f"🌟 День безліміту — {PLANS['day']['stars']} ⭐\n"
        f"👑 Місяць безліміту — {PLANS['month']['stars']} ⭐\n\n"
        f"Або зачекай {fmt_td(db.time_to_reset().total_seconds())} — і ліміт оновиться сам 🕛"
    )


# --------------------------------------------------------------------------- #
#  Допоміжне
# --------------------------------------------------------------------------- #
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


URL_RE = re.compile(r"https?://\S+")
PENDING: "OrderedDict[str, tuple[int, str]]" = OrderedDict()  # токен -> (user_id, url)
ACTIVE: set[int] = set()  # користувачі, у яких зараз іде завантаження
SEM = asyncio.Semaphore(config.MAX_PARALLEL)


def remember(user_id: int, url: str) -> str:
    token = uuid.uuid4().hex[:10]
    PENDING[token] = (user_id, url)
    while len(PENDING) > 500:
        PENDING.popitem(last=False)
    return token


def bar(percent: int) -> str:
    filled = max(0, min(10, percent // 10))
    return "▓" * filled + "░" * (10 - filled)


def progress_text(prog: Progress) -> str:
    p = int(prog.percent)
    if prog.stage == "prepare":
        return "🔎 Аналізую посилання…"
    if prog.stage == "convert":
        return f"🔄 Конвертація: [{bar(p)}] {p}%"
    return f"⏳ Завантаження: [{bar(p)}] {p}%"


async def progress_updater(msg: Message, prog: Progress) -> None:
    last = ""
    while True:
        text = progress_text(prog)
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
#  Головний сценарій завантаження
# --------------------------------------------------------------------------- #
async def run_job(
    bot: Bot,
    chat_id: int,
    user_id: int,
    url: str,
    platform: str,
    fmt: str,
    status: Message | None = None,
) -> None:
    if user_id in ACTIVE:
        await edit_or_send(
            bot, chat_id, status,
            "⏳ Я ще працюю над твоїм попереднім файлом. Зачекай хвилинку 🙏",
            main_menu(),
        )
        return

    ACTIVE.add(user_id)
    job_dir = config.DOWNLOAD_DIR / uuid.uuid4().hex
    updater: asyncio.Task | None = None
    try:
        access = await db.get_access(user_id)
        if not access.allowed:
            await edit_or_send(bot, chat_id, status, paywall_text(), premium_kb())
            return

        status = await edit_or_send(bot, chat_id, status, "🔎 Аналізую посилання…")
        if SEM.locked():
            await edit_or_send(
                bot, chat_id, status,
                "🕐 Ти в черзі — зараз я обробляю інші запити. Це ненадовго!",
            )

        async with SEM:
            job_dir.mkdir(parents=True, exist_ok=True)
            prog = Progress()
            updater = asyncio.create_task(progress_updater(status, prog))
            try:
                result = await downloader.fetch_and_download(url, platform, fmt, job_dir, prog)
            finally:
                updater.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await updater

            await edit_or_send(bot, chat_id, status, f"📤 Надсилаю файл: [{bar(100)}] 100%")
            caption = f"🎵 <b>{html.escape(result.title[:200])}</b>"
            if BOT_USERNAME:
                caption += f"\n\n✨ Завантажено через @{BOT_USERNAME}"
            file = FSInputFile(result.path)

            if result.kind == "audio":
                await bot.send_chat_action(chat_id, ChatAction.UPLOAD_VOICE)
                await bot.send_audio(
                    chat_id, file,
                    title=result.title[:100],
                    performer=(result.performer or "")[:100] or None,
                    duration=result.duration,
                    caption=caption,
                )
            else:
                await bot.send_chat_action(chat_id, ChatAction.UPLOAD_VIDEO)
                await bot.send_video(
                    chat_id, file,
                    duration=result.duration,
                    caption=caption.replace("🎵", "🎬", 1),
                    supports_streaming=True,
                )

        access = await db.register_download(user_id)  # ліміт списуємо лише після успіху
        with contextlib.suppress(Exception):
            await status.delete()

        if access.is_premium:
            tail = f"💎 Твій преміум діє до <b>{db.fmt_dt(access.premium_until)}</b>"
        else:
            tail = f"🎁 Залишилось безплатних сьогодні: <b>{access.free_left} із {config.FREE_LIMIT}</b>"
        await bot.send_message(
            chat_id, f"✅ <b>Готово!</b> Насолоджуйся 🎉\n{tail}", reply_markup=main_menu()
        )

    except MediaError as exc:
        await edit_or_send(bot, chat_id, status, str(exc), main_menu())
    except Exception:
        log.exception("Непередбачена помилка під час завантаження")
        await edit_or_send(
            bot, chat_id, status,
            "😵 Ой, щось пішло не так. Спробуй ще раз трохи пізніше — ліміт не списано.",
            main_menu(),
        )
    finally:
        if updater and not updater.done():
            updater.cancel()
        ACTIVE.discard(user_id)
        shutil.rmtree(job_dir, ignore_errors=True)  # тимчасові файли видаляємо ЗАВЖДИ


# --------------------------------------------------------------------------- #
#  Команди
# --------------------------------------------------------------------------- #
@router.message(CommandStart())
async def cmd_start(m: Message) -> None:
    await db.get_access(m.from_user.id)  # створюємо запис користувача
    await m.answer(welcome_text(m.from_user.first_name or "друже"), reply_markup=main_menu())


@router.message(Command("menu"))
async def cmd_menu(m: Message) -> None:
    await m.answer("🏠 <b>Головне меню</b>\nЩо робимо?", reply_markup=main_menu())


@router.message(Command("profile"))
async def cmd_profile(m: Message) -> None:
    access = await db.get_access(m.from_user.id)
    await m.answer(profile_text(access, m.from_user.first_name or "друже"), reply_markup=main_menu())


@router.message(Command("premium"))
async def cmd_premium(m: Message) -> None:
    await m.answer(premium_text(), reply_markup=premium_kb())


@router.message(Command("help"))
async def cmd_help(m: Message) -> None:
    await m.answer(help_text(), reply_markup=main_menu())


@router.message(Command("paysupport"))
async def cmd_paysupport(m: Message) -> None:
    await m.answer(
        "💬 <b>Питання щодо оплати</b>\n\n"
        "Якщо після оплати зірками преміум не активувався або сталася помилка — "
        f"напиши нам: {html.escape(config.SUPPORT_CONTACT)}\n"
        "Вкажи свій ID (його видно в /profile) і час платежу — ми все швидко вирішимо 🙌",
        reply_markup=main_menu(),
    )


# --------------------------------------------------------------------------- #
#  Меню (inline-кнопки)
# --------------------------------------------------------------------------- #
@router.callback_query(F.data.startswith("menu:"))
async def on_menu(cb: CallbackQuery) -> None:
    await cb.answer()
    action = cb.data.split(":", 1)[1]
    name = cb.from_user.first_name or "друже"
    if action == "main":
        await show(cb.message, "🏠 <b>Головне меню</b>\nЩо робимо?", main_menu())
    elif action == "download":
        await show(cb.message, DOWNLOAD_TEXT, main_menu())
    elif action == "premium":
        await show(cb.message, premium_text(), premium_kb())
    elif action == "profile":
        access = await db.get_access(cb.from_user.id)
        await show(cb.message, profile_text(access, name), main_menu())
    elif action == "help":
        await show(cb.message, help_text(), main_menu())


# --------------------------------------------------------------------------- #
#  Оплата Telegram Stars
# --------------------------------------------------------------------------- #
@router.callback_query(F.data.startswith("buy:"))
async def on_buy(cb: CallbackQuery) -> None:
    plan_id = cb.data.split(":", 1)[1]
    plan = PLANS.get(plan_id)
    if not plan:
        await cb.answer("Невідомий тариф", show_alert=True)
        return
    await cb.answer()
    await cb.message.answer_invoice(
        title=plan["title"],
        description=plan["desc"],
        payload=f"premium:{plan_id}",
        currency="XTR",  # Telegram Stars
        prices=[LabeledPrice(label=plan["title"], amount=plan["stars"])],
    )


@router.pre_checkout_query()
async def on_pre_checkout(q: PreCheckoutQuery) -> None:
    plan_id = q.invoice_payload.split(":")[-1]
    if q.currency == "XTR" and plan_id in PLANS:
        await q.answer(ok=True)
    else:
        await q.answer(ok=False, error_message="Щось пішло не так. Спробуй ще раз 🙏")


@router.message(F.successful_payment)
async def on_paid(m: Message) -> None:
    sp = m.successful_payment
    plan_id = sp.invoice_payload.split(":")[-1]
    plan = PLANS.get(plan_id)
    if not plan:
        log.error("Оплата з невідомим тарифом: %s", sp.invoice_payload)
        await m.answer(
            f"😬 Оплату отримано, але тариф не розпізнано. Напиши {html.escape(config.SUPPORT_CONTACT)} — виправимо!"
        )
        return
    until = await db.add_premium(
        m.from_user.id, plan_id, plan["days"], sp.total_amount, sp.telegram_payment_charge_id
    )
    if until is None:  # цей платіж уже оброблено
        return
    await m.answer(
        "🎉 <b>Дякуємо за підтримку!</b> 💛\n\n"
        f"Преміум активовано: <b>{plan['title']}</b>\n"
        f"⏳ Діє до: <b>{db.fmt_dt(until)}</b>\n\n"
        "Тепер завантажуй скільки завгодно — просто надсилай посилання 🚀",
        reply_markup=main_menu(),
    )


# --------------------------------------------------------------------------- #
#  Посилання від користувача
# --------------------------------------------------------------------------- #
@router.message(F.text)
async def on_text(m: Message, bot: Bot) -> None:
    match = URL_RE.search(m.text)
    if not match:
        await m.answer(NO_LINK_TEXT, reply_markup=main_menu())
        return
    url = match.group(0)
    platform = downloader.detect_platform(url)
    if not platform:
        await m.answer(UNSUPPORTED_TEXT, reply_markup=main_menu())
        return

    access = await db.get_access(m.from_user.id)
    if not access.allowed:
        await m.answer(paywall_text(), reply_markup=premium_kb())
        return

    if platform == "youtube":
        token = remember(m.from_user.id, url)
        await m.answer("▶️ Знайшов YouTube-посилання! Що завантажуємо?", reply_markup=format_kb(token))
    elif platform == "tiktok":
        await run_job(bot, m.chat.id, m.from_user.id, url, platform, "mp4")
    else:  # soundcloud / spotify -> завжди MP3
        await run_job(bot, m.chat.id, m.from_user.id, url, platform, "mp3")


@router.callback_query(F.data.startswith("dl:"))
async def on_format(cb: CallbackQuery, bot: Bot) -> None:
    _, token, fmt = cb.data.split(":")
    entry = PENDING.get(token)
    if not entry or entry[0] != cb.from_user.id:
        await cb.answer("Це посилання застаріло — надішли його ще раз 🙂", show_alert=True)
        return
    await cb.answer()
    if fmt == "x":
        PENDING.pop(token, None)
        await show(cb.message, "👌 Скасовано. Надсилай нове посилання, коли захочеш!", main_menu())
        return
    PENDING.pop(token, None)
    url = entry[1]
    platform = downloader.detect_platform(url) or "youtube"
    await run_job(bot, cb.message.chat.id, cb.from_user.id, url, platform, fmt, status=cb.message)


# --------------------------------------------------------------------------- #
#  Запуск
# --------------------------------------------------------------------------- #
async def start_health_server() -> None:
    """Безкоштовні хостинги часто вимагають відкритий порт — віддаємо просте "OK"."""
    import os

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

    bot = Bot(
        token=config.BOT_TOKEN,
        session=AiohttpSession(timeout=300),  # великі файли вантажаться довго
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    BOT_USERNAME = (await bot.get_me()).username or ""

    await bot.set_my_commands(
        [
            BotCommand(command="menu", description="🏠 Головне меню"),
            BotCommand(command="profile", description="👤 Мій профіль і ліміти"),
            BotCommand(command="premium", description="💎 Преміум / Тарифи"),
            BotCommand(command="help", description="🤝 Допомога"),
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
