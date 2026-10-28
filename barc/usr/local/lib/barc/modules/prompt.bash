# Inputs: EUID, TERM, NO_COLOR; optional tput. Outputs: PS1/PS2. No other module dependency.

_barc_setup_prompt() {
    local reset=""
    local red=""
    local green=""
    local yellow=""
    local colors=0

    if [[ -z "${NO_COLOR+x}" \
        && -t 1 \
        && "${TERM:-dumb}" != "dumb" ]] \
        && command -v tput >/dev/null 2>&1; then

        colors="$(command tput colors 2>/dev/null)" || colors=0

        if [[ "$colors" =~ ^[0-9]+$ ]] && (( colors >= 8 )); then
            reset="\[$(command tput sgr0)\]"
            red="\[$(command tput bold)$(command tput setaf 1)\]"
            green="\[$(command tput bold)$(command tput setaf 2)\]"
            yellow="\[$(command tput bold)$(command tput setaf 3)\]"
        fi
    fi

    if (( EUID == 0 )); then
        PS1="${red}┌─[\u@\h]─[\w]\n${red}└─# ${reset}"
    else
        PS1="${green}┌─[\u@\h]─[\w]\n${green}└─$ ${reset}"
    fi

    PS2="${yellow}→ ${reset}"
}

_barc_setup_prompt
unset -f _barc_setup_prompt
