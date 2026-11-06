# 可选的 zoxide 集成：放在模块清单末尾；zi 交互选择另需 fzf。
# 启用 z / zi 和目录记录；_ZO_* 参数放 settings.bash，历史由各用户独立保存。
command -v zoxide >/dev/null 2>&1 || return 0

local _barc_zoxide_init
_barc_zoxide_init=$(command zoxide init bash) || return "$?"
eval "$_barc_zoxide_init" || return "$?"
return 0
