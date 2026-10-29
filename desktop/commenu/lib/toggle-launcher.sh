#!/usr/bin/env bash
set -u
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/menu-common.sh"

if [[ "${1:-}" != --run ]]; then
    wb_menu_toggle launcher "$script_dir/toggle-launcher.sh" "$@"
    exit $?
fi
shift
wb_menu_worker launcher
# 不覆盖颜色、字体或几何参数，完整沿用原生 fuzzel 主题。
fuzzel --namespace waybar-launcher --terminal 'ghostty -e' "$@" &
wait "$!" || true
