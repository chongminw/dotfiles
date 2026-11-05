# Outputs: convenience aliases.
# 不包含文件覆盖、删除等安全确认别名。

alias ls='lsd'
alias ll='ls -lh'
alias la='ls -lAh'
alias lt='ls -lhtr'

alias df='df -hT'
alias du='du -sh'
alias free='free -h'

alias grep='grep --color=auto'
alias diff='diff --color=auto'
alias ping='ping -c 5'

alias cls='clear'
alias quit='exit'

alias week='date +"%G 第%V周 周%u"'
alias ports='ss -tuln'
