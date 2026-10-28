if [[ -z ${WAYLAND_DISPLAY:-} && ${XDG_VTNR:-} == 1 ]] &&
    [[ $(tty) == /dev/tty1 ]] && command -v niri-session >/dev/null 2>&1; then
    exec niri-session -l
fi
