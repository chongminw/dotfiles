# Outputs: convenience aliases. Optional command: nvim.
# 不包含文件覆盖、删除等安全确认别名。

alias ls='ls --color=auto --group-directories-first'
alias ll='ls -lh --color=auto --group-directories-first'
alias la='ls -lAh --color=auto --group-directories-first'
alias lt='ls -lhtr --color=auto'

alias df='df -hT'
alias du='du -sh'
alias free='free -h'

alias grep='grep --color=auto'
alias diff='diff --color=auto'
alias ping='ping -c 5'

alias cls='clear'
alias quit='exit'

# 仅在 nvim 存在时将 vim 映射为 nvim。
if command -v nvim >/dev/null 2>&1; then
    alias vim='nvim'
fi

alias week='date +"%G 第%V周 周%u"'
alias ports='ss -tuln'
