# Waybar 极简配置

左侧启动器和工作区，中间时间和天气，右侧依次为托盘、内存、磁盘、无线、通知和电源。
固定使用本机无线网卡 `wlp3s0` 和长治天气站点。

## 调整位置

- `config.jsonc`：模块排列、栏高、间距、刷新周期和点击动作；省略默认行为及可共用的状态格式。
- `style.css`：字体、颜色、模块留白和托盘入口样式；天气图标和温度的字号、粗细也统一在此调整。
- `scripts/weather.py`：站点、请求超时和天气图标，Waybar 直接调用。
- `~/.local/bin/commenu`：公共桌面菜单入口，`launcher` 打开应用启动器，`power` 打开电源菜单；实现与共用生命周期管理位于 `~/.local/lib/commenu/`。
- `scripts/notification.sh` / `notification-status.py` / `history.py`：通知数量、勿扰状态与切换、历史恢复，配合 `~/.config/mako/config` 使用。
- `scripts/mako_client.py`：通知脚本共用的 D-Bus 客户端、通知 ID 校验和异常分类；导入模块时不连接桌面。
- `scripts/notification-menu.sh` / `notification-cleanup.py`：中键清理菜单、通知快照与按范围永久删除。

## 依赖与启动

桌面使用 Niri、fuzzel、mako、Ghostty、NetworkManager 和 JetBrainsMono Nerd Font。
脚本依赖 Bash、Python 3、Python GI/Gio、curl，以及 `flock`、`setsid`、`pgrep`、`timeout`。
Waybar 由 `graphical-session.target` 下的用户级 `waybar.service` 启动；Waybar 和 Niri 的 `Mod+D` 都调用公共 `commenu launcher` 命令。
迁移配置时一并保留 `~/.local/bin/commenu` 和 `~/.local/lib/commenu/`。可运行 `~/.local/bin/commenu --help` 查看用法。

## 行为约定

- 整栏常规模块左右各留 3px，与全局 6px 间隔组成 12px 模块间距，左右两端等量留白。工作区数字间也留 12px，组首尾沿用 3px，不再额外撑宽；托盘内部保持紧凑。
- 右侧统一使用 13px 等宽粗体、白色文字和 12px 模块间距，悬停不变色。数字按自然长度显示，冒号后不留空格，让模块内部比模块之间紧凑。电源入口显示同字号字母 `P`，左键仍打开电源菜单。
- 状态文字统一为 `M:24%`、`D:3%`、`S:85%`、`N:0` 的样式。无线不可用时显示 `S:--%`。通知在同一位置显示：普通状态为 `N:数量`，勿扰状态为 `Q:数量`（Quiet），左键切换勿扰，右键恢复一条历史通知，中键打开清理菜单。数量为当前和历史中可查看通知的去重总数，非未读数量，悬停显示分项。
- 清理菜单显示“清除当前通知”“清空历史记录”“全部清空”及各自数量，选中后永久删除对应记录，Esc 取消。删除范围以打开菜单时的通知快照为准，之后新增的通知 ID 保留；勿扰状态保持原样。若新历史排到队首或通知服务重启，停止继续清理并提示结果，可以重新打开菜单处理剩余记录。
- 托盘位于内存左侧，默认收起，显示 `O [ ]`；点击后以 200ms 动画向左展开，显示 `C [托盘图标]`，右括号始终固定，再次点击收起，移开鼠标保持状态。仅字母 `O` 和 `C` 使用手形指针，托盘其余区域使用普通箭头。入口始终使用默认文字颜色，文字跟随全局字号，托盘图标大小和间距在 `config.jsonc` 的 `tray` 中调整。
- 菜单沿用 fuzzel 原生主题；重复点击关闭，切换入口关闭另一菜单，只管理自己创建的进程。
- 电源菜单显示 Logout、Reboot、Shutdown 三行，选中后直接执行；Esc 或再次点击图标关闭。
- 天气每 30 分钟请求一次，不缓存；连接超时 3 秒、请求超时 8 秒。失败或数据过期时隐藏，未知天气用通用图标保留温度。
- 勿扰时新通知先隐藏，再异步归档；右键逐条恢复，不关闭全局勿扰。恢复的通知保留到手动关闭，历史受 mako 的 `max-history` 限制。

`history.py` 仅为勿扰恢复补充展示标记，普通模式直接原生恢复。历史 API 不返回内嵌 image-data，勿扰下恢复只能使用应用图标。
不要将异步归档改成 `on-notify=dismiss`：本机 mako 1.11 已出现空 surface 崩溃。
托盘文字共用原生抽屉的状态，不单独记录开关；菜单的锁和进程身份检查用于保证连点切换、不误杀其他窗口。
托盘左括号由两种状态共用，字母 `O` / `C` 独立控制显示和指针，右括号始终位于动画区域外。
清理历史时使用私有 `waybar-cleanup` 模式临时隐藏恢复的记录，结束或取消后撤销本次添加的模式。删除、勿扰切换与历史恢复共用锁；菜单显示期间不占用通知锁。清理菜单、启动器和电源菜单复用同一会话管理，互相切换时关闭已有菜单。

天气数据按获取、校验、图标选择和输出分层；通知协议与展示、历史恢复分开。通知菜单业务保留在 Waybar 中，只复用公共菜单生命周期管理。
公共菜单与通知操作共用 `waybar` 运行目录和锁文件，确保会话登记和互斥保持一致。复制配置时需一并保留公共命令和实现。

## 检查与重载

```bash
python3 -m unittest discover -s "$HOME/.config/waybar/tests" -v
systemctl --user restart waybar.service
makoctl reload
```

本机 Waybar 0.15.0 的延迟光标回调在热重载后有崩溃风险；配置变更使用 `restart`，避免保留旧进程的回调。

真实通知测试须显式使用隔离 D-Bus，会短暂显示测试弹窗，不操作用户通知历史：

```bash
dbus-run-session -- python3 "$HOME/.config/waybar/tests/check_mako_desktop.py" --isolated
```

通知删除的真实 mako 验证同样必须在隔离 D-Bus 中运行；所有测试通知保持隐藏：

```bash
dbus-run-session -- python3 "$HOME/.config/waybar/tests/check_notification_cleanup.py" --isolated
```

