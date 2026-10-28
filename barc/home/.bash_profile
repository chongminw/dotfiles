# barc login entry; interactive session policy stays user-owned.
[[ ! -r ~/.bashrc ]] || source ~/.bashrc
if [[ $- == *i* && -n ${_BARC_CONFIG_DIR:-} && -r $_BARC_CONFIG_DIR/session.bash ]]; then
    source "$_BARC_CONFIG_DIR/session.bash"
fi
