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

local config = vim.deepcopy(defaults)
local components = {}

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

local file_sizes = {}

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
        file_sizes[bufnr] = false
        return
    end

    local stat = uv.fs_stat(api.nvim_buf_get_name(bufnr))
    file_sizes[bufnr] = stat and stat.size and format_file_size(stat.size) or false
end

local diagnostic_styles = {
    {
        severity = vim.diagnostic.severity.ERROR,
        icon = "\u{f057} ",
        label = "E:",
        highlight = "StatuslineDiagnosticError",
    },
    {
        severity = vim.diagnostic.severity.WARN,
        icon = "\u{f071} ",
        label = "W:",
        highlight = "StatuslineDiagnosticWarn",
    },
}

local function format_diagnostics(counts)
    local result = {}

    for _, style in ipairs(diagnostic_styles) do
        local count = counts[style.severity] or 0
        if count > 0 then
            local label = config.icons_enabled and style.icon or style.label
            result[#result + 1] = string.format(
                "%%#%s#%s%d%%#StatusLine#",
                style.highlight,
                label,
                count
            )
        end
    end

    return table.concat(result, " ")
end

-- —————————— 状态栏组件 ——————————
function components.mode()
    local definition = modes[mode_kind(api.nvim_get_mode().mode)] or modes.unknown
    local label = definition.name

    if config.icons_enabled then
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

function components.filename(bufnr, width)
    local name = api.nvim_buf_get_name(bufnr)

    if name == "" then
        return "[No Name]"
    end

    if width < config.widths.medium then
        name = vim.fs.basename(name)
    else
        name = vim.fn.fnamemodify(name, ":~:.")
    end

    return "%<" .. escape_statusline(name)
end

function components.file_flags(bufnr)
    local flags = {}

    if vim.bo[bufnr].modified then
        flags[#flags + 1] = "%#StatuslineModified#[+]%#StatusLine#"
    end

    if vim.bo[bufnr].readonly or not vim.bo[bufnr].modifiable then
        flags[#flags + 1] = "%#StatuslineReadonly#[RO]%#StatusLine#"
    end

    return table.concat(flags, " ")
end

function components.file_type(bufnr)
    local filetype = vim.bo[bufnr].filetype
    filetype = filetype ~= "" and filetype or "text"

    if not config.icons_enabled then
        return escape_statusline(filetype)
    end

    local icon = icons.get("filetype", filetype)
    return escape_statusline(icon .. " " .. filetype)
end

function components.file_size(bufnr)
    if not config.show_file_size or vim.bo[bufnr].modified then
        return ""
    end

    if file_sizes[bufnr] == nil then
        return ""
    end

    local size = file_sizes[bufnr]
    if not size then
        return ""
    end

    if config.icons_enabled then
        return "\u{f016} " .. size
    end

    return size
end

function components.diagnostics(bufnr)
    if not config.show_diagnostics then
        return ""
    end

    local status = vim.diagnostic.status(bufnr)
    -- 原生组件会重置高亮，后续组件继续使用当前状态栏的配色。
    return status ~= "" and (status .. "%#StatusLine#") or ""
end

-- —————————— 状态栏渲染 ——————————
function M.render()
    local _, bufnr = get_context()
    local width = vim.o.columns
    local separator = " › "

    local left = join_nonempty({
        components.mode(),
        join_nonempty({
            components.filename(bufnr, width),
            components.file_flags(bufnr),
        }, " "),
    }, separator)

    local right = {
        width >= config.widths.medium and components.diagnostics(bufnr) or "",
        width >= config.widths.medium and components.file_type(bufnr) or "",
        width >= config.widths.wide and components.file_size(bufnr) or "",
        "%l:%c",
        "%P",
    }

    return " " .. left .. "%=" .. join_nonempty(right, separator) .. " "
end

-- —————————— 高亮与缓存 ——————————
local function setup_highlights()
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

local function setup_autocmds()
    local group = api.nvim_create_augroup("UserStatusline", {
        clear = true,
    })

    api.nvim_create_autocmd("ColorScheme", {
        group = group,
        pattern = "*",
        desc = "Refresh statusline highlights",
        callback = function()
            setup_highlights()
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
            if file_sizes[event.buf] == nil then
                update_file_size(event.buf)
            end
            redraw_statusline()
        end,
    })

    api.nvim_create_autocmd({ "BufDelete", "BufWipeout" }, {
        group = group,
        pattern = "*",
        desc = "Clear statusline buffer cache",
        callback = function(event)
            file_sizes[event.buf] = nil
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
    config = vim.tbl_deep_extend("force", vim.deepcopy(defaults), opts or {})

    _G.CustomStatusline = {
        render = M.render,
    }

    vim.o.laststatus = 3
    setup_highlights()
    vim.diagnostic.config({ status = { format = format_diagnostics } })
    setup_autocmds()
    update_file_size(api.nvim_get_current_buf())

    vim.o.statusline = "%!v:lua.CustomStatusline.render()"
    redraw_statusline()
end

return M
