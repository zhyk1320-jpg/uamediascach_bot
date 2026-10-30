"""
Усі тексти бота трьома мовами: uk (українська), ru (русский), en (English).
Мова визначається за налаштуваннями Telegram користувача; змінити можна командою /lang.
Щоб поправити формулювання — просто відредагуй рядок у потрібному словнику.
Плейсхолдери виду {name} не змінюй.
"""

LANGS = ("uk", "ru", "en")


def pick_lang(saved: str | None, telegram_code: str | None) -> str:
    if saved in LANGS:
        return saved
    code = (telegram_code or "").lower()
    if code.startswith("ru"):
        return "ru"
    if code.startswith("en"):
        return "en"
    return "uk"


UK = {
    # --- кнопки ---
    "b_download": "📥 Завантажити медіа",
    "b_premium": "💎 Преміум / Тарифи",
    "b_profile": "👤 Мій профіль (ліміти)",
    "b_help": "🤝 Допомога",
    "b_invite": "🎁 Запросити друзів",
    "b_lang": "🌐 Мова",
    "b_back": "⬅️ Назад у меню",
    "lifetime": "назавжди ♾",
    "b_open_private": "💬 Відкрити бота",
    "group_hint": "👋 Я завантажую відео й музику!\nНадішли посилання сюди або команду <code>/dl посилання чи назва</code>.\nПрофіль, тарифи й налаштування — в особистих повідомленнях 👇",
    "group_usage": "ℹ️ Використання: <code>/dl посилання</code> або <code>/dl назва пісні</code>",
    "group_paywall": "🥲 Твої безплатні завантаження закінчилися.\nВідкрий бота в особистих повідомленнях — там можна отримати безліміт або бонуси.",
    "group_spotify": "🟢 Альбоми й плейлисти Spotify доступні лише в особистих повідомленнях з ботом.",
    "b_cancel": "✖️ Скасувати",
    "b_audio": "🎵 Аудіо (MP3)",
    "b_cut": "✂️ Обрізати / GIF 💎",
    "b_share": "📤 Поділитись ботом → +{n} скачування",
    "b_donate": "💛 Підтримати проєкт",
    "b_other": "✍️ Інша сума",
    "b_promo": "🔥 АКЦІЯ: {days} дн. за {price} ⭐",
    "promo_tail": "Забирай, поки діє 👇",
    "promo_offer": "Безліміт на {days} дн. усього за <b>{price} ⭐</b>",
    # --- основні екрани ---
    "welcome": (
        "👋 Привіт, <b>{name}</b>!\n\n"
        "Я — твій кишеньковий медіаконвертер 🎧🎬\n"
        "Кидай посилання або просто напиши назву пісні — решту зроблю я:\n\n"
        "▶️ <b>YouTube</b> — відео (MP4) або аудіо (MP3)\n"
        "🎵 <b>TikTok</b> — відео без водяних знаків\n"
        "☁️ <b>SoundCloud</b> і 🟢 <b>Spotify</b> — треки в MP3\n"
        "📸 <b>Instagram, X (Twitter), Pinterest, Facebook</b> — відео\n"
        "🔎 <b>Пошук</b> — напиши, наприклад, «Океан Ельзи Не твоя війна» і обери трек\n\n"
        "🎁 Щодня тобі доступно <b>{limit} безплатні завантаження</b>. Хочеш більше — є 💎 Преміум.\n\n"
        "Обирай, що робимо далі 👇"
    ),
    "menu_title": "🏠 <b>Головне меню</b>\nЩо робимо?",
    "download_hint": (
        "📥 <b>Надсилай посилання або назву!</b>\n\n"
        "• Встав лінк на YouTube, TikTok, SoundCloud, Spotify, Instagram, X, Pinterest чи Facebook\n"
        "• Або просто напиши назву пісні — я знайду й запропоную варіанти ✨"
    ),
    "unsupported": (
        "🙈 Це посилання я поки не вмію обробляти.\n"
        "Підтримую: <b>YouTube, TikTok, SoundCloud, Spotify, Instagram, X, Pinterest, Facebook</b>."
    ),
    "help": (
        "🤝 <b>Допомога</b>\n\n"
        "<b>Як користуватись:</b>\n"
        "1️⃣ Надішли посилання на відео чи трек — або напиши назву пісні\n"
        "2️⃣ Для YouTube обери якість або MP3\n"
        "3️⃣ Отримай файл 🎉\n\n"
        "<b>Ліміти:</b>\n"
        "🎁 {limit} безплатні завантаження на добу (оновлюються опівночі)\n"
        "➕ Бонусні скачування — за запрошення друзів і «поділитись ботом»\n"
        "💎 Преміум — без обмежень, 1080p, обрізка фрагментів, GIF, альбоми й плейлисти Spotify\n"
        "📦 Максимальний розмір файлу — 50 МБ (обмеження Telegram для ботів)\n\n"
        "<b>Команди:</b>\n"
        "/menu — головне меню\n"
        "/profile — профіль і ліміти\n"
        "/premium — тарифи\n"
        "/invite — запросити друзів\n"
        "/donate — підтримати проєкт\n"
        "/lang — змінити мову\n"
        "/privacy — конфіденційність і умови\n"
        "/paysupport — питання щодо оплати\n\n"
        "Є питання? Пиши: {contact}"
    ),
    "profile_prem": (
        "👤 <b>Профіль: {name}</b>\n\n"
        "💎 Тариф: <b>Преміум</b>\n"
        "♾ Завантаження без обмежень\n"
        "⏳ Діє до: <b>{until}</b>"
    ),
    "profile_free": (
        "👤 <b>Профіль: {name}</b>\n\n"
        "🆓 Тариф: <b>Безкоштовний</b>\n"
        "🎁 Сьогодні залишилось: <b>{daily} із {limit}</b>\n"
        "➕ Бонусних скачувань: <b>{bonus}</b>\n"
        "🕛 Добовий ліміт оновиться через {reset}\n"
        "🤝 Запрошено друзів: <b>{refs}</b>"
    ),
    "hm": "{h} год {m} хв",
    # --- тарифи, акція, paywall ---
    "premium_text": (
        "💎 <b>Преміум — завантажуй без меж!</b>\n\n"
        "{lines}\n\n"
        "✨ У преміумі: безліміт, якість 1080p, обрізка фрагментів і GIF, "
        "альбоми та плейлисти Spotify.\n\n"
        "Оплата зірками Telegram — у два дотики, не виходячи з чату. "
        "Преміум вмикається миттєво. Якщо він уже діє — новий тариф його продовжить."
    ),
    "paywall": (
        "<b>Твої безплатні завантаження на сьогодні закінчилися</b> 🥲\n"
        "Підтримай проєкт або відкрий безліміт!\n\n"
        "Або зачекай {reset} — і ліміт оновиться сам 🕛"
    ),
    "paywall_share": "📤 А ще можна поділитись ботом із другом — і отримати <b>+{n}</b> скачування (раз на добу).",
    "promo_banner": "🔥 <b>Спеціальна пропозиція!</b>\n{offer} — діє до {until}.",
    "promo_closed": "😕 Ця акція вже недоступна або ти нею вже скористався.",
    "plan_day": "🌟 День безліміту",
    "plan_week": "⭐ Тиждень безліміту",
    "plan_month": "👑 Місяць безліміту",
    "plan_quarter": "🏆 3 місяці безліміту",
    "plan_promo": "🔥 Акція: безліміт на {days} дн.",
    "plan_desc": "Безлімітні завантаження на {days} дн.: 1080p, обрізка, GIF, плейлисти Spotify",
    "premium_only": (
        "💎 Ця функція доступна в <b>Преміумі</b>.\n"
        "Відкрий безліміт і всі фішки — обери тариф 👇"
    ),
    "pre_fail": "Щось пішло не так. Спробуй ще раз 🙏",
    "paid_thanks": (
        "🎉 <b>Дякуємо за підтримку!</b> 💛\n\n"
        "Преміум активовано: <b>{plan}</b>\n"
        "⏳ Діє до: <b>{until}</b>\n\n"
        "Тепер завантажуй скільки завгодно — просто надсилай посилання 🚀"
    ),
    "paid_unknown": "😬 Оплату отримано, але тариф не розпізнано. Напиши {contact} — виправимо!",
    # --- запрошення, поширення ---
    "invite": (
        "🎁 <b>Запроси друзів — отримуй завантаження!</b>\n\n"
        "За кожного друга, який вперше запустить бота за твоїм посиланням, "
        "ви обоє отримуєте <b>+{bonus}</b> завантаження.\n\n"
        "🔗 Твоє посилання:\n<code>{link}</code>\n\n"
        "Запрошено друзів: <b>{count}</b>"
    ),
    "ref_new": "🎁 Ти зайшов за запрошенням — тобі <b>+{bonus}</b> безплатні завантаження!",
    "ref_reward": "🎉 Твій друг приєднався за посиланням — тобі <b>+{bonus}</b> завантаження!",
    "share_title": "📤 Поділитись ботом",
    "share_desc": "Надішли друзям — і отримай +{n} скачування",
    "share_message": (
        "🎧 Знайшов класного бота: завантажує відео й музику з YouTube, TikTok, SoundCloud, "
        "Spotify та не тільки — безкоштовно щодня!\n\n👉 {link}"
    ),
    "share_open": "🚀 Відкрити бота",
    "share_rewarded": "🎁 Дякуємо, що поділився! Тобі <b>+{n}</b> скачування.",
    # --- донати ---
    "donate_menu": (
        "💛 <b>Підтримати проєкт</b>\n\n"
        "Обери суму або введи свою (від {min} до {max} ⭐). "
        "Це добровільно й допомагає боту працювати та розвиватись 🙏"
    ),
    "donate_ask": "✍️ Надішли число — скільки зірок ⭐ хочеш подарувати (від {min} до {max}).",
    "donate_bad": "🤔 Потрібне ціле число від {min} до {max}. Спробуй ще раз.",
    "donate_title": "💛 Підтримка проєкту",
    "donate_desc": "Добровільний внесок на розвиток бота. Дякуємо!",
    "donate_thanks": "💛 <b>Щиро дякуємо за підтримку!</b> Ти допомагаєш боту ставати кращим.",
    # --- прогрес ---
    "p_prepare": "🔎 Аналізую посилання…",
    "p_queue": "🕐 Ти в черзі — зараз я обробляю інші запити. Це ненадовго!",
    "p_cached": "⚡ Цей файл у мене вже є — надсилаю миттєво!",
    "p_dl": "⏳ Завантаження: [{bar}] {p}%",
    "p_conv": "🔄 Конвертація: [{bar}] {p}%",
    "p_send": "📤 Надсилаю файл: [{bar}] 100%",
    "done": "✅ <b>Готово!</b> Насолоджуйся 🎉\n{tail}",
    "tail_prem": "💎 Твій преміум діє до <b>{until}</b>",
    "tail_free": "🎁 Сьогодні залишилось: <b>{daily} із {limit}</b>",
    "tail_bonus": "  •  ➕ бонусних: <b>{bonus}</b>",
    "caption_via": "✨ Завантажено через @{bot}",
    "busy": "⏳ Я ще працюю над твоїм попереднім файлом. Зачекай хвилинку 🙏",
    "unexpected": "😵 Ой, щось пішло не так. Спробуй ще раз трохи пізніше — ліміт не списано.",
    "expired": "Це посилання застаріло — надішли його ще раз 🙂",
    "cancelled": "👌 Скасовано. Надсилай нове посилання, коли захочеш!",
    "fmt_choose": "▶️ Знайшов YouTube-посилання! Що завантажуємо?",
    # --- пошук ---
    "search_wait": "🔎 Шукаю «{q}»…",
    "search_results": "🎵 Ось що я знайшов за запитом <b>{q}</b>.\nОбери трек 👇",
    "search_none": "😕 Нічого не знайшов. Спробуй іншу назву або встав посилання.",
    "search_short": "🤔 Напиши назву пісні (хоча б 2 символи) або встав посилання.",
    "search_slow": "⏳ Не так швидко 🙂 Зачекай секунду й спробуй ще раз.",
    # --- обрізка / GIF ---
    "cut_prompt": (
        "✂️ <b>Обрізка / GIF</b>\n\n"
        "Надішли проміжок часу, наприклад:\n"
        "<code>0:30-1:15</code> — відео\n"
        "<code>0:30-1:15 mp3</code> — аудіо\n"
        "<code>0:05-0:12 gif</code> — GIF (до {gif} с)\n\n"
        "Максимум для відео й аудіо — {max} с."
    ),
    "cut_bad": "🤔 Не зрозумів проміжок. Формат: <code>0:30-1:15</code> (в кінці можна додати mp3 або gif).",
    # --- колекції Spotify ---
    "col_found": "📃 Знайшов {n} трек(ів) — качаю по черзі…",
    "col_label": "📃 Трек {i} із {n}",
    "col_done": "✅ <b>Готово!</b> Надіслано треків: <b>{ok}</b> із {n}",
    # --- мова ---
    "lang_choose": "🌐 Обери мову / Choose language / Выбери язык",
    "lang_set": "✅ Мову змінено: Українська 🇺🇦",
    # --- оплата / конфіденційність ---
    "paysupport": (
        "💬 <b>Питання щодо оплати</b>\n\n"
        "Якщо після оплати зірками преміум не активувався або сталася помилка — напиши нам: {contact}\n"
        "Вкажи свій ID (його видно в /profile) і час платежу — ми все швидко вирішимо 🙌"
    ),
    "privacy": (
        "🔒 <b>Конфіденційність та умови</b>\n\n"
        "<b>Що зберігається:</b>\n"
        "• твій Telegram ID і мова інтерфейсу;\n"
        "• лічильники завантажень, бонуси, дані про запрошення;\n"
        "• статус і термін Преміуму та службові записи про платежі Stars (ID платежу, сума);\n"
        "• технічний кеш файлів (ідентифікатор медіа й Telegram file_id) — без прив'язки до тебе.\n\n"
        "<b>Чого ми не робимо:</b>\n"
        "• не зберігаємо в базі посилання та пошукові запити, які ти надсилаєш;\n"
        "• не продаємо й не передаємо твої дані третім особам;\n"
        "• не бачимо даних твоєї картки — оплата проходить через Telegram.\n\n"
        "<b>Файли:</b> тимчасові файли видаляються одразу після відправки.\n\n"
        "<b>Умови:</b> бот призначений для особистого використання. Ти сам відповідаєш за те, "
        "що завантажуєш, і за дотримання авторських прав.\n\n"
        "<b>Видалення даних:</b> напиши {contact} — і ми видалимо твої дані."
    ),
    # --- помилки ---
    "e_block": (
        "🤖 YouTube тимчасово блокує сервер бота. Спробуй пізніше "
        "(власник бота може додати cookies або проксі)."
    ),
    "e_private": "🔒 Це приватне відео — до нього я не маю доступу.",
    "e_age": "🔞 Це відео з віковим обмеженням, завантажити його не вдасться.",
    "e_unavailable": "🫥 Це відео недоступне: його видалили або закрили в регіоні.",
    "e_unsupported": "🤔 Не впізнав це посилання. Перевір, що воно веде на конкретне відео чи трек.",
    "e_rate": "🚦 Забагато запитів до сервісу. Зачекай хвилинку й спробуй ще раз.",
    "e_generic": "😕 Не вдалося завантажити. Перевір посилання або спробуй трохи пізніше.",
    "e_spotify_type": "🟢 Це посилання Spotify я не розпізнав. Надішли посилання на трек, альбом або плейлист.",
    "e_spotify_read": "🟢 Не вдалося прочитати дані зі Spotify. Спробуй інше посилання.",
    "e_spotify_open": "🟢 Не вдалося відкрити коротке посилання Spotify.",
    "e_spotify_down": "🟢 Spotify зараз не відповідає. Спробуй трохи пізніше.",
    "e_spotify_keys": "🟢 Альбоми й плейлисти Spotify ще не налаштовані адміністратором бота.",
    "e_notfound": "🔍 Не вдалося знайти цей трек на YouTube. Спробуй інший.",
    "e_playlist": "📃 Плейлисти YouTube та інші добірки не підтримуються — надішли посилання на одне відео чи трек.",
    "e_live": "🔴 Це пряма трансляція — завантажити її неможливо.",
    "e_long": "⏱ Це занадто довго: максимум {minutes} хв (інакше файл не влізе в ліміт Telegram).",
    "e_toobig": "📦 Файл завеликий для Telegram (ліміт ботів — 50 МБ). Спробуй нижчу якість, коротше відео або MP3 🎵",
    "e_nofile": "😕 Файл не вдалося створити. Спробуй інше посилання.",
    "e_cut_range": "✂️ Початок фрагмента — після кінця відео. Перевір тайм-коди.",
    "e_cut_long": "✂️ Фрагмент задовгий: максимум {seconds} с.",
    "e_search": "🔍 Пошук тимчасово недоступний. Спробуй пізніше або встав посилання.",
}

