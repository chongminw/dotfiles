#!/usr/bin/env bash
set -u
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/menu-common.sh"

if [[ "${1:-}" != --run ]]; then
    wb_menu_toggle power "$script_dir/powermenu.sh"
    exit $?
fi
wb_menu_worker power
wb_menu_output=$(mktemp "$wb_menu_runtime/power-selection.XXXXXX") || exit 1
# 仅将高度缩为三行，宽度、留白、字体和默认 > 提示符沿用应用启动器。
# 单层菜单直接执行选中操作；后台等待让 Bash 能及时处理关闭信号。
fuzzel --dmenu --only-match --namespace waybar-power-menu \
    --lines 3 >"$wb_menu_output" <<'MENU' &
Logout
Reboot
Shutdown
MENU
wait "$!" || exit 0
selection=$(<"$wb_menu_output")
case "$selection" in
    Logout) niri msg action quit --skip-confirmation ;;
    Reboot) systemctl reboot ;;
    Shutdown) systemctl poweroff ;;
    *) exit 0 ;;
esac
