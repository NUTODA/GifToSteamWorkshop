from __future__ import annotations

from aiogram import Bot, Dispatcher

from .config import DEFAULT_LOCALE

SUPPORTED_LOCALES = {"ru", "en", "uk"}
PREFERRED_LOCALE_KEY = "preferred_locale"

TRANSLATIONS: dict[str, dict[str, str]] = {
    "ru": {
        "button_help": "📖 Справка",
        "button_about_showcase": "🎮 Что такое Витрина?",
        "button_language": "🌐 Язык",
        "language_name_ru": "Русский",
        "language_name_en": "English",
        "language_name_uk": "Українська",
        "language_choose_title": "🌐 <b>Выбор языка</b>\n\nВыбери язык интерфейса бота:",
        "language_changed": "✅ <b>Язык интерфейса изменён:</b> {language_name}",
        "language_changed_short": "Язык сохранён",
        "callback_error": "Ошибка при обработке кнопки.",
        "welcome_text": (
            "🎬 <b>Steam Showcase Bot</b>\n\n"
            "Привет, {first_name}! 👋\n\n"
            "Я автоматически подготовлю твою анимацию для <b>Витрины Steam</b>.\n\n"
            "<b>📌 Как это работает:</b>\n"
            "Витрина отображает GIF через 5 горизонтальных слотов по <code>150 px</code>. Я:\n\n"
            "1️⃣  Масштабирую видео до <code>750 px</code>\n"
            "2️⃣  Нарезаю на <b>5 частей</b> по <code>150 px</code>\n"
            "3️⃣  Конвертирую каждую часть в <code>.gif</code>\n"
            "4️⃣  Упаковываю всё в <b>ZIP-архив</b>\n\n"
            "🚀 <b>Просто отправь GIF или MP4-видео — остальное сделаю я!</b>"
        ),
        "help_text": (
            "❓ <b>Справка — Steam Showcase Bot</b>\n\n"
            "<b>Поддерживаемые форматы:</b>\n"
            "• GIF-анимация (Telegram конвертирует её в MP4 автоматически)\n"
            "• MP4-видео\n"
            "• Файлы <code>.gif</code>, <code>.mp4</code>, <code>.webm</code> как документ\n\n"
            "<b>Как использовать:</b>\n"
            "1. Отправь GIF или видео прямо в этот чат\n"
            "2. Дождись обработки (обычно 10-60 сек)\n"
            "3. Получи ZIP с 5 готовыми GIF-файлами\n"
            "4. Загрузи <code>part1.gif</code>...<code>part5.gif</code>\n"
            "   в слоты Витрины на странице своего профиля Steam\n\n"
            "<b>Команды:</b>\n"
            "/start - главное меню\n"
            "/help - эта справка\n"
            "/lang - выбор языка\n\n"
            "<b>⚠️ Частые вопросы:</b>\n"
            "• <i>\"Неподдерживаемый формат\"</i> - отправь файл как GIF-анимацию, "
            "а не как документ\n"
            "• <i>\"Архив слишком большой\"</i> - файл создан на сервере, но превысил "
            "лимит отправки {limit_mb} MB\n"
            "• <i>\"FFmpeg не найден\"</i> - обратитесь к администратору сервера"
        ),
        "about_showcase_text": (
            "🎮 <b>Витрина Steam (Steam Showcase)</b>\n\n"
            "Витрина - раздел профиля Steam, где можно разместить анимированные GIF-картинки. "
            "Она состоит из <b>5 горизонтальных слотов</b>, каждый шириной <code>150 px</code>.\n\n"
            "Чтобы анимация выглядела как единое целое, нужно:\n"
            "1. Взять видео шириной <code>750 px</code> (5 x 150 px)\n"
            "2. Разрезать на 5 равных частей\n"
            "3. Загрузить каждую часть в соответствующий слот\n\n"
            "<b>Именно это я делаю автоматически!</b> 🎉\n\n"
            "Управление Витриной:\n"
            "<code>steamcommunity.com -> Профиль -> Редактировать -> Витрина</code>"
        ),
        "status_step_scale": "Масштабирование до <code>750 px</code>",
        "status_step_slice": "Нарезка на 5 частей",
        "status_step_gifs": "Создание GIF-файлов",
        "status_step_zip": "Архивирование в ZIP",
        "status_header_failed": "❌ <b>Ошибка при обработке</b>{err_detail}",
        "status_header_done": "✅ <b>Готово! Отправляю архив...</b>",
        "status_header_start": "⏳ <b>Начинаю обработку...</b>",
        "status_header_progress": "⏳ <b>Идёт обработка...</b>",
        "status_file_received": (
            "📥 <b>Файл получен:</b> <code>{filename}</code>{size_str}\n\n"
            "{header}\n\n"
            "{steps_block}"
        ),
        "media_stopping": (
            "⏳ <b>Бот завершает работу</b>\n\n"
            "Сейчас новые файлы не принимаются. Повтори отправку через минуту."
        ),
        "media_file_too_big": (
            "⚠️ <b>Файл слишком большой</b>\n\n"
            "Размер: <code>{size_mb} MB</code> (максимум: <code>{max_mb} MB</code>)\n\n"
            "Попробуй отправить файл поменьше."
        ),
        "media_downloading": "⬇️ <b>Скачиваю файл...</b>",
        "media_unsupported_format": (
            "⚠️ <b>Неподдерживаемый формат</b>\n\n"
            "Файл: <code>{filename}</code> (<code>{mime}</code>)\n\n"
            "Отправь <b>GIF-анимацию</b> или <b>MP4-видео</b>."
        ),
        "media_file_not_found": (
            "📎 <b>Файл не найден</b>\n\n"
            "Пожалуйста, отправь GIF-анимацию или MP4-видео."
        ),
        "media_download_error": (
            "❌ <b>Ошибка при скачивании файла:</b>\n"
            "<code>{error}</code>"
        ),
        "throttling_wait": (
            "⏳ <b>Подожди немного</b>\n\n"
            "Следующий файл можно отправить через <code>{remaining}</code> сек."
        ),
        "processor_ffmpeg_missing": (
            "⚠️ <b>FFmpeg не найден</b>\n\n"
            "Обработка невозможна. Попросите администратора установить "
            "<code>ffmpeg</code> и добавить его в PATH или задать "
            "переменную окружения <code>FFMPEG_BIN</code>."
        ),
        "processor_unsupported_format": (
            "⚠️ <b>Неподдерживаемый формат</b>\n\n"
            "Получен файл <code>{filename}</code>.\n\n"
            "Бот принимает только <b>MP4-файлы</b>. Telegram автоматически "
            "конвертирует GIF-анимации в MP4 - попробуй отправить файл "
            "как GIF-анимацию, а не как документ."
        ),
        "processor_gif_error": (
            "❌ <b>Ошибка при создании GIF:</b>\n"
            "<code>{error}</code>"
        ),
        "processor_scale_error": (
            "❌ <b>Ошибка при масштабировании:</b>\n"
            "<code>{error}</code>"
        ),
        "processor_archive_too_big": (
            "📦 <b>Архив готов, но слишком большой для отправки</b>\n\n"
            "Размер: <code>{size_mb} MB</code> (лимит: <code>{max_mb} MB</code>)\n\n"
            "Архив сохранён на сервере и доступен администратору."
        ),
        "processor_archive_caption": (
            "🎬 <b>Архив готов!</b>\n\n"
            "📦 Размер: <code>{size_mb} MB</code>\n"
            "🗂 Файлов: <code>5 GIF</code> "
            "(<code>part1.gif</code>...<code>part5.gif</code>)\n\n"
            "<b>📋 Как загрузить в Steam:</b>\n"
            "Профиль -> Редактировать профиль -> Витрина\n"
            "-> Выбери слот -> Загрузи каждый <code>partN.gif</code>"
        ),
        "processor_send_failed_network": (
            "⚠️ <b>Не удалось отправить архив</b>\n\n"
            "Превышено число попыток из-за сетевых ошибок. "
            "Архив сохранён на сервере."
        ),
        "processor_send_failed_generic": (
            "⚠️ <b>Не удалось отправить архив</b>\n\n"
            "Произошла ошибка при отправке. "
            "Архив сохранён на сервере."
        ),
    },
    "en": {
        "button_help": "📖 Help",
        "button_about_showcase": "🎮 What is Showcase?",
        "button_language": "🌐 Language",
        "language_name_ru": "Russian",
        "language_name_en": "English",
        "language_name_uk": "Ukrainian",
        "language_choose_title": "🌐 <b>Language selection</b>\n\nChoose bot interface language:",
        "language_changed": "✅ <b>Interface language updated:</b> {language_name}",
        "language_changed_short": "Language saved",
        "callback_error": "Failed to process button.",
        "welcome_text": (
            "🎬 <b>Steam Showcase Bot</b>\n\n"
            "Hi, {first_name}! 👋\n\n"
            "I will automatically prepare your animation for the <b>Steam Showcase</b>.\n\n"
            "<b>📌 How it works:</b>\n"
            "Showcase displays GIFs using 5 horizontal slots of <code>150 px</code> each. I will:\n\n"
            "1️⃣  Resize video to <code>750 px</code>\n"
            "2️⃣  Split it into <b>5 parts</b> of <code>150 px</code>\n"
            "3️⃣  Convert each part to <code>.gif</code>\n"
            "4️⃣  Pack everything into a <b>ZIP archive</b>\n\n"
            "🚀 <b>Just send a GIF or MP4 video - I will do the rest!</b>"
        ),
        "help_text": (
            "❓ <b>Help - Steam Showcase Bot</b>\n\n"
            "<b>Supported formats:</b>\n"
            "• GIF animation (Telegram converts it to MP4 automatically)\n"
            "• MP4 video\n"
            "• <code>.gif</code>, <code>.mp4</code>, <code>.webm</code> files as documents\n\n"
            "<b>How to use:</b>\n"
            "1. Send a GIF or video to this chat\n"
            "2. Wait for processing (usually 10-60 sec)\n"
            "3. Get a ZIP with 5 ready GIF files\n"
            "4. Upload <code>part1.gif</code>...<code>part5.gif</code>\n"
            "   to Showcase slots on your Steam profile page\n\n"
            "<b>Commands:</b>\n"
            "/start - main menu\n"
            "/help - this help\n"
            "/lang - choose language\n\n"
            "<b>⚠️ FAQ:</b>\n"
            "• <i>\"Unsupported format\"</i> - send it as GIF animation, not as document\n"
            "• <i>\"Archive is too large\"</i> - archive is created on server but exceeds "
            "the {limit_mb} MB sending limit\n"
            "• <i>\"FFmpeg not found\"</i> - contact the server administrator"
        ),
        "about_showcase_text": (
            "🎮 <b>Steam Showcase</b>\n\n"
            "Showcase is a Steam profile section where you can place animated GIFs. "
            "It has <b>5 horizontal slots</b>, each <code>150 px</code> wide.\n\n"
            "To make animation look like one whole image, you need to:\n"
            "1. Use a <code>750 px</code> wide video (5 x 150 px)\n"
            "2. Split it into 5 equal parts\n"
            "3. Upload each part into its slot\n\n"
            "<b>That is exactly what I automate!</b> 🎉\n\n"
            "Showcase settings:\n"
            "<code>steamcommunity.com -> Profile -> Edit Profile -> Showcase</code>"
        ),
        "status_step_scale": "Resizing to <code>750 px</code>",
        "status_step_slice": "Splitting into 5 parts",
        "status_step_gifs": "Creating GIF files",
        "status_step_zip": "Packing ZIP archive",
        "status_header_failed": "❌ <b>Processing error</b>{err_detail}",
        "status_header_done": "✅ <b>Done! Sending archive...</b>",
        "status_header_start": "⏳ <b>Starting processing...</b>",
        "status_header_progress": "⏳ <b>Processing in progress...</b>",
        "status_file_received": (
            "📥 <b>File received:</b> <code>{filename}</code>{size_str}\n\n"
            "{header}\n\n"
            "{steps_block}"
        ),
        "media_stopping": (
            "⏳ <b>Bot is shutting down</b>\n\n"
            "New files are temporarily unavailable. Please try again in a minute."
        ),
        "media_file_too_big": (
            "⚠️ <b>File is too large</b>\n\n"
            "Size: <code>{size_mb} MB</code> (max: <code>{max_mb} MB</code>)\n\n"
            "Please send a smaller file."
        ),
        "media_downloading": "⬇️ <b>Downloading file...</b>",
        "media_unsupported_format": (
            "⚠️ <b>Unsupported format</b>\n\n"
            "File: <code>{filename}</code> (<code>{mime}</code>)\n\n"
            "Send a <b>GIF animation</b> or <b>MP4 video</b>."
        ),
        "media_file_not_found": (
            "📎 <b>File not found</b>\n\n"
            "Please send a GIF animation or MP4 video."
        ),
        "media_download_error": (
            "❌ <b>File download error:</b>\n"
            "<code>{error}</code>"
        ),
        "throttling_wait": (
            "⏳ <b>Please wait a bit</b>\n\n"
            "You can send the next file in <code>{remaining}</code> sec."
        ),
        "processor_ffmpeg_missing": (
            "⚠️ <b>FFmpeg not found</b>\n\n"
            "Processing is unavailable. Ask the administrator to install "
            "<code>ffmpeg</code> and add it to PATH or set "
            "<code>FFMPEG_BIN</code> environment variable."
        ),
        "processor_unsupported_format": (
            "⚠️ <b>Unsupported format</b>\n\n"
            "Received file <code>{filename}</code>.\n\n"
            "The bot accepts only <b>MP4 files</b>. Telegram automatically "
            "converts GIF animations to MP4 - try sending it as GIF animation "
            "instead of document."
        ),
        "processor_gif_error": (
            "❌ <b>GIF creation error:</b>\n"
            "<code>{error}</code>"
        ),
        "processor_scale_error": (
            "❌ <b>Resize error:</b>\n"
            "<code>{error}</code>"
        ),
        "processor_archive_too_big": (
            "📦 <b>Archive is ready but too large to send</b>\n\n"
            "Size: <code>{size_mb} MB</code> (limit: <code>{max_mb} MB</code>)\n\n"
            "Archive is saved on the server and available to administrator."
        ),
        "processor_archive_caption": (
            "🎬 <b>Archive is ready!</b>\n\n"
            "📦 Size: <code>{size_mb} MB</code>\n"
            "🗂 Files: <code>5 GIF</code> "
            "(<code>part1.gif</code>...<code>part5.gif</code>)\n\n"
            "<b>📋 How to upload to Steam:</b>\n"
            "Profile -> Edit Profile -> Showcase\n"
            "-> Choose slot -> Upload each <code>partN.gif</code>"
        ),
        "processor_send_failed_network": (
            "⚠️ <b>Failed to send archive</b>\n\n"
            "Retry limit exceeded due to network errors. "
            "Archive was saved on server."
        ),
        "processor_send_failed_generic": (
            "⚠️ <b>Failed to send archive</b>\n\n"
            "An error occurred while sending. "
            "Archive was saved on server."
        ),
    },
    "uk": {
        "button_help": "📖 Довідка",
        "button_about_showcase": "🎮 Що таке Вітрина?",
        "button_language": "🌐 Мова",
        "language_name_ru": "Російська",
        "language_name_en": "Англійська",
        "language_name_uk": "Українська",
        "language_choose_title": "🌐 <b>Вибір мови</b>\n\nОберіть мову інтерфейсу бота:",
        "language_changed": "✅ <b>Мову інтерфейсу змінено:</b> {language_name}",
        "language_changed_short": "Мову збережено",
        "callback_error": "Помилка обробки кнопки.",
        "welcome_text": (
            "🎬 <b>Steam Showcase Bot</b>\n\n"
            "Привіт, {first_name}! 👋\n\n"
            "Я автоматично підготую твою анімацію для <b>Вітрини Steam</b>.\n\n"
            "<b>📌 Як це працює:</b>\n"
            "Вітрина показує GIF через 5 горизонтальних слотів по <code>150 px</code>. Я:\n\n"
            "1️⃣  Масштабую відео до <code>750 px</code>\n"
            "2️⃣  Розріжу на <b>5 частин</b> по <code>150 px</code>\n"
            "3️⃣  Конвертую кожну частину в <code>.gif</code>\n"
            "4️⃣  Запакую все в <b>ZIP-архів</b>\n\n"
            "🚀 <b>Просто надішли GIF або MP4-відео — решту зроблю я!</b>"
        ),
        "help_text": (
            "❓ <b>Довідка — Steam Showcase Bot</b>\n\n"
            "<b>Підтримувані формати:</b>\n"
            "• GIF-анімація (Telegram автоматично конвертує її в MP4)\n"
            "• MP4-відео\n"
            "• Файли <code>.gif</code>, <code>.mp4</code>, <code>.webm</code> як документ\n\n"
            "<b>Як використовувати:</b>\n"
            "1. Надішли GIF або відео в цей чат\n"
            "2. Дочекайся обробки (зазвичай 10-60 сек)\n"
            "3. Отримай ZIP з 5 готовими GIF-файлами\n"
            "4. Завантаж <code>part1.gif</code>...<code>part5.gif</code>\n"
            "   у слоти Вітрини на сторінці профілю Steam\n\n"
            "<b>Команди:</b>\n"
            "/start - головне меню\n"
            "/help - ця довідка\n"
            "/lang - вибір мови\n\n"
            "<b>⚠️ Часті питання:</b>\n"
            "• <i>\"Непідтримуваний формат\"</i> - надішли файл як GIF-анімацію, "
            "а не як документ\n"
            "• <i>\"Архів занадто великий\"</i> - файл створено на сервері, але він "
            "перевищив ліміт надсилання {limit_mb} MB\n"
            "• <i>\"FFmpeg не знайдено\"</i> - зверніться до адміністратора сервера"
        ),
        "about_showcase_text": (
            "🎮 <b>Вітрина Steam (Steam Showcase)</b>\n\n"
            "Вітрина - це розділ профілю Steam, де можна розмістити анімовані GIF. "
            "Вона має <b>5 горизонтальних слотів</b>, кожен шириною <code>150 px</code>.\n\n"
            "Щоб анімація виглядала як єдине ціле, потрібно:\n"
            "1. Взяти відео шириною <code>750 px</code> (5 x 150 px)\n"
            "2. Розрізати на 5 рівних частин\n"
            "3. Завантажити кожну частину у відповідний слот\n\n"
            "<b>Саме це я роблю автоматично!</b> 🎉\n\n"
            "Керування Вітриною:\n"
            "<code>steamcommunity.com -> Профіль -> Редагувати -> Вітрина</code>"
        ),
        "status_step_scale": "Масштабування до <code>750 px</code>",
        "status_step_slice": "Нарізка на 5 частин",
        "status_step_gifs": "Створення GIF-файлів",
        "status_step_zip": "Архівування в ZIP",
        "status_header_failed": "❌ <b>Помилка обробки</b>{err_detail}",
        "status_header_done": "✅ <b>Готово! Надсилаю архів...</b>",
        "status_header_start": "⏳ <b>Починаю обробку...</b>",
        "status_header_progress": "⏳ <b>Триває обробка...</b>",
        "status_file_received": (
            "📥 <b>Файл отримано:</b> <code>{filename}</code>{size_str}\n\n"
            "{header}\n\n"
            "{steps_block}"
        ),
        "media_stopping": (
            "⏳ <b>Бот завершує роботу</b>\n\n"
            "Зараз нові файли тимчасово не приймаються. Спробуй ще раз за хвилину."
        ),
        "media_file_too_big": (
            "⚠️ <b>Файл занадто великий</b>\n\n"
            "Розмір: <code>{size_mb} MB</code> (максимум: <code>{max_mb} MB</code>)\n\n"
            "Спробуй надіслати менший файл."
        ),
        "media_downloading": "⬇️ <b>Завантажую файл...</b>",
        "media_unsupported_format": (
            "⚠️ <b>Непідтримуваний формат</b>\n\n"
            "Файл: <code>{filename}</code> (<code>{mime}</code>)\n\n"
            "Надішли <b>GIF-анімацію</b> або <b>MP4-відео</b>."
        ),
        "media_file_not_found": (
            "📎 <b>Файл не знайдено</b>\n\n"
            "Будь ласка, надішли GIF-анімацію або MP4-відео."
        ),
        "media_download_error": (
            "❌ <b>Помилка завантаження файлу:</b>\n"
            "<code>{error}</code>"
        ),
        "throttling_wait": (
            "⏳ <b>Трохи зачекай</b>\n\n"
            "Наступний файл можна надіслати через <code>{remaining}</code> сек."
        ),
        "processor_ffmpeg_missing": (
            "⚠️ <b>FFmpeg не знайдено</b>\n\n"
            "Обробка недоступна. Попросіть адміністратора встановити "
            "<code>ffmpeg</code> і додати його в PATH або задати "
            "змінну середовища <code>FFMPEG_BIN</code>."
        ),
        "processor_unsupported_format": (
            "⚠️ <b>Непідтримуваний формат</b>\n\n"
            "Отримано файл <code>{filename}</code>.\n\n"
            "Бот приймає тільки <b>MP4-файли</b>. Telegram автоматично "
            "конвертує GIF-анімації в MP4 - спробуй надіслати файл "
            "як GIF-анімацію, а не як документ."
        ),
        "processor_gif_error": (
            "❌ <b>Помилка створення GIF:</b>\n"
            "<code>{error}</code>"
        ),
        "processor_scale_error": (
            "❌ <b>Помилка масштабування:</b>\n"
            "<code>{error}</code>"
        ),
        "processor_archive_too_big": (
            "📦 <b>Архів готовий, але занадто великий для надсилання</b>\n\n"
            "Розмір: <code>{size_mb} MB</code> (ліміт: <code>{max_mb} MB</code>)\n\n"
            "Архів збережено на сервері й доступний адміністратору."
        ),
        "processor_archive_caption": (
            "🎬 <b>Архів готовий!</b>\n\n"
            "📦 Розмір: <code>{size_mb} MB</code>\n"
            "🗂 Файлів: <code>5 GIF</code> "
            "(<code>part1.gif</code>...<code>part5.gif</code>)\n\n"
            "<b>📋 Як завантажити в Steam:</b>\n"
            "Профіль -> Редагувати профіль -> Вітрина\n"
            "-> Обери слот -> Завантаж кожен <code>partN.gif</code>"
        ),
        "processor_send_failed_network": (
            "⚠️ <b>Не вдалося надіслати архів</b>\n\n"
            "Перевищено кількість спроб через мережеві помилки. "
            "Архів збережено на сервері."
        ),
        "processor_send_failed_generic": (
            "⚠️ <b>Не вдалося надіслати архів</b>\n\n"
            "Під час надсилання сталася помилка. "
            "Архів збережено на сервері."
        ),
    },
}