RU = {
    "b_download": "📥 Скачать медиа",
    "b_premium": "💎 Премиум / Тарифы",
    "b_profile": "👤 Мой профиль (лимиты)",
    "b_help": "🤝 Помощь",
    "b_invite": "🎁 Пригласить друзей",
    "b_lang": "🌐 Язык",
    "b_back": "⬅️ Назад в меню",
    "lifetime": "навсегда ♾",
    "b_open_private": "💬 Открыть бота",
    "group_hint": "👋 Я скачиваю видео и музыку!\nОтправь ссылку сюда или команду <code>/dl ссылка или название</code>.\nПрофиль, тарифы и настройки — в личных сообщениях 👇",
    "group_usage": "ℹ️ Использование: <code>/dl ссылка</code> или <code>/dl название песни</code>",
    "group_paywall": "🥲 Твои бесплатные загрузки закончились.\nОткрой бота в личных сообщениях — там можно получить безлимит или бонусы.",
    "group_spotify": "🟢 Альбомы и плейлисты Spotify доступны только в личных сообщениях с ботом.",
    "b_cancel": "✖️ Отмена",
    "b_audio": "🎵 Аудио (MP3)",
    "b_cut": "✂️ Обрезать / GIF 💎",
    "b_share": "📤 Поделиться ботом → +{n} скачивание",
    "b_donate": "💛 Поддержать проект",
    "b_other": "✍️ Другая сумма",
    "b_promo": "🔥 АКЦИЯ: {days} дн. за {price} ⭐",
    "promo_tail": "Забирай, пока действует 👇",
    "promo_offer": "Безлимит на {days} дн. всего за <b>{price} ⭐</b>",
    "welcome": (
        "👋 Привет, <b>{name}</b>!\n\n"
        "Я — твой карманный медиаконвертер 🎧🎬\n"
        "Кидай ссылку или просто напиши название песни — остальное сделаю я:\n\n"
        "▶️ <b>YouTube</b> — видео (MP4) или аудио (MP3)\n"
        "🎵 <b>TikTok</b> — видео без водяных знаков\n"
        "☁️ <b>SoundCloud</b> и 🟢 <b>Spotify</b> — треки в MP3\n"
        "📸 <b>Instagram, X (Twitter), Pinterest, Facebook</b> — видео\n"
        "🔎 <b>Поиск</b> — напиши, например, «Земфира Хочешь» и выбери трек\n\n"
        "🎁 Каждый день тебе доступно <b>{limit} бесплатные загрузки</b>. Хочешь больше — есть 💎 Премиум.\n\n"
        "Выбирай, что делаем дальше 👇"
    ),
    "menu_title": "🏠 <b>Главное меню</b>\nЧто делаем?",
    "download_hint": (
        "📥 <b>Присылай ссылку или название!</b>\n\n"
        "• Вставь ссылку на YouTube, TikTok, SoundCloud, Spotify, Instagram, X, Pinterest или Facebook\n"
        "• Или просто напиши название песни — я найду и предложу варианты ✨"
    ),
    "unsupported": (
        "🙈 Эту ссылку я пока не умею обрабатывать.\n"
        "Поддерживаю: <b>YouTube, TikTok, SoundCloud, Spotify, Instagram, X, Pinterest, Facebook</b>."
    ),
    "help": (
        "🤝 <b>Помощь</b>\n\n"
        "<b>Как пользоваться:</b>\n"
        "1️⃣ Отправь ссылку на видео или трек — или напиши название песни\n"
        "2️⃣ Для YouTube выбери качество или MP3\n"
        "3️⃣ Получи файл 🎉\n\n"
        "<b>Лимиты:</b>\n"
        "🎁 {limit} бесплатные загрузки в сутки (обновляются в полночь)\n"
        "➕ Бонусные скачивания — за приглашение друзей и «поделиться ботом»\n"
        "💎 Премиум — без ограничений, 1080p, обрезка фрагментов, GIF, альбомы и плейлисты Spotify\n"
        "📦 Максимальный размер файла — 50 МБ (ограничение Telegram для ботов)\n\n"
        "<b>Команды:</b>\n"
        "/menu — главное меню\n"
        "/profile — профиль и лимиты\n"
        "/premium — тарифы\n"
        "/invite — пригласить друзей\n"
        "/donate — поддержать проект\n"
        "/lang — сменить язык\n"
        "/privacy — конфиденциальность и условия\n"
        "/paysupport — вопросы по оплате\n\n"
        "Есть вопросы? Пиши: {contact}"
    ),
    "profile_prem": (
        "👤 <b>Профиль: {name}</b>\n\n"
        "💎 Тариф: <b>Премиум</b>\n"
        "♾ Загрузки без ограничений\n"
        "⏳ Действует до: <b>{until}</b>"
    ),
    "profile_free": (
        "👤 <b>Профиль: {name}</b>\n\n"
        "🆓 Тариф: <b>Бесплатный</b>\n"
        "🎁 Сегодня осталось: <b>{daily} из {limit}</b>\n"
        "➕ Бонусных скачиваний: <b>{bonus}</b>\n"
        "🕛 Суточный лимит обновится через {reset}\n"
        "🤝 Приглашено друзей: <b>{refs}</b>"
    ),
    "hm": "{h} ч {m} мин",
    "premium_text": (
        "💎 <b>Премиум — качай без ограничений!</b>\n\n"
        "{lines}\n\n"
        "✨ В премиуме: безлимит, качество 1080p, обрезка фрагментов и GIF, "
        "альбомы и плейлисты Spotify.\n\n"
        "Оплата звёздами Telegram — в два касания, не выходя из чата. "
        "Премиум включается мгновенно. Если он уже действует — новый тариф его продлит."
    ),
    "paywall": (
        "<b>Твои бесплатные загрузки на сегодня закончились</b> 🥲\n"
        "Поддержи проект или открой безлимит!\n\n"
        "Или подожди {reset} — и лимит обновится сам 🕛"
    ),
    "paywall_share": "📤 А ещё можно поделиться ботом с другом — и получить <b>+{n}</b> скачивание (раз в сутки).",
    "promo_banner": "🔥 <b>Специальное предложение!</b>\n{offer} — действует до {until}.",
    "promo_closed": "😕 Эта акция уже недоступна или ты ею уже воспользовался.",
    "plan_day": "🌟 День безлимита",
    "plan_week": "⭐ Неделя безлимита",
    "plan_month": "👑 Месяц безлимита",
    "plan_quarter": "🏆 3 месяца безлимита",
    "plan_promo": "🔥 Акция: безлимит на {days} дн.",
    "plan_desc": "Безлимитные загрузки на {days} дн.: 1080p, обрезка, GIF, плейлисты Spotify",
    "premium_only": (
        "💎 Эта функция доступна в <b>Премиуме</b>.\n"
        "Открой безлимит и все фишки — выбери тариф 👇"
    ),
    "pre_fail": "Что-то пошло не так. Попробуй ещё раз 🙏",
    "paid_thanks": (
        "🎉 <b>Спасибо за поддержку!</b> 💛\n\n"
        "Премиум активирован: <b>{plan}</b>\n"
        "⏳ Действует до: <b>{until}</b>\n\n"
        "Теперь качай сколько угодно — просто присылай ссылки 🚀"
    ),
    "paid_unknown": "😬 Оплата получена, но тариф не распознан. Напиши {contact} — исправим!",
    "invite": (
        "🎁 <b>Приглашай друзей — получай загрузки!</b>\n\n"
        "За каждого друга, который впервые запустит бота по твоей ссылке, "
        "вы оба получаете <b>+{bonus}</b> загрузки.\n\n"
        "🔗 Твоя ссылка:\n<code>{link}</code>\n\n"
        "Приглашено друзей: <b>{count}</b>"
    ),
    "ref_new": "🎁 Ты пришёл по приглашению — тебе <b>+{bonus}</b> бесплатные загрузки!",
    "ref_reward": "🎉 Твой друг присоединился по ссылке — тебе <b>+{bonus}</b> загрузки!",
    "share_title": "📤 Поделиться ботом",
    "share_desc": "Отправь друзьям — и получи +{n} скачивание",
    "share_message": (
        "🎧 Нашёл классного бота: качает видео и музыку с YouTube, TikTok, SoundCloud, "
        "Spotify и не только — бесплатно каждый день!\n\n👉 {link}"
    ),
    "share_open": "🚀 Открыть бота",
    "share_rewarded": "🎁 Спасибо, что поделился! Тебе <b>+{n}</b> скачивание.",
    "donate_menu": (
        "💛 <b>Поддержать проект</b>\n\n"
        "Выбери сумму или введи свою (от {min} до {max} ⭐). "
        "Это добровольно и помогает боту работать и развиваться 🙏"
    ),
    "donate_ask": "✍️ Отправь число — сколько звёзд ⭐ хочешь подарить (от {min} до {max}).",
    "donate_bad": "🤔 Нужно целое число от {min} до {max}. Попробуй ещё раз.",
    "donate_title": "💛 Поддержка проекта",
    "donate_desc": "Добровольный взнос на развитие бота. Спасибо!",
    "donate_thanks": "💛 <b>Искренне благодарим за поддержку!</b> Ты помогаешь боту становиться лучше.",
    "p_prepare": "🔎 Анализирую ссылку…",
    "p_queue": "🕐 Ты в очереди — сейчас я обрабатываю другие запросы. Это ненадолго!",
    "p_cached": "⚡ Этот файл у меня уже есть — отправляю мгновенно!",
    "p_dl": "⏳ Загрузка: [{bar}] {p}%",
    "p_conv": "🔄 Конвертация: [{bar}] {p}%",
    "p_send": "📤 Отправляю файл: [{bar}] 100%",
    "done": "✅ <b>Готово!</b> Наслаждайся 🎉\n{tail}",
    "tail_prem": "💎 Твой премиум действует до <b>{until}</b>",
    "tail_free": "🎁 Сегодня осталось: <b>{daily} из {limit}</b>",
    "tail_bonus": "  •  ➕ бонусных: <b>{bonus}</b>",
    "caption_via": "✨ Скачано через @{bot}",
    "busy": "⏳ Я ещё работаю над твоим предыдущим файлом. Подожди минутку 🙏",
    "unexpected": "😵 Ой, что-то пошло не так. Попробуй ещё раз чуть позже — лимит не списан.",
    "expired": "Эта ссылка устарела — отправь её ещё раз 🙂",
    "cancelled": "👌 Отменено. Присылай новую ссылку, когда захочешь!",
    "fmt_choose": "▶️ Нашёл ссылку на YouTube! Что скачиваем?",
    "search_wait": "🔎 Ищу «{q}»…",
    "search_results": "🎵 Вот что я нашёл по запросу <b>{q}</b>.\nВыбери трек 👇",
    "search_none": "😕 Ничего не нашёл. Попробуй другое название или вставь ссылку.",
    "search_short": "🤔 Напиши название песни (хотя бы 2 символа) или вставь ссылку.",
    "search_slow": "⏳ Не так быстро 🙂 Подожди секунду и попробуй снова.",
    "cut_prompt": (
        "✂️ <b>Обрезка / GIF</b>\n\n"
        "Отправь промежуток времени, например:\n"
        "<code>0:30-1:15</code> — видео\n"
        "<code>0:30-1:15 mp3</code> — аудио\n"
        "<code>0:05-0:12 gif</code> — GIF (до {gif} с)\n\n"
        "Максимум для видео и аудио — {max} с."
    ),
    "cut_bad": "🤔 Не понял промежуток. Формат: <code>0:30-1:15</code> (в конце можно добавить mp3 или gif).",
    "col_found": "📃 Нашёл треков: {n} — качаю по очереди…",
    "col_label": "📃 Трек {i} из {n}",
    "col_done": "✅ <b>Готово!</b> Отправлено треков: <b>{ok}</b> из {n}",
    "lang_choose": "🌐 Обери мову / Choose language / Выбери язык",
    "lang_set": "✅ Язык изменён: Русский 🇷🇺",
    "paysupport": (
        "💬 <b>Вопросы по оплате</b>\n\n"
        "Если после оплаты звёздами премиум не активировался или случилась ошибка — напиши нам: {contact}\n"
        "Укажи свой ID (виден в /profile) и время платежа — мы всё быстро решим 🙌"
    ),
    "privacy": (
        "🔒 <b>Конфиденциальность и условия</b>\n\n"
        "<b>Что хранится:</b>\n"
        "• твой Telegram ID и язык интерфейса;\n"
        "• счётчики загрузок, бонусы, данные о приглашениях;\n"
        "• статус и срок Премиума и служебные записи о платежах Stars (ID платежа, сумма);\n"
        "• технический кеш файлов (идентификатор медиа и Telegram file_id) — без привязки к тебе.\n\n"
        "<b>Чего мы не делаем:</b>\n"
        "• не храним в базе ссылки и поисковые запросы, которые ты отправляешь;\n"
        "• не продаём и не передаём твои данные третьим лицам;\n"
        "• не видим данных твоей карты — оплата проходит через Telegram.\n\n"
        "<b>Файлы:</b> временные файлы удаляются сразу после отправки.\n\n"
        "<b>Условия:</b> бот предназначен для личного использования. Ты сам отвечаешь за то, "
        "что скачиваешь, и за соблюдение авторских прав.\n\n"
        "<b>Удаление данных:</b> напиши {contact} — и мы удалим твои данные."
    ),
    "e_block": (
        "🤖 YouTube временно блокирует сервер бота. Попробуй позже "
        "(владелец бота может добавить cookies или прокси)."
    ),
    "e_private": "🔒 Это приватное видео — доступа к нему у меня нет.",
    "e_age": "🔞 Это видео с возрастным ограничением, скачать его не получится.",
    "e_unavailable": "🫥 Это видео недоступно: его удалили или закрыли в регионе.",
    "e_unsupported": "🤔 Не узнал эту ссылку. Проверь, что она ведёт на конкретное видео или трек.",
    "e_rate": "🚦 Слишком много запросов к сервису. Подожди минутку и попробуй снова.",
    "e_generic": "😕 Не удалось скачать. Проверь ссылку или попробуй чуть позже.",
    "e_spotify_type": "🟢 Эту ссылку Spotify я не распознал. Отправь ссылку на трек, альбом или плейлист.",
    "e_spotify_read": "🟢 Не удалось прочитать данные из Spotify. Попробуй другую ссылку.",
    "e_spotify_open": "🟢 Не удалось открыть короткую ссылку Spotify.",
    "e_spotify_down": "🟢 Spotify сейчас не отвечает. Попробуй чуть позже.",
    "e_spotify_keys": "🟢 Альбомы и плейлисты Spotify ещё не настроены администратором бота.",
    "e_notfound": "🔍 Не удалось найти этот трек на YouTube. Попробуй другой.",
    "e_playlist": "📃 Плейлисты YouTube и другие подборки не поддерживаются — отправь ссылку на одно видео или трек.",
    "e_live": "🔴 Это прямая трансляция — скачать её невозможно.",
    "e_long": "⏱ Это слишком долго: максимум {minutes} мин (иначе файл не влезет в лимит Telegram).",
    "e_toobig": "📦 Файл слишком большой для Telegram (лимит ботов — 50 МБ). Попробуй качество ниже, видео покороче или MP3 🎵",
    "e_nofile": "😕 Файл не удалось создать. Попробуй другую ссылку.",
    "e_cut_range": "✂️ Начало фрагмента — после конца видео. Проверь тайм-коды.",
    "e_cut_long": "✂️ Фрагмент слишком длинный: максимум {seconds} с.",
    "e_search": "🔍 Поиск временно недоступен. Попробуй позже или вставь ссылку.",
}

