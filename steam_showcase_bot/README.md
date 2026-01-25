# Steam Showcase Bot

Проект: Telegram-бот для автоматической нарезки GIF под витрины Steam.

## Структура проекта

- `steam_showcase_bot/`
  - `bot.py` — Telegram bot (aiogram) handlers.
  - `requirements.txt` — зависимости.
  - `README.md` — этот файл.

## Коротко о запуске (локально)

1. Установите зависимости:

```bash
python -m pip install -r steam_showcase_bot/requirements.txt
```

2. Запустите бота (установите `TELEGRAM_BOT_TOKEN` в окружении):

```bash
python -m steam_showcase_bot.bot
```

> При загрузке GIF (телеграм отдаёт их в формате `.mp4`) бот сохраняет исходник в `gifs/`, копирует его в `prepared_gifs/` и применяет `ffmpeg`-ресайз (ширина не больше 750px).
>
> Требования и установка ffmpeg:
>
> - На Windows: скачайте сборку с https://ffmpeg.org/download.html либо установите через пакетный менеджер (winget: `winget install ffmpeg`, Chocolatey: `choco install ffmpeg`). После установки добавьте папку с `ffmpeg.exe` в системную переменную PATH, либо задайте путь в переменной окружения `FFMPEG_BIN`.
> - Проверить доступность: в PowerShell выполните `ffmpeg -version` — команда должна вывести версию ffmpeg.
> - Если `ffmpeg` не найден, бот пропустит автоматическую подготовку и пришлёт сообщение об этом.
