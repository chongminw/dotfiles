local lazy_path = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"

if not vim.uv.fs_stat(lazy_path) then
    local lazy_repo = "https://github.com/folke/lazy.nvim.git"
    local output = vim.fn.system({
        "git",
        "clone",
        "--filter=blob:none",
        "--branch=stable",
        lazy_repo,
        lazy_path,
    })

    if vim.v.shell_error ~= 0 then
        error("Failed to clone lazy.nvim:\n" .. output)
    end
end

vim.opt.rtp:prepend(lazy_path)

require("lazy").setup({
    spec = {
        { import = "plugins" },
    },
})