EN = {
    "b_download": "📥 Download media",
    "b_premium": "💎 Premium / Plans",
    "b_profile": "👤 My profile (limits)",
    "b_help": "🤝 Help",
    "b_invite": "🎁 Invite friends",
    "b_lang": "🌐 Language",
    "b_back": "⬅️ Back to menu",
    "lifetime": "forever ♾",
    "b_open_private": "💬 Open the bot",
    "group_hint": "👋 I download video and music!\nSend a link here or use <code>/dl link or title</code>.\nProfile, plans and settings are in the private chat 👇",
    "group_usage": "ℹ️ Usage: <code>/dl link</code> or <code>/dl song name</code>",
    "group_paywall": "🥲 Your free downloads are over.\nOpen the bot in a private chat — you can get unlimited access or bonuses there.",
    "group_spotify": "🟢 Spotify albums and playlists are available only in the private chat with the bot.",
    "b_cancel": "✖️ Cancel",
    "b_audio": "🎵 Audio (MP3)",
    "b_cut": "✂️ Trim / GIF 💎",
    "b_share": "📤 Share the bot → +{n} download",
    "b_donate": "💛 Support the project",
    "b_other": "✍️ Other amount",
    "b_promo": "🔥 PROMO: {days} day(s) for {price} ⭐",
    "promo_tail": "Grab it while it lasts 👇",
    "promo_offer": "Unlimited for {days} day(s) for just <b>{price} ⭐</b>",
    "welcome": (
        "👋 Hi, <b>{name}</b>!\n\n"
        "I'm your pocket media converter 🎧🎬\n"
        "Send a link or just type a song name — I'll do the rest:\n\n"
        "▶️ <b>YouTube</b> — video (MP4) or audio (MP3)\n"
        "🎵 <b>TikTok</b> — video without watermarks\n"
        "☁️ <b>SoundCloud</b> and 🟢 <b>Spotify</b> — tracks as MP3\n"
        "📸 <b>Instagram, X (Twitter), Pinterest, Facebook</b> — video\n"
        "🔎 <b>Search</b> — type e.g. “Imagine Dragons Believer” and pick a track\n\n"
        "🎁 You get <b>{limit} free downloads</b> every day. Want more? Try 💎 Premium.\n\n"
        "Pick what's next 👇"
    ),
    "menu_title": "🏠 <b>Main menu</b>\nWhat shall we do?",
    "download_hint": (
        "📥 <b>Send a link or a title!</b>\n\n"
        "• Paste a link from YouTube, TikTok, SoundCloud, Spotify, Instagram, X, Pinterest or Facebook\n"
        "• Or just type a song name — I'll search and offer options ✨"
    ),
    "unsupported": (
        "🙈 I can't handle this link yet.\n"
        "Supported: <b>YouTube, TikTok, SoundCloud, Spotify, Instagram, X, Pinterest, Facebook</b>."
    ),
    "help": (
        "🤝 <b>Help</b>\n\n"
        "<b>How to use:</b>\n"
        "1️⃣ Send a video/track link — or type a song name\n"
        "2️⃣ For YouTube, pick a quality or MP3\n"
        "3️⃣ Get your file 🎉\n\n"
        "<b>Limits:</b>\n"
        "🎁 {limit} free downloads per day (reset at midnight)\n"
        "➕ Bonus downloads — for inviting friends and sharing the bot\n"
        "💎 Premium — unlimited, 1080p, clip trimming, GIFs, Spotify albums and playlists\n"
        "📦 Max file size — 50 MB (Telegram limit for bots)\n\n"
        "<b>Commands:</b>\n"
        "/menu — main menu\n"
        "/profile — profile and limits\n"
        "/premium — plans\n"
        "/invite — invite friends\n"
        "/donate — support the project\n"
        "/lang — change language\n"
        "/privacy — privacy and terms\n"
        "/paysupport — payment questions\n\n"
        "Questions? Write to: {contact}"
    ),
    "profile_prem": (
        "👤 <b>Profile: {name}</b>\n\n"
        "💎 Plan: <b>Premium</b>\n"
        "♾ Unlimited downloads\n"
        "⏳ Valid until: <b>{until}</b>"
    ),
    "profile_free": (
        "👤 <b>Profile: {name}</b>\n\n"
        "🆓 Plan: <b>Free</b>\n"
        "🎁 Left today: <b>{daily} of {limit}</b>\n"
        "➕ Bonus downloads: <b>{bonus}</b>\n"
        "🕛 Daily limit resets in {reset}\n"
        "🤝 Friends invited: <b>{refs}</b>"
    ),
    "hm": "{h}h {m}m",
    "premium_text": (
        "💎 <b>Premium — download without limits!</b>\n\n"
        "{lines}\n\n"
        "✨ Premium includes: unlimited downloads, 1080p, clip trimming and GIFs, "
        "Spotify albums and playlists.\n\n"
        "Pay with Telegram Stars in two taps without leaving the chat. "
        "Premium turns on instantly. If it's already active, a new plan extends it."
    ),
    "paywall": (
        "<b>Your free downloads for today are over</b> 🥲\n"
        "Support the project or unlock unlimited!\n\n"
        "Or wait {reset} — the limit will reset by itself 🕛"
    ),
    "paywall_share": "📤 You can also share the bot with a friend and get <b>+{n}</b> download (once a day).",
    "promo_banner": "🔥 <b>Special offer!</b>\n{offer} — valid until {until}.",
    "promo_closed": "😕 This promo is no longer available or you have already used it.",
    "plan_day": "🌟 1 day unlimited",
    "plan_week": "⭐ 1 week unlimited",
    "plan_month": "👑 1 month unlimited",
    "plan_quarter": "🏆 3 months unlimited",
    "plan_promo": "🔥 Promo: unlimited, {days} day(s)",
    "plan_desc": "Unlimited downloads for {days} day(s): 1080p, trimming, GIFs, Spotify playlists",
    "premium_only": (
        "💎 This feature is available in <b>Premium</b>.\n"
        "Unlock unlimited and all the extras — pick a plan 👇"
    ),
    "pre_fail": "Something went wrong. Please try again 🙏",
    "paid_thanks": (
        "🎉 <b>Thank you for your support!</b> 💛\n\n"
        "Premium activated: <b>{plan}</b>\n"
        "⏳ Valid until: <b>{until}</b>\n\n"
        "Now download as much as you like — just send links 🚀"
    ),
    "paid_unknown": "😬 Payment received, but the plan wasn't recognized. Contact {contact} — we'll fix it!",
    "invite": (
        "🎁 <b>Invite friends — get downloads!</b>\n\n"
        "For every friend who starts the bot for the first time via your link, "
        "you both get <b>+{bonus}</b> downloads.\n\n"
        "🔗 Your link:\n<code>{link}</code>\n\n"
        "Friends invited: <b>{count}</b>"
    ),
    "ref_new": "🎁 You joined via an invitation — you got <b>+{bonus}</b> free downloads!",
    "ref_reward": "🎉 Your friend joined via your link — you got <b>+{bonus}</b> downloads!",
    "share_title": "📤 Share the bot",
    "share_desc": "Send it to friends and get +{n} download",
    "share_message": (
        "🎧 Found a great bot: it downloads video and music from YouTube, TikTok, SoundCloud, "
        "Spotify and more — free every day!\n\n👉 {link}"
    ),
    "share_open": "🚀 Open the bot",
    "share_rewarded": "🎁 Thanks for sharing! You got <b>+{n}</b> download.",
    "donate_menu": (
        "💛 <b>Support the project</b>\n\n"
        "Pick an amount or enter your own ({min}–{max} ⭐). "
        "It's voluntary and helps the bot run and grow 🙏"
    ),
    "donate_ask": "✍️ Send a number — how many stars ⭐ you'd like to give ({min}–{max}).",
    "donate_bad": "🤔 I need a whole number from {min} to {max}. Try again.",
    "donate_title": "💛 Project support",
    "donate_desc": "A voluntary contribution to the bot's development. Thank you!",
    "donate_thanks": "💛 <b>Thank you so much for your support!</b> You help the bot get better.",
    "p_prepare": "🔎 Analyzing the link…",
    "p_queue": "🕐 You're in the queue — I'm processing other requests. It won't take long!",
    "p_cached": "⚡ I already have this file — sending instantly!",
    "p_dl": "⏳ Downloading: [{bar}] {p}%",
    "p_conv": "🔄 Converting: [{bar}] {p}%",
    "p_send": "📤 Sending file: [{bar}] 100%",
    "done": "✅ <b>Done!</b> Enjoy 🎉\n{tail}",
    "tail_prem": "💎 Your premium is valid until <b>{until}</b>",
    "tail_free": "🎁 Left today: <b>{daily} of {limit}</b>",
    "tail_bonus": "  •  ➕ bonus: <b>{bonus}</b>",
    "caption_via": "✨ Downloaded via @{bot}",
    "busy": "⏳ I'm still working on your previous file. Please wait a moment 🙏",
    "unexpected": "😵 Oops, something went wrong. Try again a bit later — your limit wasn't used.",
    "expired": "This link has expired — please send it again 🙂",
    "cancelled": "👌 Cancelled. Send a new link whenever you like!",
    "fmt_choose": "▶️ Found a YouTube link! What shall we download?",
    "search_wait": "🔎 Searching “{q}”…",
    "search_results": "🎵 Here's what I found for <b>{q}</b>.\nPick a track 👇",
    "search_none": "😕 Nothing found. Try another title or paste a link.",
    "search_short": "🤔 Type a song name (at least 2 characters) or paste a link.",
    "search_slow": "⏳ Not so fast 🙂 Wait a second and try again.",
    "cut_prompt": (
        "✂️ <b>Trim / GIF</b>\n\n"
        "Send a time range, for example:\n"
        "<code>0:30-1:15</code> — video\n"
        "<code>0:30-1:15 mp3</code> — audio\n"
        "<code>0:05-0:12 gif</code> — GIF (up to {gif} s)\n\n"
        "Maximum for video and audio — {max} s."
    ),
    "cut_bad": "🤔 I didn't get the range. Format: <code>0:30-1:15</code> (you can add mp3 or gif at the end).",
    "col_found": "📃 Found {n} track(s) — downloading one by one…",
    "col_label": "📃 Track {i} of {n}",
    "col_done": "✅ <b>Done!</b> Tracks sent: <b>{ok}</b> of {n}",
    "lang_choose": "🌐 Обери мову / Choose language / Выбери язык",
    "lang_set": "✅ Language changed: English 🇬🇧",
    "paysupport": (
        "💬 <b>Payment questions</b>\n\n"
        "If premium didn't activate after paying with Stars or something went wrong, write to us: {contact}\n"
        "Include your ID (see /profile) and the payment time — we'll sort it out quickly 🙌"
    ),
    "privacy": (
        "🔒 <b>Privacy and terms</b>\n\n"
        "<b>What we store:</b>\n"
        "• your Telegram ID and interface language;\n"
        "• download counters, bonuses, invitation data;\n"
        "• Premium status and expiry, and service records of Stars payments (payment ID, amount);\n"
        "• a technical file cache (media ID and Telegram file_id) — not linked to you.\n\n"
        "<b>What we don't do:</b>\n"
        "• we don't keep the links or search queries you send in our database;\n"
        "• we don't sell or share your data with third parties;\n"
        "• we can't see your card details — payment goes through Telegram.\n\n"
        "<b>Files:</b> temporary files are deleted right after sending.\n\n"
        "<b>Terms:</b> the bot is for personal use. You are responsible for what you download "
        "and for respecting copyright.\n\n"
        "<b>Data deletion:</b> write to {contact} and we'll delete your data."
    ),
    "e_block": (
        "🤖 YouTube is temporarily blocking the bot's server. Try again later "
        "(the owner can add cookies or a proxy)."
    ),
    "e_private": "🔒 This video is private — I can't access it.",
    "e_age": "🔞 This video is age-restricted and can't be downloaded.",
    "e_unavailable": "🫥 This video is unavailable: it was removed or blocked in the region.",
    "e_unsupported": "🤔 I don't recognize this link. Make sure it points to a specific video or track.",
    "e_rate": "🚦 Too many requests to the service. Wait a minute and try again.",
    "e_generic": "😕 Couldn't download. Check the link or try again a bit later.",
    "e_spotify_type": "🟢 I didn't recognize this Spotify link. Send a track, album or playlist link.",
    "e_spotify_read": "🟢 Couldn't read the data from Spotify. Try another link.",
    "e_spotify_open": "🟢 Couldn't open the short Spotify link.",
    "e_spotify_down": "🟢 Spotify isn't responding right now. Try again a bit later.",
    "e_spotify_keys": "🟢 Spotify albums and playlists aren't set up by the bot admin yet.",
    "e_notfound": "🔍 Couldn't find this track on YouTube. Try another one.",
    "e_playlist": "📃 YouTube playlists and other collections aren't supported — send a single video or track link.",
    "e_live": "🔴 This is a live stream — it can't be downloaded.",
    "e_long": "⏱ This is too long: max {minutes} min (otherwise the file won't fit Telegram's limit).",
    "e_toobig": "📦 The file is too large for Telegram (bot limit is 50 MB). Try lower quality, a shorter video or MP3 🎵",
    "e_nofile": "😕 Couldn't create the file. Try another link.",
    "e_cut_range": "✂️ The clip starts after the video ends. Check the timestamps.",
    "e_cut_long": "✂️ The clip is too long: max {seconds} s.",
    "e_search": "🔍 Search is temporarily unavailable. Try later or paste a link.",
}

TEXTS = {"uk": UK, "ru": RU, "en": EN}


def tr(lang: str, key: str, **kw) -> str:
    text = TEXTS.get(lang, UK).get(key) or UK[key]
    return text.format(**kw) if kw else text
