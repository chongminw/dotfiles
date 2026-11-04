return {
    {
        "MeanderingProgrammer/render-markdown.nvim",
        branch = "main",
        version = "*",
        ft = { "markdown" },
        cmd = "RenderMarkdown",
        dependencies = {
            "nvim-mini/mini.icons",
        },
        keys = {
            {
                "<leader>mr",
                "<cmd>RenderMarkdown toggle<CR>",
                desc = "切换 Markdown 渲染",
                ft = "markdown",
            },
        },
        opts = {
            file_types = { "markdown" },
            -- 光标所在行保持渲染，避免移动时切换为源码。
            anti_conceal = { enabled = false },
            injections = {
                gitcommit = { enabled = false },
            },
            -- 仅使用 Markdown 解析器，关闭需要额外依赖的渲染功能。
            html = { enabled = false },
            latex = { enabled = false },
            yaml = { enabled = false },
        },
    },
}
