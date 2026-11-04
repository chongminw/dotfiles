local paths = require("config.paths")
-- 核心前置配置
vim.g.mapleader = " "
-- 标记为“0.12 默认”的选项用于明确个人偏好，当前暂时显式保留

-- —————————— 界面与显示 ——————————
vim.opt.number           = true    -- 显示绝对行号
vim.opt.relativenumber   = true    -- 显示相对行号，方便快速跳转
vim.opt.cursorline       = true    -- 高亮当前光标所在行
vim.opt.wrap             = false   -- 不自动折行，长行横向滚动
vim.opt.scrolloff        = 10      -- 光标上下最少保留行数
vim.opt.sidescrolloff    = 10      -- 光标左右最少保留列数
vim.opt.signcolumn       = "yes"   -- 始终显示符号列，防止界面抖动
vim.opt.showmatch        = true    -- 高亮匹配的括号
vim.opt.cmdheight        = 0       -- 命令行高度
vim.opt.showmode         = false   -- 关闭默认模式提示
vim.opt.fillchars        = { eob = " " } -- 隐藏缓冲区末尾的 ~ 符号

-- —————————— 缩进与 Tab ——————————
vim.opt.tabstop          = 4       -- Tab 显示宽度
vim.opt.softtabstop      = 4       -- 插入模式 Tab/退格宽度
vim.opt.shiftwidth       = 4       -- 自动缩进步长
vim.opt.expandtab        = true    -- Tab 转换为空格
vim.opt.autoindent       = true    -- 新行继承上一行缩进（0.12 默认，显式保留）
vim.opt.smartindent      = true    -- 启用智能缩进

-- —————————— 搜索设置 ——————————
vim.opt.ignorecase       = true    -- 默认忽略大小写
vim.opt.smartcase        = true    -- 含大写时自动区分大小写
vim.opt.hlsearch         = true    -- 高亮搜索匹配结果（0.12 默认，显式保留）
vim.opt.incsearch        = true    -- 实时跳转搜索结果（0.12 默认，显式保留）

-- —————————— 窗口与分屏 ——————————
vim.opt.splitbelow       = true    -- 水平分屏新窗口在下方
vim.opt.splitright       = true    -- 垂直分屏新窗口在右侧
vim.opt.pumheight        = 10      -- 补全菜单最大高度
vim.opt.pumblend         = 10      -- 补全菜单透明度
vim.opt.winblend         = 0       -- 浮动窗口透明度（0.12 默认，显式保留）

-- —————————— 编辑行为 ——————————
vim.opt.backspace        = "indent,eol,start" -- 正常退格行为（0.12 默认，显式保留）
vim.opt.iskeyword:append("-")          -- 连字符视为单词一部分
vim.opt.selection        = "inclusive" -- 可视化模式包含尾字符（0.12 默认，显式保留）
vim.opt.autowrite        = false       -- 关闭自动保存（0.12 默认，显式保留）
vim.opt.autoread         = true        -- 外部修改自动重新读取（0.12 默认，显式保留）
vim.opt.autochdir        = false       -- 不自动切换工作目录（0.12 默认，显式保留）
vim.opt.errorbells       = false       -- 关闭错误提示音（0.12 默认，显式保留）

-- —————————— 性能与响应 ——————————
vim.opt.updatetime       = 300    -- 加快 LSP/插件响应速度
vim.opt.timeoutlen       = 500    -- 快捷键等待超时时间

-- —————————— 文件备份与恢复 ——————————
vim.opt.backup           = false   -- 关闭永久备份文件（0.12 默认，显式保留）
vim.opt.writebackup      = true    -- 写入时临时备份（0.12 默认，显式保留）
vim.opt.swapfile         = false   -- 关闭交换文件
vim.opt.undofile         = true    -- 开启持久化撤销
vim.opt.undodir          = paths.undo -- 撤销文件存储路径

-- —————————— 颜色与主题 ——————————
vim.opt.termguicolors    = true    -- 开启终端真彩色
vim.cmd.colorscheme("catppuccin")    -- 应用配色主题
