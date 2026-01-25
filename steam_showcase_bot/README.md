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
