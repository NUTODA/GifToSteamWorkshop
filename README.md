# GifToSteamWorkshop

Telegram-бот для автоматической подготовки GIF-анимаций под Витрину Steam (Steam Showcase).

---

## Зачем это нужно

Витрина Steam отображает GIF-анимации через 5 горизонтальных слотов, каждый шириной **150px**. Чтобы анимация выглядела как единое целое, её нужно:

1. Отмасштабировать до ширины **750px** (5 × 150px)
2. Нарезать на **5 частей** по 150px
3. Сконвертировать каждую часть в `.gif`
4. Загрузить каждый `.gif` в соответствующий слот витрины

Бот автоматизирует шаги 1–3 и отдаёт пользователю ZIP-архив с 5 готовыми GIF-файлами (`part1.gif` … `part5.gif`).

---

## Как это работает

```
Пользователь → Telegram (GIF/видео MP4)
       ↓
Bot скачивает файл → gifs/
       ↓
ffmpeg: scale=750:-2, H.264 CRF 18 → prepared_gifs/
       ↓
ffmpeg: crop 5×150px → sliced_gifs/<stem>_part{1..5}.mp4
       ↓
ffmpeg: каждая часть → GIF (fps=12, 150px, 128 цветов, dither=bayer)
 + _fix_gif_terminator(): 0x3B → 0x21 (совместимость со Steam)
       ↓
ZIP-архив: sliced_gifs/<stem>_gifs.zip
       ↓
Bot отправляет ZIP пользователю (retry x3)
       ↓
Очистка промежуточных файлов
```

> **Примечание об `_fix_gif_terminator`:** После генерации каждого GIF бот заменяет последний байт с `0x3B` (стандартный GIF-терминатор) на `0x21`. Это нестандартная правка, необходимая для корректного воспроизведения анимации движком Steam.

---

## Структура репозитория

```
GifToSteamWorkshop/
├── README.md                        ← этот файл
├── AGENTS.md                        ← инструкции для AI-агентов
├── Dockerfile                       ← образ для Docker
├── docker-compose.yml               ← оркестрация контейнера
├── .dockerignore                    ← исключения из контекста сборки
├── steam_showcase_bot/              ← основной Python-пакет
│   ├── __init__.py
│   ├── __main__.py                  ← точка входа: python -m steam_showcase_bot
│   ├── bot.py                       ← создание Bot/Dispatcher, startup/shutdown, polling
│   ├── config.py                    ← загрузка переменных окружения
│   ├── ffmpeg_utils.py              ← вся логика ffmpeg: resize, slice, gif
│   ├── texts.py                     ← текстовые шаблоны и UI-хелперы
│   ├── handlers/
│   │   ├── __init__.py              ← регистрация роутеров
│   │   ├── commands.py              ← /start, /help
│   │   ├── callbacks.py             ← inline-кнопки
│   │   └── media.py                 ← обработка медиафайлов
│   ├── services/
│   │   ├── __init__.py
│   │   └── processor.py             ← resize → slice → gif → zip → отправка
│   ├── middlewares/
│   │   ├── __init__.py
│   │   └── throttling.py            ← rate limiting по пользователю
│   ├── requirements.txt             ← зависимости pip
│   ├── .env                         ← секреты (не в git)
│   ├── .env.example                 ← пример конфига
│   ├── .gitignore
│   ├── gifs/                        ← оригинальные загрузки (создаётся автоматически)
│   ├── prepared_gifs/               ← ресайзнутые копии (создаётся автоматически)
│   └── sliced_gifs/                 ← нарезанные части + ZIP (создаётся автоматически)
├── steam_showcase_bot.log           ← лог-файл (создаётся автоматически)
└── venv/                            ← виртуальное окружение (не в git)
```

---

## Установка и запуск

### Требования

- Python 3.10+
- `ffmpeg` и `ffprobe` (должны быть в PATH или заданы через `FFMPEG_BIN` / `FFPROBE_BIN`)

### 1. Клонировать репозиторий

```bash
git clone <repo-url>
cd GifToSteamWorkshop
```

### 2. Создать виртуальное окружение

```bash
python -m venv venv
source venv/bin/activate          # Linux / macOS
# venv\Scripts\activate           # Windows
```

