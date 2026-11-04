local M = {}

local api = vim.api
local icons = require("mini.icons")
local uv = vim.uv

local defaults = {
    icons_enabled = true,
    show_diagnostics = true,
    show_file_size = true,
    widths = {
        medium = 90,
        wide = 130,
    },
}

M.config = vim.deepcopy(defaults)
M.components = {}

-- —————————— 模式定义 ——————————
-- 行/块变体复用基础模式的高亮组，颜色来源只在基础模式中定义。
local modes = {
    normal = {
        name = "Normal",
        icon = "\u{f121}",
        highlight = "StatuslineModeNormal",
        source = "Function",
    },
    operator = {
        name = "Operator",
        icon = "\u{f121}",
        highlight = "StatuslineModeOperator",
        source = "Special",
    },
    insert = {
        name = "Insert",
        icon = "\u{f11c}",
        highlight = "StatuslineModeInsert",
        source = "String",
    },
    visual = {
        name = "Visual",
        icon = "\u{f0168}",
        highlight = "StatuslineModeVisual",
        source = "Constant",
    },
    visual_line = {
        name = "V-line",
        icon = "\u{f0168}",
        highlight = "StatuslineModeVisual",
    },
    visual_block = {
        name = "V-block",
        icon = "\u{f0168}",
        highlight = "StatuslineModeVisual",
    },
    select = {
        name = "Select",
        icon = "\u{f0c5}",
        highlight = "StatuslineModeSelect",
        source = "Type",
    },
    select_line = {
        name = "S-line",
        icon = "\u{f0c5}",
        highlight = "StatuslineModeSelect",
    },
    select_block = {
        name = "S-block",
        icon = "\u{f0c5}",
        highlight = "StatuslineModeSelect",
    },
    replace = {
        name = "Replace",
        icon = "\u{f044}",
        highlight = "StatuslineModeReplace",
        source = "DiagnosticError",
    },
    command = {
        name = "Command",
        icon = "\u{f120}",
        highlight = "StatuslineModeCommand",
        source = "Identifier",
    },
    terminal = {
        name = "Terminal",
        icon = "\u{f120}",
        highlight = "StatuslineModeTerminal",
        source = "DiagnosticOk",
    },
    prompt = {
        name = "Prompt",
        icon = "\u{f059}",
        highlight = "StatuslineModePrompt",
        source = "WarningMsg",
    },
    shell = {
        name = "Shell",
        icon = "\u{f489}",
        highlight = "StatuslineModeShell",
        source = "PreProc",
    },
    unknown = {
        name = "Unknown",
        icon = "\u{f059}",
        highlight = "StatuslineModeUnknown",
        source = "Comment",
    },
}

local cache = {
    diagnostics = {},
    file_sizes = {},
}

-- —————————— 通用工具函数 ——————————
local function escape_statusline(value)
    return tostring(value):gsub("%%", "%%%%")
end

