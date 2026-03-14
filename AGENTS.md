# AGENTS.md — Инструкции для AI-агентов

Этот файл содержит полный контекст проекта, соглашения по разработке и руководство по внесению изменений для будущих AI-агентов.

---

## Краткое описание проекта

**GifToSteamWorkshop** — Telegram-бот на Python (aiogram 3.x), который принимает GIF или MP4-видео, масштабирует их до 750px в ширину, нарезает на 5 частей по 150px и конвертирует каждую часть в `.gif` для загрузки в слоты Витрины Steam. Результат отправляется пользователю как ZIP-архив.

---

## Структура кода

```
steam_showcase_bot/
├── __init__.py
├── __main__.py              ← точка входа: python -m steam_showcase_bot
├── bot.py                   ← создание Bot/Dispatcher, on_startup/on_shutdown, polling
├── config.py                ← чтение переменных окружения через python-dotenv
├── ffmpeg_utils.py          ← вся логика ffmpeg: resize, slice, gif, archive
├── texts.py                 ← текстовые шаблоны, inline-клавиатура, прогресс-статус
├── handlers/
│   ├── __init__.py          ← регистрация роутеров: register_routers(dp)
│   ├── commands.py          ← /start, /help (aiogram Router)
│   ├── callbacks.py         ← inline-кнопки (aiogram Router)
│   └── media.py             ← обработка медиафайлов (aiogram Router)
├── services/
│   ├── __init__.py
│   └── processor.py         ← ProcessingService: resize → slice → gif → zip → отправка
├── middlewares/
│   ├── __init__.py
│   └── throttling.py        ← ThrottlingMiddleware (rate limiting по пользователю)
├── requirements.txt         ← pip-зависимости
├── .env                     ← секреты (НЕ в git)
└── .env.example             ← шаблон конфига
```

Рабочие директории создаются автоматически при первом запуске:
- `steam_showcase_bot/gifs/` — оригинальные загрузки
- `steam_showcase_bot/prepared_gifs/` — ресайзнутые копии
- `steam_showcase_bot/sliced_gifs/` — нарезанные части + итоговый ZIP

---

## UI/UX архитектура

### Команды и хендлеры

| Хендлер | Файл | Триггер | Описание |
|---|---|---|---|
| `cmd_start` | `handlers/commands.py` | `/start` | Приветственное сообщение с inline-кнопками |
| `cmd_help` | `handlers/commands.py` | `/help` | Подробная справка |
| `handle_callback` | `handlers/callbacks.py` | Кнопки `help`, `about_showcase` | Ответ на нажатия inline-кнопок |
| `handle_file` | `handlers/media.py` | Медиафайл (animation/video/document) | Проверка размера + скачивание + запуск обработки |

### Прогресс-сообщение (живое обновление)

После получения файла бот создаёт **одно статус-сообщение** и редактирует его на каждом шаге — чат остаётся чистым.

**Шаги (константы в `texts.py`):**
```python
STEP_SCALE = 1   # Масштабирование до 750px
STEP_SLICE = 2   # Нарезка на 5 частей
STEP_GIFS  = 3   # Создание GIF-файлов
STEP_ZIP   = 4   # Архивирование в ZIP
STEP_DONE  = 5   # Готово
```

**Визуальные состояния иконок:**
- `▫️` — ожидание
- `🔄` — выполняется прямо сейчас
- `✅` — завершено
- `❌` — ошибка на этом шаге

**Функции для управления статусом (в `texts.py`):**
- `status_text(filename, size_mb, step, failed_at, error_msg)` — строит HTML-текст статуса
- `edit_status(msg, **kwargs)` — тихо редактирует сообщение (игнорирует ошибки)

**Хронология обновлений:**
```
⬇️ Скачиваю файл…                     ← создаётся при старте скачивания
📥 Файл получен: name.mp4 (X.X MB)    ← после скачивания, step=0
  ▫️ Масштабирование / ▫️ Нарезка / ...
  ↓ (фоновая задача через ProcessingService)
🔄 Масштабирование  step=1
✅ Масштабирование
🔄 Нарезка          step=2
✅ Всё готово!      step=5
  ↓
[Bot отправляет документ с caption]
```