### 3. Установить зависимости

```bash
pip install -r steam_showcase_bot/requirements.txt
```

### 4. Настроить окружение

Скопировать `.env.example` в `.env` и заполнить:

```bash
cp steam_showcase_bot/.env.example steam_showcase_bot/.env
```

```dotenv
TELEGRAM_BOT_TOKEN=your_bot_token_here
LOG_LEVEL=INFO
```

### 5. Установить ffmpeg

| Платформа | Команда |
|-----------|---------|
| macOS (Homebrew) | `brew install ffmpeg` |
| Ubuntu/Debian | `sudo apt install ffmpeg` |
| Windows (winget) | `winget install ffmpeg` |
| Windows (Chocolatey) | `choco install ffmpeg` |

Проверка: `ffmpeg -version` и `ffprobe -version`.

Если ffmpeg не в PATH, задайте переменные окружения:
```dotenv
FFMPEG_BIN=/path/to/ffmpeg
FFPROBE_BIN=/path/to/ffprobe
```

### 6. Запустить бота

```bash
python -m steam_showcase_bot
```

Бот запустится в режиме long polling. Остановка — `Ctrl+C`.

---

## Запуск через Docker

### Требования

- [Docker](https://docs.docker.com/get-docker/) и [Docker Compose](https://docs.docker.com/compose/) (v2+)
- Файл `steam_showcase_bot/.env` с токеном бота (см. шаг 4 выше)

### Сборка и запуск

```bash
docker compose up -d --build
```

Контейнер соберётся (~2–3 мин при первом запуске: установка ffmpeg + зависимостей), после чего бот запустится в фоновом режиме.

### Управление

```bash
# Посмотреть логи в реальном времени
docker compose logs -f bot

# Остановить бота
docker compose down

# Пересобрать образ (после изменений в коде)
docker compose up -d --build

# Посмотреть статус контейнера
docker compose ps
```

### Что хранится в Docker volumes

| Volume | Путь в контейнере | Содержимое |
|---|---|---|
| `gifs` | `/app/steam_showcase_bot/gifs` | Скачанные оригиналы |
| `prepared_gifs` | `/app/steam_showcase_bot/prepared_gifs` | Ресайзнутые MP4 |
| `sliced_gifs` | `/app/steam_showcase_bot/sliced_gifs` | Нарезанные части и ZIP |
| `logs` | `/app/steam_showcase_bot/logs` | Лог-файлы |

Данные в volumes **не удаляются** при пересборке образа. Для полной очистки: `docker compose down -v`.

---

## Конфигурация

Все параметры задаются через переменные окружения (в файле `.env` внутри `steam_showcase_bot/` или в системном окружении).

| Переменная | По умолчанию | Описание |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | — | **Обязательно.** Токен бота из [@BotFather](https://t.me/BotFather) |
| `LOG_LEVEL` | `INFO` | Уровень логирования: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FILE` | `steam_showcase_bot.log` | Имя лог-файла |
| `LOG_TO_FILE` | `1` | Писать логи в файл (`1` / `0`) |
| `SAVE_UPLOADS` | `1` | Сохранять загрузки пользователей (`1` / `0`) |
| `FFMPEG_BIN` | авто (PATH) | Путь к бинарнику `ffmpeg` |
| `FFPROBE_BIN` | авто (PATH) | Путь к бинарнику `ffprobe` |
| `TELEGRAM_CLIENT_TIMEOUT` | `300` | HTTP-таймаут aiohttp-клиента (сек) |
| `TELEGRAM_CLIENT_CONNECT_LIMIT` | `0` | Лимит соединений aiohttp (0 = без ограничений) |
| `MAX_FILE_SIZE_MB` | `20` | Максимальный размер входного файла (MB); проверяется до скачивания |
| `MAX_ARCHIVE_SEND_MB` | `50` | Максимальный размер ZIP для отправки (MB); если больше — архив остаётся на диске |
| `RATE_LIMIT_SECONDS` | `30` | Минимальный интервал между файлами от одного пользователя (сек) |
| `MAX_CONCURRENT_TASKS` | `3` | Максимум параллельных задач ffmpeg |
| `ZIP_SEND_RETRIES` | `3` | Количество попыток отправки ZIP при сетевой ошибке |
| `ZIP_SEND_TIMEOUT` | `300` | Таймаут одной попытки отправки ZIP (сек) |
| `BOT_DEBUG` | `0` | Включить отладочные хендлеры (`1` / `0`) |

---

## Технологический стек

| Компонент | Версия | Назначение |
|---|---|---|
| Python | 3.10+ | Основной язык |
| [aiogram](https://docs.aiogram.dev/) | ≥ 3.0.0b7 | Асинхронный Telegram Bot API |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | ≥ 0.21.0 | Загрузка `.env` |
| ffmpeg / ffprobe | любая актуальная | Ресайз, нарезка, конвертация в GIF |

---

## Ключевые модули

### `bot.py`

Создание `Bot` и `Dispatcher`, lifecycle-хуки `on_startup`/`on_shutdown`, запуск polling. Сессия `aiohttp` создаётся в `on_startup` (внутри event loop).

### `texts.py`

Все текстовые шаблоны, inline-клавиатура, прогресс-статус обработки.

### `handlers/`

Aiogram-роутеры: `commands.py` (`/start`, `/help`), `callbacks.py` (inline-кнопки), `media.py` (приём медиафайлов с проверкой размера до скачивания).

### `services/processor.py`

Класс `ProcessingService` — полный цикл обработки файла (resize → slice → GIF → ZIP → отправка → cleanup) с `asyncio.Semaphore` для ограничения параллельных задач ffmpeg.

### `middlewares/throttling.py`

`ThrottlingMiddleware` — rate limiting по пользователю, подключается к медиа-роутеру.

### `ffmpeg_utils.py`

Вся работа с ffmpeg:

- `is_ffmpeg_available()` — проверяет наличие ffmpeg
- `resize_mp4_to_width_750(input, output)` — масштабирует видео до 750px (H.264, CRF 18)
- `prepare_and_resize_copy(src, prepared_dir)` — копирует файл и применяет resize
- `get_width_height(path)` — читает размеры через ffprobe
- `make_gif_from_video(input, output, fps, scale_w, max_colors)` — конвертирует видео в GIF с palettegen/paletteuse
- `_fix_gif_terminator(gif_path)` — заменяет `0x3B` → `0x21` в конце GIF
- `slice_video_inplace_with_gifs(path)` — нарезает 750px-видео на 5 частей по 150px, создаёт GIF для каждой части, архивирует в ZIP

### `config.py`

Загружает переменные окружения через `python-dotenv`. Экспортирует все настройки: токены, лимиты, таймауты, rate limiting.

---

## Известные особенности и ограничения

1. **Только MP4.** Telegram присылает GIF в формате MP4. Другие форматы (`.gif`, `.webm`) принимаются как документ, но при несовпадении `.mp4` расширения обработка пропускается.

2. **Большие архивы.** Если результирующий ZIP превышает `MAX_ARCHIVE_SEND_MB` (50 MB по умолчанию), файл остаётся на диске сервера и пользователь получает уведомление.

3. **Хранилище состояний.** Используется `MemoryStorage` — состояния FSM теряются при перезапуске бота. Для production рекомендуется `RedisStorage`.

---

## Разработка и отладка

### Отладочный режим

Задайте `LOG_LEVEL=DEBUG` или `BOT_DEBUG=1` в `.env`. Бот будет:
- Логировать все входящие сообщения с полным разбором полей
- Отправлять в чат дополнительную отладочную информацию о типе медиафайла

### Структура рабочих директорий

Директории создаются автоматически при первом запуске:

```
steam_showcase_bot/
├── gifs/                   ← сохраняются оригиналы (временно)
├── prepared_gifs/          ← ресайзнутые MP4 (временно)
└── sliced_gifs/
    ├── <stem>_part2.mp4    ← промежуточные части (удаляются после архивации)
    ├── <stem>_part3.mp4
    ├── <stem>_part4.mp4
    ├── <stem>_part5.mp4
    └── <stem>_gifs.zip     ← финальный результат
```

Оригинал `<stem>.mp4` в `sliced_gifs/` заменяется `part1` в процессе нарезки.

### Логирование

Логи пишутся в `steam_showcase_bot.log` (корень проекта) и в stdout. Уровень задаётся через `LOG_LEVEL`.
