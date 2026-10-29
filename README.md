# dotfiles

个人 Bash 与 Wayland 桌面配置的源码归档，用于集中阅读、记录修改和保留迁移参考。

```text
dotfiles/
├── barc/
│   ├── etc/                  # 系统 Bash 入口
│   ├── home/                 # 用户 Shell 入口、barc 设置和桌面会话入口
│   └── usr/local/            # barc 程序源码及命令入口
└── desktop/
    ├── niri/                 # 窗口管理器配置、快捷键及截图脚本
    ├── mako/                 # 通知服务配置
    ├── waybar/               # 状态栏配置、天气与通知脚本
    ├── ghostty/              # 终端配置、回滚缓冲和分屏快捷键
    └── commenu/
        ├── bin/commenu       # 公共菜单命令入口
        └── lib/              # 启动器、电源菜单和菜单会话管理
```

## 阅读入口

| 组件 | 文档或配置 |
| --- | --- |
| barc | [模块化 Bash 配置说明](barc/usr/local/lib/barc/README.md) |
| 桌面集合 | [目录导航、组件关系与现用位置](desktop/README.md) |
| niri | [配置维护说明](desktop/niri/README.md) |
| mako | [通知配置](desktop/mako/config) |
| Waybar | [状态栏与脚本说明](desktop/waybar/README.md) |
| Ghostty | [终端配置说明](desktop/ghostty/README.md) |
| commenu | [公共菜单说明](desktop/commenu/lib/README.md) |

## 目录与组件关系

`barc` 同时涉及系统入口、用户入口和程序源码，保留 `etc/`、`home/`、`usr/` 的系统路径镜像。
其中 `home/` 表示用户主目录下的内容；桌面组件各自直接收纳配置和源码。

barc 的用户登录入口加载 [session.bash](barc/home/.config/barc/session.bash)，满足 tty1 等条件时启动 `niri-session -l`。
Niri 和 Waybar 共用 `commenu` 提供启动器、电源菜单；Waybar 的通知菜单也复用其菜单会话管理。
Waybar 的通知状态、勿扰和历史操作配合 mako 配置使用。

## 维护方式

本仓库是现用配置的副本。运行中的文件位于 `~/.config`、`~/.local`，以及系统的 `/etc`、`/usr/local` 等位置。
修改现用文件后，需要手动同步到仓库对应位置，检查差异后再提交；编辑仓库文件后，现用配置仍需另行同步。
同步时保留脚本的可执行权限，排除缓存、运行数据和备份。

显示器、网卡、天气站点和壁纸路径等本机设置，以及未收纳的外部资源，见 [桌面集合说明](desktop/README.md#本机设置与外部资源)。
当前收纳配置、源码、文档及测试，不包含部署脚本。
