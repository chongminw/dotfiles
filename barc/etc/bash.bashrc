# Managed by barc. Arch interactive entry; /etc/profile remains unchanged.
[[ $- == *i* ]] || return 0
[[ ${PS1:-} != '\s-\v\$ ' ]] || PS1='[\u@\h \W]\$ '
if [[ -r /usr/local/lib/barc/loader.bash ]]; then
    source /usr/local/lib/barc/loader.bash
else
    builtin printf 'barc: shared loader is missing\n' >&2
fi
