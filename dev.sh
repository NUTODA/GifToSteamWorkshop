#!/usr/bin/env bash
# dev.sh — вспомогательные команды для разработки и эксплуатации бота
# Использование: ./dev.sh <команда>

set -euo pipefail

SERVICE="bot"
COMPOSE="docker compose"

# ─── Цвета ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "${CYAN}▸ $*${RESET}"; }
success() { echo -e "${GREEN}✔ $*${RESET}"; }
warn()    { echo -e "${YELLOW}⚠ $*${RESET}"; }
error()   { echo -e "${RED}✖ $*${RESET}" >&2; exit 1; }

# ─── Команды ──────────────────────────────────────────────────────────────────

cmd_help() {
    echo -e "${BOLD}GifToSteamWorkshop — dev.sh${RESET}"
    echo ""
    echo -e "${BOLD}Использование:${RESET}  ./dev.sh <команда>"
    echo ""
    echo -e "${BOLD}Команды:${RESET}"
    echo -e "  ${CYAN}up${RESET}          Собрать образ и запустить бота (фоновый режим)"
    echo -e "  ${CYAN}down${RESET}        Остановить и удалить контейнер"
    echo -e "  ${CYAN}restart${RESET}     Перезапустить контейнер без пересборки"
    echo -e "  ${CYAN}rebuild${RESET}     Пересобрать образ и перезапустить контейнер"
    echo -e "  ${CYAN}stop${RESET}        Приостановить контейнер (без удаления)"
    echo -e "  ${CYAN}start${RESET}       Запустить ранее остановленный контейнер"
    echo -e "  ${CYAN}logs${RESET}        Показать последние 100 строк логов и следить за ними"
    echo -e "  ${CYAN}logs-tail N${RESET} Показать последние N строк логов (без слежения)"
    echo -e "  ${CYAN}status${RESET}      Показать статус контейнера"
    echo -e "  ${CYAN}shell${RESET}       Открыть bash внутри запущенного контейнера"
    echo -e "  ${CYAN}build${RESET}       Только собрать образ (без запуска)"
    echo -e "  ${CYAN}pull${RESET}        Скачать обновлённые базовые образы"
    echo -e "  ${CYAN}prune${RESET}       Удалить остановленные контейнеры и неиспользуемые образы"
    echo -e "  ${CYAN}prune-all${RESET}   Удалить контейнер, все volumes и образы проекта (⚠ данные удаляются)"
    echo -e "  ${CYAN}env-check${RESET}   Проверить наличие .env файла и обязательных переменных"
    echo -e "  ${CYAN}ffmpeg-check${RESET} Проверить версию ffmpeg внутри контейнера"
}

cmd_up() {
    cmd_env_check
    info "Сборка образа и запуск контейнера..."
    $COMPOSE up -d --build
    success "Бот запущен. Логи: ./dev.sh logs"
}

cmd_down() {
    info "Остановка и удаление контейнера..."
    $COMPOSE down
    success "Контейнер остановлен."
}

cmd_restart() {
    info "Перезапуск контейнера..."
    $COMPOSE restart "$SERVICE"
    success "Контейнер перезапущен."
}

cmd_rebuild() {
    cmd_env_check
    info "Пересборка образа без кэша и перезапуск..."
    $COMPOSE build --no-cache "$SERVICE"
    $COMPOSE up -d "$SERVICE"
    success "Образ пересобран, контейнер перезапущен."
}

cmd_stop() {
    info "Приостановка контейнера (без удаления)..."
    $COMPOSE stop "$SERVICE"
    success "Контейнер остановлен (данные сохранены)."
}

cmd_start() {
    info "Запуск ранее остановленного контейнера..."
    $COMPOSE start "$SERVICE"
    success "Контейнер запущен."
}

cmd_logs() {
    info "Логи контейнера (Ctrl+C для выхода):"
    $COMPOSE logs -f --tail=100 "$SERVICE"
}

cmd_logs_tail() {
    local n="${1:-50}"
    $COMPOSE logs --tail="$n" "$SERVICE"
}

cmd_status() {
    echo ""
    $COMPOSE ps
    echo ""
    info "Использование ресурсов:"
    docker stats --no-stream --format \
        "  CPU: {{.CPUPerc}}  RAM: {{.MemUsage}}  NET: {{.NetIO}}" \
        "$(docker compose ps -q "$SERVICE" 2>/dev/null)" 2>/dev/null || \
        warn "Контейнер не запущен."
}

cmd_shell() {
    info "Открываю bash в контейнере '$SERVICE'..."
    $COMPOSE exec "$SERVICE" bash
}

cmd_build() {
    info "Сборка образа (без запуска)..."
    $COMPOSE build "$SERVICE"
    success "Образ собран."
}

cmd_pull() {
    info "Скачивание обновлённых базовых образов..."
    $COMPOSE pull
    success "Базовые образы обновлены. Для применения запустите: ./dev.sh rebuild"
}

cmd_prune() {
    info "Очистка неиспользуемых контейнеров и образов..."
    docker container prune -f
    docker image prune -f
    success "Очистка выполнена."
}

cmd_prune_all() {
    warn "Это удалит контейнер, все volumes проекта (gifs, prepared_gifs, sliced_gifs, logs) и образ."
    read -r -p "Вы уверены? [y/N] " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || { info "Отменено."; exit 0; }
    info "Удаление контейнера, volumes и образов..."
    $COMPOSE down -v --rmi local
    success "Всё удалено."
}

cmd_env_check() {
    local env_file="steam_showcase_bot/.env"
    if [[ ! -f "$env_file" ]]; then
        error ".env файл не найден: $env_file\n  Создайте его из шаблона:\n  cp steam_showcase_bot/.env.example steam_showcase_bot/.env"
    fi
    if ! grep -q "TELEGRAM_BOT_TOKEN" "$env_file" 2>/dev/null || \
       grep -q "TELEGRAM_BOT_TOKEN=your_bot_token_here" "$env_file" 2>/dev/null || \
       grep -q "TELEGRAM_BOT_TOKEN=$" "$env_file" 2>/dev/null; then
        error "TELEGRAM_BOT_TOKEN не задан в $env_file"
    fi
    success ".env файл найден и токен задан."
}

cmd_ffmpeg_check() {
    info "Версия ffmpeg внутри контейнера:"
    $COMPOSE exec "$SERVICE" ffmpeg -version 2>&1 | head -n 1
    info "Версия ffprobe внутри контейнера:"
    $COMPOSE exec "$SERVICE" ffprobe -version 2>&1 | head -n 1
}

# ─── Диспетчер ────────────────────────────────────────────────────────────────

COMMAND="${1:-help}"
shift || true

case "$COMMAND" in
    up)            cmd_up ;;
    down)          cmd_down ;;
    restart)       cmd_restart ;;
    rebuild)       cmd_rebuild ;;
    stop)          cmd_stop ;;
    start)         cmd_start ;;
    logs)          cmd_logs ;;
    logs-tail)     cmd_logs_tail "${1:-50}" ;;
    status)        cmd_status ;;
    shell)         cmd_shell ;;
    build)         cmd_build ;;
    pull)          cmd_pull ;;
    prune)         cmd_prune ;;
    prune-all)     cmd_prune_all ;;
    env-check)     cmd_env_check ;;
    ffmpeg-check)  cmd_ffmpeg_check ;;
    help|--help|-h) cmd_help ;;
    *)
        error "Неизвестная команда: '$COMMAND'\nСправка: ./dev.sh help"
        ;;
esac
