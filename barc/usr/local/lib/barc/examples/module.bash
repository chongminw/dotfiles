# 用户模块模板：复制为配置目录的 modules/<名称>.bash，再把名称加入 modules.conf。
# 名称仅使用小写字母、数字和连字符，以字母或数字开头。不要使用内置模块同名名称。
# 模板不会自动启用。写明本模块的输入、输出和必要的外部命令。
#
# 模块在加载器函数内 source，与当前 shell 共享变量、函数、别名和选项，无隔离。
# 需要保留到全局的声明用 declare -g，例如：
# declare -g MY_WORKSPACE="$HOME/projects"
# my-workspace() { builtin cd -- "$MY_WORKSPACE"; }
#
# 显式检查关键操作，不依赖 set -e 自动退出，例如：
# source "$HOME/.config/my-tools.bash" || return "$?"
#
# 初始化只定义本地 shell 配置，不联网、不启动服务；此类操作应放进显式调用的函数。
# 成功时明确返回 0，失败时返回非零；状态只记录 source 返回值。
return 0
