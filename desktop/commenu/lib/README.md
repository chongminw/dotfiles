# 公共桌面菜单

应用启动器和电源菜单由用户命令 `~/.local/bin/commenu` 提供，实现位于
`~/.local/lib/commenu/`。Niri 和 Waybar 可分别调用，公共菜单不依赖 Waybar 配置目录。

```sh
"$HOME/.local/bin/commenu" launcher
"$HOME/.local/bin/commenu" power
"$HOME/.local/bin/commenu" --help
```

`launcher` 后的参数原样传给 fuzzel；`power` 不接受额外参数。
启动器与电源菜单沿用 fuzzel 原生主题，重复调用关闭当前菜单，切换入口会关闭另一菜单。
电源菜单选中 Logout、Reboot、Shutdown 后执行对应操作，Esc 取消。

## 文件职责

| 文件 | 用途 |
| --- | --- |
| `~/.local/bin/commenu` | 校验参数并分派至固定菜单实现 |
| `toggle-launcher.sh` | 应用启动器内容 |
| `powermenu.sh` | 电源菜单内容及选中动作 |
| `menu-common.sh` | 互斥、进程身份核对、会话登记和退出清理 |

Waybar 的通知菜单仍在 `~/.config/waybar/scripts/notification-menu.sh`，
只共用 `menu-common.sh` 的生命周期管理，通知读取和清理逻辑继续由 Waybar 维护。
三种菜单互相切换时仍会关闭已登记的另一菜单，不影响其他 fuzzel 窗口。

## 维护

Niri 和 Waybar 统一调用 `~/.local/bin/commenu`，修改菜单功能时只改本目录中的实现。
`--run` 是菜单生命周期管理使用的内部工作进程入口。

运行状态使用 `${XDG_RUNTIME_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}}/waybar`，
生命周期管理使用 `wb_menu_*` 内部名称及对应的 fuzzel namespace。公共菜单共用同一把菜单锁，
通知恢复与清理也使用同一把 `history.lock`。不要单独修改一方的锁目录。

依赖 Bash、fuzzel、Ghostty、`flock`、`setsid`、`pgrep` 和标准文件工具；
电源操作还使用 Niri 和 systemd 用户会话所在系统。

离线回归测试位于 `~/.config/waybar/tests`，使用临时 HOME 和假桌面命令：

```sh
python3 -B -m unittest discover -s "$HOME/.config/waybar/tests" -v
```

迁移机器时一并复制公共命令和本目录；Waybar 的通知菜单也依赖此公共实现。