### HTML-форматирование

Все сообщения используют `parse_mode='HTML'`. Специальные символы в пользовательских данных (имена файлов, сообщения об ошибках) экранируются через `esc()` (`html.escape()`) из `texts.py`.

### Inline-клавиатура /start

```python
welcome_markup()  →  [📖 Справка]  [🎮 Что такое Витрина?]
```
Callbacks: `'help'` → `help_text()`, `'about_showcase'` → `about_showcase_text()`

### Текстовые шаблоны (в `texts.py`)

| Функция | Содержимое |
|---|---|
| `welcome_text(first_name)` | Приветствие + объяснение работы + призыв к действию |
| `help_text()` | Форматы, инструкция, команды, FAQ |
| `about_showcase_text()` | Объяснение устройства Витрины Steam |
| `status_text(...)` | Прогресс-статус обработки файла |

---

## Ключевые технические детали

### Поток обработки файла

1. `handlers/media.py → handle_file()` — проверяет размер файла (`MAX_FILE_SIZE_MB`), скачивает в `gifs/`, создаёт `asyncio.create_task()`
2. `services/processor.py → ProcessingService.process_file()` — захватывает семафор (`MAX_CONCURRENT_TASKS`), проверяет ffmpeg, принимает только `.mp4`
3. `ffmpeg_utils.prepare_and_resize_copy()` — масштабирует до 750px → `prepared_gifs/`
4. `ffmpeg_utils.slice_video_inplace_with_gifs()` — нарезает на 5 частей по 150px, создаёт GIF, архивирует в ZIP
5. `ProcessingService._send_archive()` — отправляет ZIP пользователю с retry (до `ZIP_SEND_RETRIES` попыток)
6. Удаляет все промежуточные файлы

### Rate limiting и ограничение параллелизма

- **ThrottlingMiddleware** (`middlewares/throttling.py`) — подключена к media-роутеру, блокирует повторную отправку файла в течение `RATE_LIMIT_SECONDS` секунд от одного пользователя. Не блокирует `/start` и `/help`.
- **asyncio.Semaphore** (`services/processor.py`) — ограничивает число параллельных задач ffmpeg до `MAX_CONCURRENT_TASKS`. Семафор создаётся в `on_startup` (внутри event loop).

### Проверка размера файла

В `handlers/media.py` перед вызовом `bot.download()` проверяется `file_size` у объектов `Animation`, `Video`, `Document` (Telegram API). Если `file_size > MAX_FILE_SIZE_MB` — файл не скачивается, пользователь получает уведомление.

### aiohttp-сессия

Сессия `aiohttp.ClientSession` создаётся в `on_startup()` внутри event loop через `AiohttpSession` (обёртка aiogram). Закрывается в `on_shutdown()`. Это гарантирует совместимость с Python 3.12+.

### ffmpeg-команды (важно понимать)

**Ресайз до 750px:**
```
ffmpeg -y -i input.mp4 -vf scale=750:-2 -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -c:a copy output.mp4
```

**Нарезка части `i` (0-based), ширина 150px:**
```
ffmpeg -y -i input.mp4 -vf "crop=150:h:i*150:0" -c:v libx264 -crf 18 -preset medium -c:a copy part.mp4
```

**Конвертация в GIF:**
```
ffmpeg -y -i part.mp4 -vf "fps=12,scale=150:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer" output.gif
```

### _fix_gif_terminator — критически важная правка

После генерации каждого GIF последний байт `0x3B` (стандартный GIF89a-терминатор) заменяется на `0x21`. Это необходимо для корректного отображения анимации в движке Steam. **Не удалять и не отключать эту функцию без тестирования в Steam.**

### Обнаружение ffmpeg

`ffmpeg_utils.py` ищет ffmpeg в следующем порядке:
1. Переменная окружения `FFMPEG_BIN`
2. `shutil.which('ffmpeg')` (системный PATH)

Для ffprobe аналогично: `FFPROBE_BIN` → `shutil.which('ffprobe')` → директория рядом с ffmpeg.

---

## Соглашения по разработке

