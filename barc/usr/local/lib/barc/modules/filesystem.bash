# Output: mkcd; mkdir is required only when called. No initialization side effects.

mkcd() {
    if (( $# != 1 )); then
        builtin printf '用法: mkcd <目录>\n' >&2
        return 2
    fi

    command mkdir -p -- "$1" || return
    local _barc_target=$1
    [[ $_barc_target == /* ]] || _barc_target=./$_barc_target
    builtin cd -P -- "$_barc_target" || return
}
