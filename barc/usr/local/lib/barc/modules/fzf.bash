# 可选的 fzf 集成：在 completion 之后加载。
# Ctrl-R 搜索历史，Ctrl-T 插入路径，Alt-C 选择目录；FZF_* 参数放 settings.bash。
command -v fzf >/dev/null 2>&1 || return 0

local _barc_fzf_init
_barc_fzf_init=$(command fzf --bash) || return "$?"
eval "$_barc_fzf_init" || return "$?"
return 0
