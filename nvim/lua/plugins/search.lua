return {
    {
        "nvim-telescope/telescope.nvim",
        version = "*",
        cmd = "Telescope",
        keys = {
            {
                "<leader>ff",
                "<cmd>Telescope find_files<CR>",
                desc = "查找文件",
            },
            {
                "<leader>fg",
                "<cmd>Telescope live_grep<CR>",
                desc = "使用 ripgrep 搜索文本",
            },
            {
                "<leader>fb",
                "<cmd>Telescope buffers<CR>",
                desc = "查找缓冲区",
            },
            {
                "<leader>fr",
                "<cmd>Telescope oldfiles<CR>",
                desc = "最近文件",
            },
        },
        dependencies = {
            "nvim-lua/plenary.nvim",
        },
        opts = {
            pickers = {
                find_files = {
                    hidden = true,
                },
                live_grep = {
                    additional_args = function()
                        return { "--hidden" }
                    end,
                },
            },
        },
    },
}
