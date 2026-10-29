# niri 配置维护

配置使用原生 KDL `include` 拆分，需要 niri 25.11 或更高版本；当前验证版本为 26.04。

`config.kdl` 是唯一入口，只声明模块和加载顺序。各子文件保留完整的 niri 顶层配置节点。

## 到哪里修改

| 文件 | 职责 |
| --- | --- |
| `modules/environment.kdl` | 语言和输入法环境变量 |
| `modules/input.kdl` | 键盘、鼠标、触摸板配置 |
| `modules/autostart.kdl` | 通用会话启动项：mako |
| `modules/behavior.kdl` | CSD 偏好和快捷键提示面板 |
| `modules/layout.kdl` | 间距、预设列宽、默认列宽、焦点框和边框 |
| `modules/animations.kdl` | 动画曲线、时长和弹簧参数 |
| `modules/window-rules.kdl` | 应用窗口规则，目前为 Firefox 画中画 |
| `modules/layer-rules.kdl` | 壁纸等 layer-shell 表面规则；概览使用当前壁纸 |
| `binds/applications.kdl` | 应用启动快捷键 |
| `binds/windows.kdl` | 窗口和列操作快捷键 |
| `binds/workspaces.kdl` | 工作区快捷键 |
| `binds/monitors.kdl` | 显示器之间聚焦和移动列 |
| `binds/system.kdl` | 帮助、截图、抑制切换、关闭屏幕和退出 |
| `local.kdl` | 本机显示器、截图路径、壁纸和认证代理 |

框选截图快捷键调用 `scripts/screenshot.sh`：`annotate` 打开标注，`copy` 直接复制。
取消框选时结束；截图完整成功后才启动标注或复制，失败不会把空内容写入剪贴板。
截图暂存在私有临时目录，命令结束时清理；`Mod+Alt+S` 仍使用 niri 原生窗口截图。

`Mod+D` 调用公共命令 `~/.local/bin/commenu launcher`。实现位于
`~/.local/lib/commenu/`，应用启动器可独立于 Waybar 配置使用，并与桌面其他菜单保持互斥。

## 加载与归属

- 所有 `include` 都写在顶层；相对路径以声明它的配置文件所在目录为基准。
- 每个配置项维护一个主要定义位置。添加新模块时，在入口明确添加 `include`。
- 后加载的配置可以覆盖前面相同的普通设置或快捷键。通用文件之间避免重复定义按键；需要本机覆盖时在最后加载的 `local.kdl` 中明确说明原因。
- `output`、`window-rule`、`workspace` 等条目按顺序插入，不按名称跨文件合并。同一台显示器的配置集中在一个文件中。
- `struts`、`preset-column-widths`、输入设备子块和单项动画配置等整体结构应在所属模块完整维护，避免分散到多个文件。
- 边框使用显式 `on` 或 `off`。子文件里的空 `border {}` 不会自动开启边框。
- 新增窗口规则保持通用规则在前、具体应用规则在后；规则增多后再按应用拆分。
- 迁移机器时先调整 `local.kdl` 中的接口名称、显示参数、资源路径和认证代理路径。
- Fcitx5 由 `/etc/xdg/autostart/org.fcitx.Fcitx5.desktop` 启动，niri 会话会启用 XDG 自动启动；不再在 KDL 中重复启动。此归属调整在下一次登录时验证。

## 概览壁纸

`modules/layer-rules.kdl` 使用 `place-within-backdrop true`，将 swaybg 的 `wallpaper` 图层放入概览背景。`modules/layout.kdl` 的 `background-color "transparent"` 让工作区透出这张铺满屏幕的壁纸。

更换壁纸工具时，先运行 `niri msg layers`，再更新匹配的 namespace。当前概览快捷键为 `Mod+O`，通常对应 `Super+O`。

详细说明见 [niri 概览背景文档](https://niri-wm.github.io/niri/Overview.html#backdrop-customization)。

## 验证

验证完整入口，确保所有子文件一起被检查：

```sh
niri validate -c "$HOME/.config/niri/config.kdl"
```

验证候选配置时，把完整目录放在临时位置，指定该目录的入口：

```sh
niri validate -c /tmp/niri-candidate/config.kdl
```

截图脚本的离线测试仅使用假命令，不连接桌面或修改剪贴板：

```sh
python3 -B -m unittest discover -s "$HOME/.config/niri/tests" -v
```

配置文件保存后由 niri 自动重载，包括已加载的子文件。启动项在会话启动时执行，修改后需在下一次会话启动时确认效果。

检查当前会话的配置加载日志：

```sh
journalctl --user -u niri.service -n 30 --no-pager
```

## 外部依赖

| 用途 | 程序或资源 |
| --- | --- |
| 应用快捷键 | `ghostty`、`commenu`、`fuzzel`、`nautilus`、`firefox` |
| 通用启动项 | `mako` |
| 输入法自动启动 | `fcitx5`，由系统 XDG 自动启动项提供 |
| 壁纸 | `swaybg` 和 `local.kdl` 指定的图片 |
| 权限认证 | `local.kdl` 指定的 polkit 认证代理 |
| 框选截图 | `grim`、`slurp`、`satty`、`wl-copy` |

`niri validate` 检查配置解析和支持的选项；外部程序及截图交互需要在桌面会话中检查。

原生 include 的详细规则见 [niri 官方文档](https://niri-wm.github.io/niri/Configuration%3A-Include.html)。
