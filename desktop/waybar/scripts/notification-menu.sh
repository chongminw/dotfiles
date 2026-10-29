#!/usr/bin/env bash
set -u

readonly SNAPSHOT_TIMEOUT=6 CLEAR_TIMEOUT=15 KILL_TIMEOUT=5 LOCK_TIMEOUT=2
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$HOME/.local/lib/commenu/menu-common.sh" || exit "$?"

if [[ "${1:-}" != --run ]]; then
    wb_menu_toggle notification "$script_dir/notification-menu.sh"
    exit $?
fi
wb_menu_worker notification
wb_menu_output=$(mktemp "$wb_menu_runtime/notification-selection.XXXXXX") || exit 1
wb_menu_snapshot=$(mktemp "$wb_menu_runtime/notification-snapshot.XXXXXX") || exit 1

run_cleanup() (
    local limit="$1"
    shift
    exec 8>"$wb_menu_runtime/history.lock" || exit 1
    flock -w "$LOCK_TIMEOUT" 8 || exit 1
    # 保持在菜单进程组中，切换菜单时能够同时停止核心操作并释放锁。
    timeout --foreground -k "$KILL_TIMEOUT" "$limit" \
        python3 "$script_dir/notification-cleanup.py" "$@"
)

show_message() {
    local message="${1//$'\n'/ }"
    # 结果提示不用系统通知，以免清理后又增加通知数。
    fuzzel --dmenu --only-match --namespace waybar-notification-menu \
        --lines 1 <<<"$message" >/dev/null &
    wait "$!" || true
}

run_cleanup "$SNAPSHOT_TIMEOUT" snapshot "$wb_menu_snapshot" >"$wb_menu_output" 2>/dev/null &
if ! wait "$!"; then
    show_message '暂时无法读取通知，请稍后重试'
    exit 0
fi
menu_items=$(<"$wb_menu_output")
mapfile -t choices <<<"$menu_items"
if [[ "${#choices[@]}" != 3 || -z "${choices[0]}" || -z "${choices[1]}" || -z "${choices[2]}" ]]; then
    show_message '暂时无法读取通知，请稍后重试'
    exit 0
fi

# 等待用户选择期间不占 history.lock；删除只使用这次展示前的快照。
fuzzel --dmenu --only-match --namespace waybar-notification-menu \
    --lines 3 <<<"$menu_items" >"$wb_menu_output" &
wait "$!" || exit 0
selection=$(<"$wb_menu_output")
case "$selection" in
    "${choices[0]}") scope=current ;;
    "${choices[1]}") scope=history ;;
    "${choices[2]}") scope=all ;;
    *) exit 0 ;;
esac

run_cleanup "$CLEAR_TIMEOUT" clear "$scope" "$wb_menu_snapshot" >"$wb_menu_output" 2>/dev/null &
wait "$!" && exit 0
message=$(python3 -c '
import json, sys
result = json.load(sys.stdin)
message = result.get("message")
if not isinstance(message, str) or not message:
    raise ValueError("missing result message")
print(message)
' <"$wb_menu_output" 2>/dev/null) || message='通知清理未完成，请稍后重试'
show_message "$message"
