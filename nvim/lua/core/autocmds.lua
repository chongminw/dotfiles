local api = vim.api

-- 辅助函数：创建自动命令组（统一管理，支持安全重载）
local function augroup(name)
    return api.nvim_create_augroup("user_" .. name, { clear = true })
end

-- —————————— 复制文本高亮提示 ——————————
api.nvim_create_autocmd("TextYankPost", {
    group = augroup("highlight_yank"),
    pattern = "*",
    desc = "Highlight text after yanking",
    callback = function()
        vim.hl.on_yank({ timeout = 180 })
    end,
})

-- —————————— 打开文件恢复光标位置 ——————————
local cursor_restore_exclude = {
    gitcommit = true,
    gitrebase = true,
}

api.nvim_create_autocmd("BufWinEnter", {
    group = augroup("restore_cursor"),
    pattern = "*",
    desc = "Restore cursor to the last known position",
    callback = function(event)
        if vim.bo[event.buf].buftype ~= "" or cursor_restore_exclude[vim.bo[event.buf].filetype] then
            return
        end

        if vim.b[event.buf].user_cursor_restored then
            return
        end
        vim.b[event.buf].user_cursor_restored = true

        local mark = api.nvim_buf_get_mark(event.buf, '"')
        local line_count = api.nvim_buf_line_count(event.buf)
        if mark[1] <= 0 or mark[1] > line_count then
            return
        end

        local win = api.nvim_get_current_win()
        if api.nvim_win_get_buf(win) ~= event.buf then
            win = vim.fn.bufwinid(event.buf)
        end
        if win == -1 or not api.nvim_win_is_valid(win) then
            return
        end

        local line = api.nvim_buf_get_lines(event.buf, mark[1] - 1, mark[1], false)[1] or ""
        local position = { mark[1], math.min(mark[2], #line) }
        pcall(api.nvim_win_set_cursor, win, position)
    end,
})

-- —————————— 保存前自动创建父级目录 ——————————
api.nvim_create_autocmd("BufWritePre", {
    group = augroup("create_parent_dir"),
    pattern = "*",
    desc = "Create missing parent directories before writing",
    callback = function(event)
        if vim.bo[event.buf].buftype ~= "" then
            return
        end

        local file = api.nvim_buf_get_name(event.buf)
        if file == "" or file:match("^%a[%w+.-]*://") then
            return
        end

        local dir = vim.fs.dirname(vim.fs.normalize(file))
        if dir and dir ~= "" and vim.fn.isdirectory(dir) == 0 then
            vim.fn.mkdir(dir, "p")
        end
    end,
})

-- —————————— 特定窗口按 q 快速关闭 ——————————
api.nvim_create_autocmd("FileType", {
    group = augroup("close_with_q"),
    pattern = {
        "checkhealth",
        "help",
        "lspinfo",
        "qf",
        "query",
        "startuptime",
    },
    desc = "Close temporary windows with q",
    callback = function(event)
        -- FileType 也可能属于真实的可编辑文件（例如 Tree-sitter query）。
        -- 只处理 help、quickfix、nofile 等特殊缓冲区，避免覆盖普通文件的 q。
        if vim.bo[event.buf].buftype == "" then
            return
        end

        vim.bo[event.buf].buflisted = false
        vim.keymap.set("n", "q", "<cmd>quit<CR>", {
            buffer = event.buf,
            silent = true,
            nowait = true,
            desc = "Close window",
        })
    end,
})

-- —————————— 禁用自动续写注释 ——————————
api.nvim_create_autocmd("FileType", {
    group = augroup("format_options"),
    pattern = "*",
    desc = "Disable automatic comment continuation",
    callback = function()
        vim.opt_local.formatoptions:remove({ "c", "r", "o" })
    end,
})

-- —————————— 检查文件是否被外部修改 ——————————
api.nvim_create_autocmd({ "FocusGained", "TermClose", "TermLeave" }, {
    group = augroup("check_external_changes"),
    pattern = "*",
    desc = "Check for external file changes",
    callback = function()
        if vim.fn.getcmdwintype() == "" then
            vim.cmd.checktime()
        end
    end,
})