### Язык кода
- Код на Python, комментарии и сообщения пользователю — на **русском**
- Логи (`logger.*`) — на **русском** или английском (уже смешано, не переписывать)

### Принципы внесения изменений

1. **Не трогать `_fix_gif_terminator`** без явного тестирования результата в Steam
2. **Все вызовы ffmpeg** должны идти через `ffmpeg_utils.py`, не в хендлерах напрямую
3. **Асинхронный контекст:** тяжёлые синхронные операции (ffmpeg) запускаются через `loop.run_in_executor(None, func, *args)`, не блокируя event loop
4. **Очистка файлов:** промежуточные файлы ОБЯЗАТЕЛЬНО удаляются после успешной обработки. При ошибке — тоже пытаться почистить артефакты
5. **Retry при отправке:** при `TelegramNetworkError` повторять до `ZIP_SEND_RETRIES` раз с экспоненциальной паузой (`2^attempt` сек)
6. **Новые хендлеры** добавлять через aiogram Router в соответствующий файл `handlers/`, регистрировать в `handlers/__init__.py`
7. **Бизнес-логику обработки** держать в `services/processor.py`, не в хендлерах

### Линтер (обязательно)

- В проекте используется `ruff` с конфигом в `pyproject.toml` (корень репозитория)
- Перед завершением любой правки агент обязан выполнить:
  - `venv/bin/ruff check .`
- Если есть автоматически исправляемые замечания, сначала выполнить:
  - `venv/bin/ruff check . --fix`
  - затем повторно `venv/bin/ruff check .`
- Игнорировать ошибки линтера нельзя: нужно исправить замечания или явно обосновать невозможность исправления

### Добавление новых зависимостей

- Добавлять в `steam_showcase_bot/requirements.txt`
- Указывать минимальную версию: `package>=X.Y.Z`
- Обновлять раздел «Технологический стек» в `README.md`

### Переменные окружения

- Все новые конфигурационные параметры добавлять в `config.py`
- Если параметр критичный — добавить в `.env.example` с примером значения
- Документировать в таблице «Конфигурация» в `README.md`

---

## Что можно улучшить (известная техническая задолженность)

| # | Проблема | Приоритет |
|---|---|---|
| 1 | `MemoryStorage` для FSM — состояния теряются при перезапуске | Средний |
| 2 | `moviepy` и `imageio-ffmpeg` в зависимостях, но не используются | Низкий |
| 3 | Нет unit-тестов для `ffmpeg_utils.py` | Высокий |
| 4 | Нет обработки случая, когда исходное видео шире 750px и нужен downscale | Средний |
| 5 | Логи смешаны (рус/англ) | Низкий |

---

## Как запустить бота локально

```bash
# 1. Активировать venv
source venv/bin/activate

# 2. Создать .env
cp steam_showcase_bot/.env.example steam_showcase_bot/.env
# → вписать TELEGRAM_BOT_TOKEN

# 3. Запустить
python -m steam_showcase_bot
```

---

## Как тестировать изменения

1. Запустить бота локально
2. В Telegram отправить боту GIF-анимацию (Telegram сам конвертирует её в MP4)
3. Бот должен ответить: прогресс-сообщение → прислать ZIP
4. Распаковать ZIP, проверить наличие `part1.gif`…`part5.gif`
5. Каждый файл должен быть корректным GIF с шириной 150px

Для проверки GIF-терминатора:
```python
with open('part1.gif', 'rb') as f:
    f.seek(-1, 2)
    print(hex(f.read(1)[0]))  # должно быть 0x21 (не 0x3b)
```

---

## Полезные команды

```bash
# Проверить доступность ffmpeg
ffmpeg -version
ffprobe -version

# Проверить размер видео
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of json video.mp4

# Ручной ресайз до 750px
ffmpeg -y -i input.mp4 -vf scale=750:-2 -c:v libx264 -crf 18 output.mp4

# Ручная нарезка (первая часть)
ffmpeg -y -i input.mp4 -vf "crop=150:ih:0:0" -c:v libx264 -crf 18 part1.mp4

# Ручная конвертация в GIF
ffmpeg -y -i part1.mp4 -vf "fps=12,scale=150:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer" part1.gif
```
