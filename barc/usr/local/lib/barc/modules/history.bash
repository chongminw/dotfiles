# Inputs: BARC_HISTSIZE/BARC_HISTFILESIZE, existing HISTFILE, HOME, NO_COLOR.
# Outputs: HIST* and history options. History is saved on shell exit.
HISTSIZE=${BARC_HISTSIZE:-10000}
HISTFILESIZE=${BARC_HISTFILESIZE:-20000}
: "${HISTFILE=$HOME/.bash_history}"
HISTCONTROL=ignoreboth
HISTIGNORE='ls:ll:la:cd:pwd:exit:clear:history:c:q'
if [[ ! ${NO_COLOR+x} && -t 1 && ${TERM:-dumb} != dumb ]]; then
    HISTTIMEFORMAT=$'\e[2;37m%F %T \e[0m'
else
    HISTTIMEFORMAT='%F %T '
fi
shopt -s histappend cmdhist lithist
