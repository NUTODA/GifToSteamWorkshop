# Steam Showcase Bot

Telegram-бот для автоматической нарезки GIF под Витрину Steam (Steam Showcase).

> Полная документация — в корневом [README.md](../README.md).  
> Инструкции для AI-агентов — в [AGENTS.md](../AGENTS.md).

## Структура пакета

- `bot.py` — точка входа, Telegram-хендлеры (aiogram 3.x)
- `config.py` — загрузка переменных окружения
- `ffmpeg_utils.py` — вся логика ffmpeg: ресайз, нарезка, GIF, архивация
- `requirements.txt` — зависимости pip
- `.env.example` — шаблон конфигурации

## Быстрый старт

### 1. Установить зависимости

```bash
pip install -r steam_showcase_bot/requirements.txt
```

### 2. Настроить окружение

```bash
cp steam_showcase_bot/.env.example steam_showcase_bot/.env
# Вписать TELEGRAM_BOT_TOKEN в .env
```

### 3. Запустить бота

```bash
python -m steam_showcase_bot.bot
```

## Мультиязычность

- Поддерживаются языки интерфейса: `ru`, `en`, `uk`
- Пользователь может сменить язык командой `/lang` (или `/language`)
- Значение по умолчанию задаётся через `DEFAULT_LOCALE` в `.env`

## Требования к ffmpeg

ffmpeg и ffprobe должны быть установлены в системе:

| Платформа | Команда |
|-----------|---------|
| macOS | `brew install ffmpeg` |
| Ubuntu/Debian | `sudo apt install ffmpeg` |
| Windows (winget) | `winget install ffmpeg` |
| Windows (choco) | `choco install ffmpeg` |

Если ffmpeg не в PATH, задайте переменные окружения `FFMPEG_BIN` и `FFPROBE_BIN`.  
Проверка: `ffmpeg -version` и `ffprobe -version`.
