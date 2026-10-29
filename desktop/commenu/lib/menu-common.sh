#!/usr/bin/env bash
# 桌面菜单生命周期工具：只管理已登记的菜单会话，不影响其他 fuzzel 窗口。

wb_menu_init() {
    umask 077
    # 沿用运行目录和内部接口，兼容旧入口及通知历史锁。
    wb_menu_runtime="${XDG_RUNTIME_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}}/waybar"
    mkdir -p -- "$wb_menu_runtime" || return 1
}

wb_menu_token() {
    local pid="$1" stat_line
    local -a fields
    [[ "$pid" =~ ^[1-9][0-9]*$ && -O "/proc/$pid" ]] || return 1
    IFS= read -r stat_line 2>/dev/null <"/proc/$pid/stat" || return 1
    # comm 字段允许空格；从最后一个右括号后拆分。starttime 可防止 PID 复用误杀。
    read -r -a fields <<<"${stat_line##*) }"
    [[ "${fields[2]:-}" == "$pid" && "${fields[3]:-}" == "$pid" ]] || return 1
    [[ "${fields[0]:-}" != Z ]] || return 1
    printf '%s\n' "${fields[19]}"
}

wb_menu_read() {
    local kind="$1" token
    [[ -r "$wb_menu_runtime/$kind.state" ]] || return 1
    read -r wb_menu_pid wb_menu_start <"$wb_menu_runtime/$kind.state" || return 1
    token=$(wb_menu_token "$wb_menu_pid") || return 1
    [[ "$token" == "$wb_menu_start" ]]
}

wb_menu_group_alive() {
    local pid="$1" member stat_line
    local -a fields
    # 控制脚本可能先退出；还须等待同组 fuzzel 真正退出，才可启动下一菜单。
    for member in $(pgrep -u "$UID" -g "$pid"); do
        IFS= read -r stat_line 2>/dev/null <"/proc/$member/stat" || continue
        read -r -a fields <<<"${stat_line##*) }"
        [[ "${fields[2]:-}" == "$pid" && "${fields[0]:-}" != Z ]] && return 0
    done
    return 1
}

wb_menu_stop() {
    local kind="$1" pid attempt
    wb_menu_read "$kind" || return 0
    pid="$wb_menu_pid"
    # setsid 建立独立进程组：菜单和控制脚本一起关闭。
    kill -TERM -- "-$pid" 2>/dev/null || true
    for ((attempt = 0; attempt < 40; attempt++)); do
        wb_menu_group_alive "$pid" || return 0
        sleep 0.025
    done
    return 1
}

wb_menu_toggle() {
    local kind="$1" script="$2" other pid token attempt
    shift 2
    wb_menu_init || return 1
    # 菜单入口共用短期锁，保证连点与互相切换不会生成重复菜单。
    exec 9>"$wb_menu_runtime/menu.lock" || return 1
    flock -w 2 9 || return 1
    if wb_menu_read "$kind"; then
        wb_menu_stop "$kind"
        return
    fi
    for other in launcher power notification; do
        [[ "$other" == "$kind" ]] || wb_menu_stop "$other" || return 1
    done
    # 子会话不能继承互斥锁，否则菜单打开期间其他点击无法进入。
    setsid bash "$script" --run "$@" </dev/null >/dev/null 2>&1 9>&- &
    pid=$!
    for ((attempt = 0; attempt < 40; attempt++)); do
        if token=$(wb_menu_token "$pid"); then
            printf '%s %s\n' "$pid" "$token" >"$wb_menu_runtime/$kind.state"
            return 0
        fi
        kill -0 "$pid" 2>/dev/null || return 1
        sleep 0.025
    done
    return 1
}

wb_menu_cleanup() {
    local path
    for path in "${wb_menu_output:-}" "${wb_menu_snapshot:-}"; do
        [[ -z "$path" ]] || rm -f -- "$path"
    done
    # 保留小登记文件，下次点击通过 PID + starttime 判断是否有效。
    # 退出时不竞争启动锁，也不删除可能已被新会话覆盖的登记。
}

wb_menu_worker() {
    local kind="$1" attempt
    wb_menu_init || exit 1
    trap 'exit 0' TERM INT
    trap wb_menu_cleanup EXIT
    # 等待父进程完成登记：避免菜单快速取消时，父进程把正常退出误判为启动失败。
    for ((attempt = 0; attempt < 40; attempt++)); do
        if wb_menu_read "$kind" && [[ "$wb_menu_pid" == "$$" ]]; then
            return 0
        fi
        sleep 0.025
    done
    exit 1
}
