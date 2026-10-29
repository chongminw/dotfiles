#!/usr/bin/env bash
# Capture completely before opening the editor or changing the clipboard.
set -u
if (( $# != 1 )) || [[ $1 != annotate && $1 != copy ]]; then
    printf '用法: screenshot.sh {annotate|copy}\n' >&2
    exit 2
fi
mode=$1

umask 077
work_dir=$(mktemp -d -- "${XDG_RUNTIME_DIR:-${TMPDIR:-/tmp}}/niri-screenshot.XXXXXX") || exit "$?"
trap 'rm -f -- "$work_dir/selection.err" "$work_dir/screenshot.png"; rmdir -- "$work_dir"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if region=$(slurp </dev/null 2>"$work_dir/selection.err"); then
    if [[ -z $region ]]; then
        printf '截图失败：框选结果为空。\n' >&2
        exit 1
    fi
else
    result=$?
    # slurp uses status 1 for both cancellation and errors; distinguish its
    # explicit cancellation message instead of swallowing every failure.
    if (( result == 1 )) && [[ -z $region && $(<"$work_dir/selection.err") == 'selection cancelled' ]]; then
        exit 0
    fi
    cat -- "$work_dir/selection.err" >&2
    exit "$result"
fi

image=$work_dir/screenshot.png
grim -g "$region" "$image" || exit "$?"
if [[ ! -s $image ]]; then
    printf '截图失败：未生成图片。\n' >&2
    exit 1
fi

case $mode in
    annotate)
        satty --filename "$image" --copy-command wl-copy --actions-on-enter save-to-clipboard,exit
        ;;
    copy)
        wl-copy --type image/png <"$image"
        ;;
esac
