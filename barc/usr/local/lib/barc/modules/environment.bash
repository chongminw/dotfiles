# Inputs: existing EDITOR/VISUAL, HOME, PATH. Outputs: exported defaults and PATH.
# No dependency on other modules. Existing nonempty editor choices are preserved.
if [[ -z ${EDITOR:-} ]]; then
    for _barc_editor in nvim vim vi; do
        if command -v "$_barc_editor" >/dev/null 2>&1; then
            EDITOR=$_barc_editor
            break
        fi
    done
    unset _barc_editor
fi
if [[ -n ${EDITOR:-} ]]; then
    : "${VISUAL:=$EDITOR}"
    export EDITOR VISUAL
fi
_barc_environment_path() {
    local _barc_e_dir
    # Prepend missing paths only. Do not reorder or remove inherited entries.
    for _barc_e_dir in /usr/local/bin "$HOME/bin" "$HOME/.local/bin"; do
        [[ -d $_barc_e_dir ]] || continue
        case :${PATH:-}: in
            *:"$_barc_e_dir":*) ;;
            *) PATH=$_barc_e_dir${PATH:+:$PATH} ;;
        esac
    done
    export PATH
}
_barc_environment_path
unset -f _barc_environment_path
return 0
