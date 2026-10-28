# Sourced only by _barc_help: locals disappear when the caller returns.
# Keep help read-only and use builtins so it works without external commands.
local _barc_h_bold= _barc_h_cyan= _barc_h_yellow= _barc_h_reset=
if [[ -t 1 && -n ${TERM:-} && $TERM != dumb && ! ${NO_COLOR+x} ]]; then
    _barc_h_bold=$'\e[1m'
    _barc_h_cyan=$'\e[36m'
    _barc_h_yellow=$'\e[33m'
    _barc_h_reset=$'\e[0m'
fi

case ${1:-barc} in
    ebrc)
        builtin printf '\n%s编辑 barc 配置%s\n' "$_barc_h_bold" "$_barc_h_reset"
        builtin printf '  用法：ebrc [settings|modules|local]\n\n'
        builtin printf '  %s%-24s%s %s\n' \
            "$_barc_h_cyan" 'ebrc settings' "$_barc_h_reset" '启动参数：编辑器、历史条数、代理地址' \
            "$_barc_h_cyan" 'ebrc modules' "$_barc_h_reset" '启用模块及加载顺序，每行一个名称' \
            "$_barc_h_cyan" 'ebrc local' "$_barc_h_reset" '个人别名、函数及最终覆盖' \
            "$_barc_h_cyan" 'ebrc' "$_barc_h_reset" '等同于 ebrc local' \
            "$_barc_h_cyan" 'ebrc --help' "$_barc_h_reset" '显示本帮助，也可用 -h'
        builtin printf '\n%s配置目录%s\n  %s\n' \
            "$_barc_h_bold" "$_barc_h_reset" "$_BARC_CONFIG_DIR"
        builtin printf '\n%s使用提示%s\n' "$_barc_h_bold" "$_barc_h_reset"
        builtin printf '  首次编辑会创建模板；modules 复制完整默认清单。\n'
        builtin printf '  modules.conf 整表替换默认清单，按需保留已有模块。\n'
        builtin printf '  启动参数写入 settings.bash，使用 EDITOR 指定的编辑器。\n'
        builtin printf '  %s保存后打开新 shell 生效。%s\n' "$_barc_h_yellow" "$_barc_h_reset"
        builtin printf '  完整帮助：%sbarc help%s\n\n' "$_barc_h_cyan" "$_barc_h_reset"
        ;;
    barc)
        builtin printf '\n%sbarc %s · Bash 模块化配置%s\n' \
            "$_barc_h_bold" "$_BARC_VERSION" "$_barc_h_reset"
        builtin printf '  启动参数、模块选择和个人定制，各有清晰入口。\n'
        builtin printf '\n%s常用命令%s\n' "$_barc_h_bold" "$_barc_h_reset"
        builtin printf '  %s%-24s%s %s\n' \
            "$_barc_h_cyan" 'barc help' "$_barc_h_reset" '显示本帮助；barc、barc -h / --help 也可' \
            "$_barc_h_cyan" 'barc status' "$_barc_h_reset" '查看模块加载状态和来源；兼容 barc_status' \
            "$_barc_h_cyan" 'ebrc settings' "$_barc_h_reset" '编辑启动参数：编辑器、历史条数、代理地址' \
            "$_barc_h_cyan" 'ebrc modules' "$_barc_h_reset" '选择模块及加载顺序，每行一个名称' \
            "$_barc_h_cyan" 'ebrc local' "$_barc_h_reset" '编辑个人别名和函数；ebrc 默认打开此文件' \
            "$_barc_h_cyan" 'ebrc --help' "$_barc_h_reset" '查看配置编辑说明'
        builtin printf '  ebrc 是核心命令，不依赖可选模块。\n'
        builtin printf '\n%s当前配置%s\n' "$_barc_h_bold" "$_barc_h_reset"
        builtin printf '  目录：%s\n' "$_BARC_CONFIG_DIR"
        builtin printf '  顺序：settings.bash → modules.conf 中的模块 → local.bash\n'
        builtin printf '\n%s添加个人模块%s\n' "$_barc_h_bold" "$_barc_h_reset"
        builtin printf '  1. 在配置目录的 modules/ 中创建 dev-tools.bash。\n'
        builtin printf '  2. 运行 ebrc modules，添加一行 dev-tools（不带 .bash）。\n'
        builtin printf '  3. 打开新 shell，运行 barc status 检查加载结果。\n'
        builtin printf '  清单整表替换默认列表；模块须显式列入，不自动扫描。\n'
        builtin printf '  %s个人模块与内置模块同名时会报冲突，两者都不加载。%s\n' \
            "$_barc_h_yellow" "$_barc_h_reset"
        builtin printf '\n%s其他常用工具%s\n' "$_barc_h_bold" "$_barc_h_reset"
        builtin printf '  %s%-24s%s %s\n' \
            "$_barc_h_cyan" 'proxy on|off|status|test' "$_barc_h_reset" '代理开关、状态与测试，需要 proxy 模块' \
            "$_barc_h_cyan" 'mkcd <dir>' "$_barc_h_reset" '创建并进入目录，需要 filesystem 模块'
        builtin printf '\n%s使用提示%s\n' "$_barc_h_bold" "$_barc_h_reset"
        builtin printf '  %s修改配置后打开新 shell 生效。%s\n' "$_barc_h_yellow" "$_barc_h_reset"
        builtin printf '  帮助在终端自动着色；设置 NO_COLOR 可关闭颜色。\n'
        builtin printf '\n%s完整说明与模块模板%s\n' "$_barc_h_bold" "$_barc_h_reset"
        builtin printf '  %s/README.md\n  %s/examples/module.bash\n\n' "$_BARC_ROOT" "$_BARC_ROOT"
        ;;
esac
return 0
