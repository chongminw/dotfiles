return {
    {
        "nvim-mini/mini.icons",
        version = "*",
        lazy = false,
        config = function()
            local icons = require("mini.icons")
            icons.setup()
            icons.mock_nvim_web_devicons()
        end,
    },
    {
        "akinsho/bufferline.nvim",
        version = "*",
        event = "VeryLazy",
        dependencies = {
            "nvim-mini/mini.icons",
        },
        opts = {
            options = {
                mode = "buffers",
                always_show_bufferline = true,
                close_command = "bdelete %d",
                diagnostics = false,
                get_element_icon = function(element)
                    return require("mini.icons").get("file", element.path)
                end,
                indicator = {
                    style = "underline",
                },
                persist_buffer_sort = false,
                right_mouse_command = false,
                separator_style = "thin",
                show_buffer_close_icons = true,
                show_close_icon = true,
                sort_by = "id",
            },
        },
    },
    {
        "folke/which-key.nvim",
        version = "*",
        event = "VeryLazy",
        opts = {
            show_help = false,
            show_keys = false,
            win = {
                height = 2,
                no_overlap = false,
                padding = { 0, 0 },
                title = false,
            },
        },
    },
}
