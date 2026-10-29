#!/usr/bin/env bash
set -u

readonly STATUS_TIMEOUT=3 ACTION_TIMEOUT=2 HISTORY_TIMEOUT=5 LOCK_TIMEOUT=2
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

case "${1:-status}" in
    status)
        timeout -k 1 "$STATUS_TIMEOUT" python3 "$script_dir/notification-status.py" 2>/dev/null ||
            printf '{"text":"N:--","tooltip":"mako · 服务不可用"}\n'
        ;;
    menu)
        exec "$script_dir/notification-menu.sh"
        ;;
    dnd|history)
        # 模式切换、恢复和清理共用锁，避免同一历史条目被并发操作。
        runtime_dir="${XDG_RUNTIME_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}}/waybar"
        umask 077
        mkdir -p -- "$runtime_dir" || exit 0
        exec 9>"$runtime_dir/history.lock" || exit 0
        flock -w "$LOCK_TIMEOUT" 9 || exit 0
        case "$1" in
            dnd)
                timeout "$ACTION_TIMEOUT" makoctl mode -t do-not-disturb >/dev/null 2>&1 || true
                ;;
            history)
                # 普通状态原生恢复；勿扰时由兼容层为同一 ID 设置展示标记。
                timeout "$HISTORY_TIMEOUT" python3 "$script_dir/history.py" >/dev/null 2>&1 || true
                ;;
        esac
        ;;
    *) exit 1 ;;
esac
