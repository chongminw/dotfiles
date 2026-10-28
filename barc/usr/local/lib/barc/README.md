# barc 1.5.2

barc 是面向交互式 Bash 5.1 及以上版本的模块化配置。安装目录通常是
`/usr/local/lib/barc`，用户配置默认位于 `~/.config/barc`；若设置了绝对路径的
`XDG_CONFIG_HOME`，则使用 `$XDG_CONFIG_HOME/barc`。

## 帮助与状态

```bash
barc help           # 中文帮助、常用命令和添加模块说明
barc status         # 当前模块加载状态和来源，等同于 barc_status
ebrc --help         # 配置编辑说明，不依赖可选模块
```

`barc` 不带参数、`barc -h` 和 `barc --help` 都显示总帮助；`ebrc -h`
也可查看配置编辑说明。帮助只显示信息，不创建配置或打开编辑器。

帮助在支持颜色的终端使用加粗标题和彩色命令，管道及重定向输出自动使用纯文本。
设置 `NO_COLOR`（包括空值）可关闭颜色，例如 `NO_COLOR= barc help`；
`TERM` 未设置、为空或为 `dumb` 时也不着色。

## 配置入口

加载顺序为 `settings.bash → modules.conf 中的模块 → local.bash`。

| 文件 | 用途 |
| --- | --- |
| `settings.bash` | 启动参数，如编辑器、历史条数、代理地址 |
| `modules.conf` | 启用模块及其加载顺序，每行一个名称 |
| `local.bash` | 少量个人别名、函数，以及最后的覆盖 |
| `modules/<名称>.bash` | 可独立选择和排序的个人模块 |
| `session.bash` | 已有桌面会话配置，沿用原会话入口，不由模块加载器执行 |

`ebrc` 是核心管理命令；关闭 `aliases`、使用空清单或清单加载报错后，仍可编辑配置：

```bash
ebrc settings
ebrc modules
ebrc local
ebrc                 # 等同于 ebrc local
```

首次编辑时，`settings` 和 `local` 从注释模板创建；`modules` 复制完整默认清单，
保留当前默认功能。已有文件不会被模板覆盖。编辑器沿用 `EDITOR`，支持可执行文件路径
或简单空格分隔的参数，不解析 shell 表达式。保存后打开一个新 shell 生效。

`settings.bash` 中设置模块启动时需要的参数，例如：

```bash
BARC_HISTSIZE=20000
BARC_HISTFILESIZE=40000
```

`history` 模块在加载时读取这些值，因此应放在 `settings.bash`。
`local.bash` 适合少量个人定制，也可以显式 `source` 自己信任的片段。
无需改变当前 shell 状态的工具，优先做成 `~/.local/bin` 下的独立命令；
需要切换当前目录、设置环境变量、别名或 shell 选项的功能才放进 barc。

## 添加个人模块

用户模块与内置模块共用一份清单，严格按清单顺序加载，不自动扫描目录。
仅将文件放入 `modules/` 不会执行。名称可以包含小写字母、数字和连字符，
以字母或数字开头；清单中不写 `.bash` 后缀。

先建立清单，再从模板建立模块（路径通过当前 shell 的 barc 配置位置取得）：

```bash
ebrc modules
mkdir -p -- "$_BARC_CONFIG_DIR/modules"
cp -n -- "$_BARC_ROOT/examples/module.bash" "$_BARC_CONFIG_DIR/modules/dev-tools.bash"
```

编辑 `modules/dev-tools.bash`，例如加入常用开发目录入口：

```bash
cdev() { builtin cd -- "$HOME/projects"; }
return 0
```

再次运行 `ebrc modules`，保留需要的已有行，并在末尾添加一行 `dev-tools`。
打开新 shell 后运行 `barc_status`，检查加载结果和模块来源。

用户 `modules.conf` **整表替换**默认清单，不是对默认清单追加。空清单会禁用全部模块，
升级后默认清单新增的模块也不会自动加入用户清单。空行和 `#` 注释会被忽略，
重复名称只保留第一次出现的位置；非法条目会报错。

内置模块位于安装目录的 `modules/`，个人模块位于用户配置目录的 `modules/`。
同名模块若同时存在于两处，该清单项会报冲突，两个文件都不加载。
替换内置提示符时，把个人文件命名为 `my-prompt.bash`，从清单移除 `prompt`，
在相应位置加入 `my-prompt`。不需要改动系统文件或管理员权限。

## 模块编写约定

- 模块通过 `source` 在当前 shell 执行，共享变量、函数、别名和选项，无隔离。
  只加载自己信任的文件，不修改 `_BARC_`、`_barc_` 开头的内部名称。
- 模块在加载器函数内部执行，需要持久保留的变量声明使用 `declare -g`。
  `settings.bash` 和 `local.bash` 在顶层加载，普通 `declare` 不受此限制。
- 关键操作显式检查错误并返回非零，不依赖 `set -e`。成功时明确 `return 0`。
- 加载时只做本地 shell 初始化，不联网、不启动服务；需要这些动作时放进显式调用的函数。
- 不提供依赖解析，模块顺序由清单决定。有依赖时写明要求，并检查所需功能是否可用。

`examples/module.bash` 是注释模板，不在默认清单中。`barc_status` 显示本轮加载状态和
模块来源，并在存在加载错误时返回非零；它依据 `source` 返回值，不代表功能测试通过。
同一 shell 中重复加载会被忽略，编辑配置后应打开新 shell。