local function join_nonempty(items, separator)
    local result = {}

    for _, item in ipairs(items) do
        if item and item ~= "" then
            result[#result + 1] = item
        end
    end

    return table.concat(result, separator)
end

local function format_file_size(size)
    size = tonumber(size) or 0

    if size < 1024 then
        return string.format("%dB", size)
    elseif size < 1024 * 1024 then
        return string.format("%.1fK", size / 1024)
    elseif size < 1024 * 1024 * 1024 then
        return string.format("%.1fM", size / 1024 / 1024)
    end

    return string.format("%.1fG", size / 1024 / 1024 / 1024)
end

local function get_context()
    local win = tonumber(vim.g.statusline_winid) or api.nvim_get_current_win()

    if not api.nvim_win_is_valid(win) then
        win = api.nvim_get_current_win()
    end

    return win, api.nvim_win_get_buf(win)
end

local function is_normal_file_buffer(bufnr)
    if not api.nvim_buf_is_valid(bufnr) or vim.bo[bufnr].buftype ~= "" then
        return false
    end

    local name = api.nvim_buf_get_name(bufnr)
    return name ~= "" and not name:match("^%a[%w+.-]*://")
end

local function redraw_statusline()
    vim.cmd.redrawstatus()
end

local function mode_kind(mode)
    if mode:sub(1, 1) == "\22" then
        return "visual_block"
    elseif mode == "\19" then
        return "select_block"
    elseif mode:sub(1, 2) == "no" then
        return "operator"
    elseif mode:sub(1, 1) == "n" then
        return "normal"
    elseif mode:sub(1, 1) == "i" then
        return "insert"
    elseif mode == "V" or mode:sub(1, 2) == "Vs" then
        return "visual_line"
    elseif mode:sub(1, 1) == "v" then
        return "visual"
    elseif mode == "S" then
        return "select_line"
    elseif mode:sub(1, 1) == "s" then
        return "select"
    elseif mode:sub(1, 1) == "R" then
        return "replace"
    elseif mode:sub(1, 1) == "c" then
        return "command"
    elseif mode:sub(1, 1) == "t" then
        return "terminal"
    elseif mode:sub(1, 1) == "r" then
        return "prompt"
    elseif mode == "!" then
        return "shell"
    end

    return "unknown"
end

local function get_highlight(name)
    local ok, value = pcall(api.nvim_get_hl, 0, {
        name = name,
        link = false,
    })

    return ok and value or {}
end

local function set_mode_highlight(name, source)
    local statusline = get_highlight("StatusLine")
    local normal = get_highlight("Normal")
    local accent = get_highlight(source)
    local spec = {
        bold = true,
    }

    spec.bg = accent.fg
    spec.fg = statusline.bg or normal.bg or statusline.fg

    if not spec.bg then
        spec.reverse = true
    end

    api.nvim_set_hl(0, name, spec)
end

local function set_inline_highlight(name, source)
    local statusline = get_highlight("StatusLine")
    local accent = get_highlight(source)

    api.nvim_set_hl(0, name, {
        fg = accent.fg,
        bg = statusline.bg,
        bold = true,
    })
end

local function update_file_size(bufnr)
    if not is_normal_file_buffer(bufnr) then
        cache.file_sizes[bufnr] = false
        return
    end

    local stat = uv.fs_stat(api.nvim_buf_get_name(bufnr))
    cache.file_sizes[bufnr] = stat and stat.size and format_file_size(stat.size) or false
end

local function update_diagnostics(bufnr)
    if not api.nvim_buf_is_valid(bufnr) then
        return
    end

    local counts = vim.diagnostic.count(bufnr)
    cache.diagnostics[bufnr] = {
        errors = counts[vim.diagnostic.severity.ERROR] or 0,
        warnings = counts[vim.diagnostic.severity.WARN] or 0,
    }
end

-- —————————— 状态栏组件 ——————————
function M.components.mode()
    local definition = modes[mode_kind(api.nvim_get_mode().mode)] or modes.unknown
    local label = definition.name

    if M.config.icons_enabled then
        label = definition.icon .. "  " .. label
    end

    return table.concat({
        "%#",
        definition.highlight,
        "# ",
        escape_statusline(label),
        " %#StatusLine#",
    })
end

function M.components.filename(bufnr, width)
    local name = api.nvim_buf_get_name(bufnr)

    if name == "" then
        return "[No Name]"
    end

    if width < M.config.widths.medium then
        name = vim.fs.basename(name)
    else
        name = vim.fn.fnamemodify(name, ":~:.")
    end

    return "%<" .. escape_statusline(name)
end

function M.components.file_flags(bufnr)
    local flags = {}

    if vim.bo[bufnr].modified then
        flags[#flags + 1] = "%#StatuslineModified#[+]%#StatusLine#"
    end

    if vim.bo[bufnr].readonly or not vim.bo[bufnr].modifiable then
        flags[#flags + 1] = "%#StatuslineReadonly#[RO]%#StatusLine#"
    end

    return table.concat(flags, " ")
end

function M.components.file_type(bufnr)
    local filetype = vim.bo[bufnr].filetype
    filetype = filetype ~= "" and filetype or "text"

    if not M.config.icons_enabled then
        return escape_statusline(filetype)
    end

    local icon = icons.get("filetype", filetype)
    return escape_statusline(icon .. " " .. filetype)
end

function M.components.file_size(bufnr)
    if not M.config.show_file_size or vim.bo[bufnr].modified then
        return ""
    end

    if cache.file_sizes[bufnr] == nil then
        return ""
    end

    local size = cache.file_sizes[bufnr]
    if not size then
        return ""
    end

    if M.config.icons_enabled then
        return "\u{f016} " .. size
    end

    return size
end

function M.components.diagnostics(bufnr)
    if not M.config.show_diagnostics then
        return ""
    end

    local diagnostics = cache.diagnostics[bufnr]
    if not diagnostics or (diagnostics.errors == 0 and diagnostics.warnings == 0) then
        return ""
    end

    local result = {}
    if diagnostics.errors > 0 then
        local label = M.config.icons_enabled and "\u{f057} " or "E:"
        result[#result + 1] = string.format(
            "%%#StatuslineDiagnosticError#%s%d%%#StatusLine#",
            label,
            diagnostics.errors
        )
    end

    if diagnostics.warnings > 0 then
        local label = M.config.icons_enabled and "\u{f071} " or "W:"
        result[#result + 1] = string.format(
            "%%#StatuslineDiagnosticWarn#%s%d%%#StatusLine#",
            label,
            diagnostics.warnings
        )
    end

    return table.concat(result, " ")
end

-- —————————— 状态栏渲染 ——————————
function M.render()
    local _, bufnr = get_context()
    local width = vim.o.columns
    local separator = " › "

    local left = join_nonempty({
        M.components.mode(),
        join_nonempty({
            M.components.filename(bufnr, width),
            M.components.file_flags(bufnr),
        }, " "),
    }, separator)

    local right = {
        width >= M.config.widths.medium and M.components.diagnostics(bufnr) or "",
        width >= M.config.widths.medium and M.components.file_type(bufnr) or "",
        width >= M.config.widths.wide and M.components.file_size(bufnr) or "",
        "%l:%c",
        "%P",
    }

    return " " .. left .. "%=" .. join_nonempty(right, separator) .. " "
end

-- —————————— 高亮与缓存 ——————————
function M.setup_highlights()
    for _, definition in pairs(modes) do
        if definition.source then
            set_mode_highlight(definition.highlight, definition.source)
        end
    end

    set_inline_highlight("StatuslineDiagnosticError", "DiagnosticError")
    set_inline_highlight("StatuslineDiagnosticWarn", "DiagnosticWarn")
    set_inline_highlight("StatuslineModified", "DiagnosticWarn")
    set_inline_highlight("StatuslineReadonly", "DiagnosticError")
end

function M.refresh(bufnr)
    bufnr = bufnr or api.nvim_get_current_buf()
    update_file_size(bufnr)
    update_diagnostics(bufnr)
    redraw_statusline()
end

local function setup_autocmds()
    local group = api.nvim_create_augroup("UserStatusline", {
        clear = true,
    })

    api.nvim_create_autocmd("ColorScheme", {
        group = group,
        pattern = "*",
        desc = "Refresh statusline highlights",
        callback = function()
            M.setup_highlights()
            redraw_statusline()
        end,
    })

    api.nvim_create_autocmd({ "BufFilePost", "BufReadPost", "BufWritePost", "FileChangedShellPost" }, {
        group = group,
        pattern = "*",
        desc = "Refresh cached statusline file data",
        callback = function(event)
            update_file_size(event.buf)
            redraw_statusline()
        end,
    })

    api.nvim_create_autocmd("BufEnter", {
        group = group,
        pattern = "*",
        desc = "Initialize statusline buffer cache",
        callback = function(event)
            if cache.file_sizes[event.buf] == nil then
                update_file_size(event.buf)
            end
            if cache.diagnostics[event.buf] == nil then
                update_diagnostics(event.buf)
            end
            redraw_statusline()
        end,
    })

    api.nvim_create_autocmd("DiagnosticChanged", {
        group = group,
        pattern = "*",
        desc = "Refresh cached statusline diagnostics",
        callback = function(event)
            update_diagnostics(event.buf)
            redraw_statusline()
        end,
    })

    api.nvim_create_autocmd({ "BufDelete", "BufWipeout" }, {
        group = group,
        pattern = "*",
        desc = "Clear statusline buffer cache",
        callback = function(event)
            cache.file_sizes[event.buf] = nil
            cache.diagnostics[event.buf] = nil
        end,
    })

    api.nvim_create_autocmd({ "DirChanged", "ModeChanged", "VimResized" }, {
        group = group,
        pattern = "*",
        desc = "Redraw the global statusline",
        callback = redraw_statusline,
    })
end

-- —————————— 初始化 ——————————
function M.setup(opts)
    M.config = vim.tbl_deep_extend("force", vim.deepcopy(defaults), opts or {})

    _G.CustomStatusline = {
        render = M.render,
    }

    vim.o.laststatus = 3
    M.setup_highlights()
    setup_autocmds()
    M.refresh()

    vim.o.statusline = "%!v:lua.CustomStatusline.render()"
end

return M
