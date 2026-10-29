# Desktop 配置源码

集中阅读和归档当前桌面的配置、脚本、说明及测试，保留现有源码和调用关系。

```text
desktop/
├── niri/                 # 配置入口、模块、快捷键、截图脚本及测试
├── mako/                 # 通知服务配置
├── waybar/               # 状态栏配置、天气与通知脚本及测试
└── commenu/
    ├── bin/commenu       # 公共菜单命令入口
    └── lib/              # 启动器、电源菜单和公共会话管理
```

## 阅读入口

- [niri/README.md](niri/README.md)：模块职责及快捷键；配置入口为 [niri/config.kdl](niri/config.kdl)。
- [mako/config](mako/config)：通知外观、勿扰及 Waybar 通知操作需要的规则。
- [waybar/README.md](waybar/README.md)：状态栏模块和脚本说明；配置入口为 [waybar/config.jsonc](waybar/config.jsonc)。
- [commenu/lib/README.md](commenu/lib/README.md)：公共菜单说明；命令入口为 [commenu/bin/commenu](commenu/bin/commenu)。

## 组件关系与现用位置

Niri 的启动器快捷键和 Waybar 的启动器、电源菜单共同调用 `commenu`。
Waybar 的通知菜单还引用 `commenu/lib/menu-common.sh`，共享菜单互斥与会话管理。
Waybar 的通知状态、勿扰、历史恢复与清理脚本配合 mako 配置使用。

| 归档位置 | 当前系统使用的位置 |
| --- | --- |
| `niri/` | `~/.config/niri/` |
| `mako/` | `~/.config/mako/` |
| `waybar/` | `~/.config/waybar/` |
| `commenu/bin/commenu` | `~/.local/bin/commenu` |
| `commenu/lib/` | `~/.local/lib/commenu/` |

## 本机设置与外部资源

- `niri/local.kdl` 保留本机显示器、截图目录、壁纸路径及 polkit 认证代理设置。
- 壁纸等外部资源未随源码收纳，配置仍保留原路径。
- `waybar/config.jsonc` 保留本机无线网卡设置；天气脚本保留当前站点和时区。
- 程序、字体等依赖见各组件 README。
- 现有测试保留原路径约定；归档布局下运行 Waybar 离线测试时，可用 `COMMENU_TEST_ROOT` 指定 `commenu/lib/`，用 `COMMENU_TEST_BIN` 指定 `commenu/bin/commenu`。

本目录用于源码归档，不包含部署脚本。Python 缓存、运行数据和改名前备份不收纳。
