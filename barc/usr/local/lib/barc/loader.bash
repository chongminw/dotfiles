# barc 1.5.2: trusted interactive Bash configuration. No prompt hooks or hot reload.
[[ $- == *i* ]] || return 0
if (( BASH_VERSINFO[0] < 5 || (BASH_VERSINFO[0] == 5 && BASH_VERSINFO[1] < 1) )); then
    builtin printf 'barc: Bash 5.1 or newer is required\n' >&2
    return 1
fi
case ${_BARC_STATE:-} in loading|loaded|loaded_with_errors) return 0 ;; esac
_BARC_STATE=loading
_BARC_VERSION=1.5.2
_BARC_ROOT=${BASH_SOURCE[0]%/*}
_BARC_CONFIG_DIR=$HOME/.config/barc
if [[ ${XDG_CONFIG_HOME:-} == /* ]]; then
    _BARC_CONFIG_DIR=${XDG_CONFIG_HOME%/}/barc
fi
_BARC_ERRORS=0
declare -gA _BARC_MODULE_STATUS=()
declare -gA _BARC_MODULE_SOURCE=()
declare -ga _BARC_MODULE_ORDER=()

# Source user configuration at top level: ordinary declare stays global.
if [[ -r $_BARC_CONFIG_DIR/settings.bash ]]; then
    if ! source "$_BARC_CONFIG_DIR/settings.bash"; then
        builtin printf 'barc: settings.bash returned an error\n' >&2
        ((_BARC_ERRORS+=1))
    fi
fi

# Configuration editing is a core command, independent of optional modules.
ebrc() {
    local -a _barc_editor=()
    local _barc_target=${1-local} _barc_file _barc_template
    (( $# <= 1 )) || { builtin printf 'Usage: ebrc [settings|modules|local] | ebrc --help\n' >&2; return 2; }
    case $_barc_target in
        -h|--help) _barc_help ebrc; return ;;
        settings|local)
            _barc_file=$_BARC_CONFIG_DIR/$_barc_target.bash
            _barc_template=$_BARC_ROOT/examples/$_barc_target.bash ;;
        modules)
            _barc_file=$_BARC_CONFIG_DIR/modules.conf
            _barc_template=$_BARC_ROOT/defaults/modules.conf ;;
        *) builtin printf 'Usage: ebrc [settings|modules|local] | ebrc --help\n' >&2; return 2 ;;
    esac
    # Accept an executable path or a command with simple, whitespace-separated flags.
    if command -v "${EDITOR:-vi}" >/dev/null 2>&1; then
        _barc_editor=("${EDITOR:-vi}")
    else
        IFS=$' \t\n' read -r -a _barc_editor <<< "${EDITOR:-vi}"
    fi
    (( ${#_barc_editor[@]} )) || { builtin printf 'ebrc: EDITOR is empty\n' >&2; return 2; }
    command mkdir -p -- "$_BARC_CONFIG_DIR" || return
    if [[ ! -e $_barc_file && ! -L $_barc_file ]]; then
        command cp -nT -- "$_barc_template" "$_barc_file" || return
    fi
    "${_barc_editor[@]}" "$_barc_file" || return
    builtin printf 'barc: open a new shell to apply changes\n'
}

_barc_read_modules() {
    local _barc_conf=$_BARC_ROOT/defaults/modules.conf
    local _barc_line _barc_name _barc_extra
    local _barc_number=0
    local -A _barc_seen=()
    if [[ -e $_BARC_CONFIG_DIR/modules.conf || -L $_BARC_CONFIG_DIR/modules.conf ]]; then
        _barc_conf=$_BARC_CONFIG_DIR/modules.conf
    fi
    if [[ ! -f $_barc_conf || ! -r $_barc_conf ]]; then
        builtin printf 'barc: module list is unreadable: %s\n' "$_barc_conf" >&2
        ((_BARC_ERRORS+=1))
        return 0
    fi
    while IFS= read -r _barc_line || [[ -n $_barc_line ]]; do
        ((_barc_number+=1))
        _barc_line=${_barc_line%$'\r'}
        _barc_line=${_barc_line%%#*}
        read -r _barc_name _barc_extra <<< "$_barc_line"
        [[ -n $_barc_name ]] || continue
        if [[ ! $_barc_name =~ ^[a-z0-9][a-z0-9-]*$ || -n $_barc_extra ]]; then
            builtin printf 'barc: invalid module entry at %s:%s\n' "$_barc_conf" "$_barc_number" >&2
            ((_BARC_ERRORS+=1))
            continue
        fi
        [[ ! ${_barc_seen[$_barc_name]+present} ]] || continue
        _barc_seen[$_barc_name]=1
        _BARC_MODULE_ORDER+=("$_barc_name")
    done < "$_barc_conf"
}

_barc_run_modules() {
    local _barc_name _barc_file _barc_system _barc_user
    # Modules inherit the caller's stdin, never the module list.
    # Modules run in this function: persistent declarations require declare -g.
    # Check critical operations explicitly and return nonzero on failure.
    for _barc_name in "${_BARC_MODULE_ORDER[@]}"; do
        _barc_system=$_BARC_ROOT/modules/$_barc_name.bash
        _barc_user=$_BARC_CONFIG_DIR/modules/$_barc_name.bash
        _barc_file=
        _BARC_MODULE_SOURCE[$_barc_name]='-'
        # Resolve only listed modules. Never silently shadow a module by name.
        if [[ ( -e $_barc_system || -L $_barc_system ) &&
              ( -e $_barc_user || -L $_barc_user ) ]]; then
            _BARC_MODULE_STATUS[$_barc_name]=conflict
            _BARC_MODULE_SOURCE[$_barc_name]="$_barc_system | $_barc_user"
        elif [[ -e $_barc_system || -L $_barc_system ]]; then
            _barc_file=$_barc_system
        elif [[ -e $_barc_user || -L $_barc_user ]]; then
            _barc_file=$_barc_user
        else
            _BARC_MODULE_STATUS[$_barc_name]=missing
        fi
        if [[ -n $_barc_file ]]; then
            _BARC_MODULE_SOURCE[$_barc_name]=$_barc_file
            if [[ ! -f $_barc_file || ! -r $_barc_file ]]; then
                _BARC_MODULE_STATUS[$_barc_name]=unreadable
            elif source "$_barc_file"; then
                _BARC_MODULE_STATUS[$_barc_name]=loaded
                continue
            else
                _BARC_MODULE_STATUS[$_barc_name]=failed
            fi
        fi
        builtin printf 'barc: module %s: %s (%s)\n' "$_barc_name" \
            "${_BARC_MODULE_STATUS[$_barc_name]}" "${_BARC_MODULE_SOURCE[$_barc_name]}" >&2
        ((_BARC_ERRORS+=1))
    done
}
_barc_read_modules
_barc_run_modules
unset -f _barc_read_modules _barc_run_modules
if [[ -r $_BARC_CONFIG_DIR/local.bash ]]; then
    if ! source "$_BARC_CONFIG_DIR/local.bash"; then
        builtin printf 'barc: local.bash returned an error\n' >&2
        ((_BARC_ERRORS+=1))
    fi
fi
if (( _BARC_ERRORS )); then _BARC_STATE=loaded_with_errors; else _BARC_STATE=loaded; fi

barc_status() {
    local _barc_s_module
    builtin printf 'barc %s: %s (%s errors)\n' "$_BARC_VERSION" "$_BARC_STATE" "$_BARC_ERRORS"
    for _barc_s_module in "${_BARC_MODULE_ORDER[@]}"; do
        builtin printf '  %-16s %-10s %s\n' "$_barc_s_module" \
            "${_BARC_MODULE_STATUS[$_barc_s_module]}" "${_BARC_MODULE_SOURCE[$_barc_s_module]}"
    done
    builtin printf 'Status reflects source return values, not functional checks.\n'
    (( _BARC_ERRORS == 0 ))
}

# Read help only when requested; rendering runs inside this function's scope.
_barc_help() {
    if [[ ! -f $_BARC_ROOT/help.bash || ! -r $_BARC_ROOT/help.bash ]]; then
        builtin printf 'barc: help file is unavailable: %s/help.bash\n' "$_BARC_ROOT" >&2
        return 1
    fi
    source "$_BARC_ROOT/help.bash" "${1:-barc}"
}

barc() {
    if (( $# <= 1 )); then
        case ${1-help} in
            help|-h|--help) _barc_help barc; return ;;
            status) barc_status; return ;;
        esac
    fi
    builtin printf '用法: barc [help|status]；运行 barc help 查看帮助。\n' >&2
    return 2
}
return 0