def _extract_lang_part(locale: str | None) -> str | None:
    if not locale:
        return None
    normalized = str(locale).strip().lower().replace("_", "-")
    if not normalized:
        return None
    return normalized.split("-", 1)[0]


def resolve_locale(stored_locale: str | None, telegram_locale: str | None = None) -> str:
    stored = _extract_lang_part(stored_locale)
    if stored in SUPPORTED_LOCALES:
        return stored
    tg = _extract_lang_part(telegram_locale)
    if tg in SUPPORTED_LOCALES:
        return tg
    return DEFAULT_LOCALE if DEFAULT_LOCALE in SUPPORTED_LOCALES else "ru"


def normalize_locale(locale: str | None) -> str:
    return resolve_locale(stored_locale=locale, telegram_locale=None)


async def get_user_locale(
    dispatcher: Dispatcher,
    bot: Bot,
    user_id: int | None,
    telegram_locale: str | None = None,
) -> str:
    if user_id is None:
        return resolve_locale(None, telegram_locale)
    try:
        state = dispatcher.fsm.get_context(bot=bot, chat_id=user_id, user_id=user_id)
        data = await state.get_data()
    except Exception:
        return resolve_locale(None, telegram_locale)
    return resolve_locale(data.get(PREFERRED_LOCALE_KEY), telegram_locale)


async def set_user_locale(dispatcher: Dispatcher, bot: Bot, user_id: int | None, locale: str | None) -> str:
    resolved = normalize_locale(locale)
    if user_id is None:
        return resolved
    try:
        state = dispatcher.fsm.get_context(bot=bot, chat_id=user_id, user_id=user_id)
        await state.update_data(**{PREFERRED_LOCALE_KEY: resolved})
    except Exception:
        return resolved
    return resolved


def locale_display_name(locale: str, target_locale: str) -> str:
    key = f"language_name_{normalize_locale(locale)}"
    return tr(key, target_locale)


def tr(key: str, locale: str | None = None, **kwargs) -> str:
    resolved_locale = normalize_locale(locale)
    template = TRANSLATIONS.get(resolved_locale, {}).get(key)
    if template is None:
        template = TRANSLATIONS.get("ru", {}).get(key, key)
    if kwargs:
        return template.format(**kwargs)
    return template
