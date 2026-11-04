-- 快捷键配置辅助函数
local function opts(desc) return { silent = true, desc = desc } end
local map = vim.keymap.set

-- —————————— 基础前置 ——————————
-- 禁用空格默认行为（适配 Leader 键）
map({ "n", "v" }, "<Space>", "<Nop>", { silent = true })

-- —————————— 插入模式 ——————————
-- 快速退出插入模式
for _, keys in ipairs({"jk", "kj"}) do
	map("i", keys, "<Esc>", opts("退出插入模式"))
end

-- —————————— 可视模式 ——————————
-- 移动选中文本 + 保持选中缩进
map("x", "J", ":m '>+1<CR>gv=gv", opts("向下移动选中文本"))
map("x", "K", ":m '<-2<CR>gv=gv", opts("向上移动选中文本"))
map("v", "<", "<gv", opts("减少缩进并保持选中"))
map("v", ">", ">gv", opts("增加缩进并保持选中"))

-- —————————— 文件操作 ——————————
map("n", "<leader>w", "<cmd>write<CR>", opts("保存文件"))
map("n", "<leader>q", "<cmd>bdelete<cr>", opts("关闭当前缓冲区"))
map("n", "<leader>Q", "<cmd>quitall<cr>", opts("退出 Neovim"))

-- —————————— 搜索优化 ——————————
map("n", "<leader>h", "<cmd>nohlsearch<cr>", opts("清除搜索高亮"))

-- —————————— 窗口管理 ——————————
-- 窗口快速切换
map("n", "<C-h>", "<C-w>h", opts("切换到左侧窗口"))
map("n", "<C-j>", "<C-w>j", opts("切换到下方窗口"))
map("n", "<C-k>", "<C-w>k", opts("切换到上方窗口"))
map("n", "<C-l>", "<C-w>l", opts("切换到右侧窗口"))

-- 窗口大小调整
map("n", "<C-Up>", "<cmd>resize +2<cr>", opts("增加窗口高度"))
map("n", "<C-Down>", "<cmd>resize -2<cr>", opts("减少窗口高度"))
map("n", "<C-Left>", "<cmd>vertical resize -2<cr>", opts("减少窗口宽度"))
map("n", "<C-Right>", "<cmd>vertical resize +2<cr>", opts("增加窗口宽度"))

-- —————————— 缓冲区管理 ——————————
map("n", "<S-h>", "<cmd>bprevious<cr>", opts("上一个缓冲区"))
map("n", "<S-l>", "<cmd>bnext<cr>", opts("下一个缓冲区"))
