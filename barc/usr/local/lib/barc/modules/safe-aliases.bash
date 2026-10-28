# Outputs: interactive cp/mv/rm/mkdir aliases; assumes GNU coreutils. No hard dependencies.
# 不需要交互保护时，可在 modules.conf 中注释掉该模块。

alias cp='cp -iv'
alias mv='mv -iv'
alias rm='rm -Iv --preserve-root'
alias mkdir='mkdir -pv'
