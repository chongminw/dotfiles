# Neovim 配置

本机验证版本：Neovim 0.12.6。插件由 lazy.nvim 管理，`lazy-lock.json` 记录具体版本。

## 目录与加载顺序

```text
init.lua
lua/
├── config/
│   ├── lazy.lua          # lazy.nvim 引导、插件目录导入
│   └── paths.lua         # 持久化撤销目录
├── core/
│   ├── options.lua       # 基础选项、Leader、主题
│   ├── autocmds.lua      # 编辑器自动命令
│   ├── keymaps.lua       # 通用快捷键
│   └── statusline.lua    # 自定义状态栏，通过 setup() 显式初始化
└── plugins/
    ├── ui.lua            # mini.icons、bufferline、which-key
    ├── search.lua        # Telescope、plenary
    └── markdown.lua      # Tree-sitter、render-markdown
```

`init.lua` 依次加载 `options → autocmds → keymaps → config.lazy → statusline.setup()`。
Leader 在插件管理器初始化之前设置；状态栏在其图标依赖加载之后初始化。
新增插件时，在 `lua/plugins/` 下返回 Lazy 插件声明表即可自动导入。
插件专用快捷键跟随插件声明，通用快捷键放在 `core/keymaps.lua`。

## 依赖与数据

- Git 用于插件安装和版本管理，ripgrep 用于 Telescope 文本搜索。
- 主题使用本机 Neovim 运行时提供的 `catppuccin`。
- Markdown 需要 `markdown`、`markdown_inline` 两个 Tree-sitter 解析器。
- 插件和解析器位于 `stdpath("data")`，撤销记录位于 `stdpath("state")/undo`。
- Markdown 光标行保持渲染，按 `空格 → m → r` 切换源码显示。
