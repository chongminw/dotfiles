# Ghostty 配置

当前以本机 Ghostty 1.3.1-arch2 校验。配置集中在 `config.ghostty`，少量设置直接在此文件修改。

| 配置 | 当前选择 |
| --- | --- |
| 字体 | JetBrainsMono Nerd Font，12 pt |
| 主题 | Dracula |
| 留白 | 左右 6 pt，上下 4 pt，并平衡网格取整后的边缘空隙 |
| 鼠标 | 输入时隐藏，移动后显示 |
| 回滚缓冲 | 每个终端窗口、标签页或分屏上限 32 MiB，按需分配 |
| 分屏尺寸快捷键 | 暂时停用，等待 GTK 分屏布局问题修复 |
| 关闭确认 | 关闭，沿用已有选择 |

留白单位是 pt，会随屏幕 DPI 缩放，不是固定像素。

## 检查与生效

```sh
ghostty +validate-config
ghostty +show-config
ghostty +list-keybinds --plain
```

保存后按 `Ctrl+Shift+,` 重载配置。窗口留白和回滚缓冲上限只对新窗口、新标签页或新分屏生效；
新开一个终端窗口即可加载全部设置，无需关闭正在运行任务的窗口。

单实例模式下，从 Niri 再次启动 Ghostty 可能复用原进程；应先重载配置，再新建窗口。
也可按 `Ctrl+Shift+P`，在命令面板选择 `Reload Config`。
`+validate-config` 和 `+list-keybinds` 检查的是磁盘上的配置，不能证明已有窗口已加载新绑定。

候选文件可单独校验：

```sh
ghostty +validate-config --config-file=/path/to/config.ghostty
```

本版本的 `+validate-config` 使用 `--config-file` 指定候选文件；可运行 `ghostty +validate-config --help` 查看支持的参数。

## Niri 下的分屏操作

| 快捷键 | 功能 |
| --- | --- |
| `Ctrl+Shift+O` | 向右分屏 |
| `Ctrl+Shift+E` | 向下分屏 |
| `Ctrl+Alt+方向键` | 聚焦相邻分屏 |
| `Ctrl+Alt+Shift+方向键` | 暂停，忽略输入 |
| `Ctrl+Shift+Enter` | 切换当前分屏放大 |
| `Ctrl+Shift+PageUp/PageDown` | 跳转到上一个或下一个命令提示符 |

关闭当前分屏时，在该分屏中执行 `exit`，或在空命令提示符处按 `Ctrl+D`；
其余分屏会自动扩展。`Ctrl+Shift+W` 会关闭当前整个标签页及其中所有分屏。

目前将 `Ctrl+Alt+Shift+方向键` 和 Ghostty 默认的 `Super+Ctrl+Shift+方向键` 都设为 `ignore`，
暂停通过快捷键调整分屏尺寸，同时避免把该组合的方向键字符送入终端。
Niri 的跨显示器移动窗口列快捷键保持原样；创建、聚焦及放大分屏的快捷键继续沿用 Ghostty 默认值。

Ghostty 1.3.1 的 GTK 分屏实现存在快速调整时短暂显示错误尺寸、随后跳回的已知问题，
与快捷键冲突或尺寸数字提示框是不同现象。Ghostty 1.4.0 已包含
[分屏尺寸同步修复](https://github.com/ghostty-org/ghostty/pull/13414)。
若分隔线和文字来回跳动，应核对程序版本；仅修改调整步长或关闭 `resize-overlay` 不能可靠修复布局问题。
本机升级并确认修复后，可仅将 `Ctrl+Alt+Shift+方向键` 四条恢复为对应的 `resize_split:方向,10`，再重载配置。
`Super+Ctrl+Shift+方向键` 在 Ghostty 内继续保留 `ignore`，由 Niri 负责跨显示器移动窗口列。

## 回滚缓冲

`scrollback-limit = 33554432` 把回滚缓冲上限从本版本默认的 10,000,000 字节提高到 32 MiB，
便于查找较长的构建或日志输出。缓冲按需分配，每个窗口、标签页和分屏分别计量，包含当前可见屏幕；
多个终端的实际内存占用可能累加。此项不影响 Bash 命令历史，命令历史仍由 barc 管理。

## 默认行为与职责

- Ghostty 默认自动检测 Bash 并加载 Shell 集成，提供目录报告、命令提示标记等功能；无需在 barc 或 `.bashrc` 中重复加载集成脚本。
- 新窗口、标签页和分屏默认继承工作目录，不需要重复添加配置。
- Niri 负责窗口布局和装饰偏好，Ghostty 沿用自动装饰选择。
- `Ctrl+Shift+C/V` 复制粘贴，`Ctrl+Shift+F` 搜索，`Ctrl+Shift+P` 打开命令面板。
- 中文字形和符号沿用 Fontconfig 回退。查找字体问题时可运行 `fc-match 'JetBrainsMono Nerd Font'`。

本机完整选项说明位于 `/usr/share/ghostty/doc/ghostty.5.md`，
也可运行 `ghostty +show-config --default --docs` 查看当前版本的默认值与说明。

官方参考：[回滚缓冲配置](https://ghostty.org/docs/config/reference#scrollback-limit)、
[分屏尺寸动作](https://ghostty.org/docs/config/keybind/reference#resize_split)。
