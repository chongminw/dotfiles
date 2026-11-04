# Neovim 配置

本机验证版本：Neovim 0.12.6。插件由 lazy.nvim 管理，`lazy-lock.json` 记录具体版本。

## 目录与加载顺序

```text
init.lua                    # 加载入口、主题
lua/
├── config/
│   └── lazy.lua          # lazy.nvim 引导、插件目录导入
├── core/
│   ├── options.lua       # 基础选项、Leader
│   ├── autocmds.lua      # 编辑器自动命令
│   ├── keymaps.lua       # 通用快捷键
│   └── statusline.lua    # 自定义状态栏，通过 setup() 显式初始化
└── plugins/
    ├── ui.lua            # mini.icons、bufferline、which-key
    ├── search.lua        # Telescope、plenary
    └── markdown.lua      # render-markdown，使用内置解析器
```

`init.lua` 依次加载 `options → colorscheme("catppuccin") → autocmds → keymaps → config.lazy → statusline.setup()`。
Leader 和终端颜色选项先设置，再由 `init.lua` 应用主题，保持原有启动顺序。
`mini.icons` 明确随启动加载；状态栏在其图标依赖加载之后初始化，bufferline 和 which-key 仍在 `VeryLazy` 时加载。
状态栏的诊断段使用内置 `vim.diagnostic.status()`，文件大小保留按缓冲区缓存。
新增插件时，在 `lua/plugins/` 下返回 Lazy 插件声明表即可自动导入。
插件专用快捷键跟随插件声明，通用快捷键放在 `core/keymaps.lua`。

## 依赖与数据

- Git 用于插件安装和版本管理，ripgrep 用于 Telescope 文本搜索。
- 主题使用本机 Neovim 运行时提供的 `catppuccin`。
- Markdown 使用 Neovim 自带的 `markdown`、`markdown_inline` 解析器及查询规则，随系统包更新。
- 第三方插件位于 `stdpath("data")`；开启 `undofile` 保存撤销历史，使用 Neovim 默认的 `stdpath("state")/undo` 目录，由 Neovim 自动创建。
- 按 `空格 → u` 切换内置撤销树，在左侧打开；首次使用时加载。
- Markdown 光标行保持渲染，按 `空格 → m → r` 切换源码显示。
