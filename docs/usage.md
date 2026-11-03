# 使用指南

[返回项目首页](../README.md)

## 命令格式

```text
python3 main.py APPIMAGE [选项]
```

`APPIMAGE` 是输入文件路径。包含空格的路径请使用引号。转换前准备 Python 3.9+、`unsquashfs` 和相应打包工具，安装命令见 [README](../README.md#环境要求)。

## 命令行选项

| 选项 | 作用 | 默认行为 |
| --- | --- | --- |
| `-h`, `--help` | 显示帮助并退出 | — |
| `--version` | 显示转换器版本并退出 | — |
| `-f`, `--format {deb,rpm,both}` | 选择输出格式 | `deb` |
| `-o`, `--output PATH` | 设置输出目录 | `./output` |
| `-c`, `--config PATH` | 读取 JSON 配置 | 不读取配置文件 |
| `-m`, `--maintainer TEXT` | 设置包维护者 | `AppImage Converter <converter@example.com>` |
| `--section TEXT` | 设置 DEB 分类 | 未配置时为 `misc` |
| `--priority TEXT` | 设置 DEB 优先级 | 未配置时为 `optional` |
| `--depends [PACKAGE ...]` | 同时设置 DEB 的依赖与 RPM 的需求 | 使用配置或内置默认值 |
| `--license TEXT` | 设置原应用的许可证标识，用于 RPM 元数据 | `Unknown` |
| `--homepage URL` | 设置包主页 | 未配置时为空 |
| `--architecture ARCH`, `--arch ARCH` | 设置目标包的架构标识 | 检测构建机器架构 |
| `-v`, `--verbose` | 显示配置摘要及错误堆栈 | 关闭 |
| `--keep-temp` | 保留 AppImage 提取目录 | 提取目录在结束时清理 |

`--keep-temp` 只保留提取目录，DEB/RPM 的构建目录仍会清理。`--depends` 可接收多个值，建议放在命令末尾。

## 常用示例

### 设置 DEB 元数据

```bash
python3 main.py ./application.AppImage \
  --format deb \
  --maintainer "Package Maintainer <maintainer@example.com>" \
  --section graphics \
  --priority optional \
  --homepage https://example.com \
  --depends libc6 libgcc-s1
```

上述维护者、主页和依赖是示例，使用时请替换为原应用与目标系统对应的信息。

### 为两种格式分别配置依赖

```bash
cp config.example.json config.json
# 编辑 config.json 后执行
python3 main.py ./application.AppImage --format both --config config.json
```

示例文件内容：

```json
{
    "maintainer": "Package Maintainer <maintainer@example.com>",
    "license": "Unknown",
    "homepage": "https://example.com",
    "deb": {
        "section": "graphics",
        "priority": "optional",
        "depends": ["libc6", "libgcc-s1"]
    },
    "rpm": {
        "section": "Applications/Graphics",
        "requires": ["glibc", "libgcc"]
    }
}
```

维护者与主页需要替换；`license` 应按原应用的声明填写。示例依赖只用于展示字段结构，不是完整的应用依赖清单。

### 配置字段与优先级

| 配置字段 | 作用 |
| --- | --- |
| `maintainer` | DEB 的维护者字段 |
| `license` | RPM 的许可证字段 |
| `homepage` | DEB/RPM 的主页字段 |
| `architecture` | 包架构标识，不改变应用二进制 |
| `deb.section` | DEB 的 `Section` |
| `deb.priority` | DEB 的 `Priority` |
| `deb.depends` | DEB 的 `Depends`，使用字符串数组 |
| `rpm.section` | RPM 的 `Group` |
| `rpm.requires` | RPM 的 `Requires`，使用字符串数组 |

旧的顶层 `section`、`priority`、`depends`、`requires` 仍受支持。依赖和分类字段优先读取对应的子配置，没有对应字段时再读取顶层配置。

显式命令行参数覆盖配置文件：`--section`、`--priority` 覆盖 DEB 对应字段，`--depends` 同时覆盖 `deb.depends` 和 `rpm.requires`。两种格式的依赖名称不同时，请使用各自的子配置。

`deb.requires` 与 `rpm.depends` 不参与相应包的依赖生成。依赖未配置或列表为空时，DEB 回退为 `libc6`、`libgcc-s1`，RPM 回退为 `glibc`、`libgcc`；空数组不能用来清除默认依赖。

### 架构

配置中的 `architecture` 与命令行 `--architecture` 使用同一规则：

| 输入标识 | DEB 标识 | RPM 标识 |
| --- | --- | --- |
| `amd64` | `amd64` | `x86_64` |
| `arm64` | `arm64` | `aarch64` |
| `armhf` | `armhf` | `armv7hl` |
| `i386` | `i386` | `i686` |

未指定时检测构建机器，不能据此判断输入文件的架构。请确保架构标识与原 AppImage 一致；修改标识不会将 x86 程序转换为 ARM 程序。

## 检查输出

输出目录由 `--output` 指定，文件路径会在结束时打印。DEB 文件名为 `<应用名>_<版本>_<架构>.deb`；RPM 使用 `rpmbuild` 生成的文件名。

在具备相应工具的系统上检查生成包：

```bash
# DEB：元数据和文件列表
dpkg-deb --info ./output/application.deb
dpkg-deb --contents ./output/application.deb

# RPM：元数据和文件列表
rpm -qip ./output/application.rpm
rpm -qlp ./output/application.rpm
```

请将示例文件名替换为实际输出。元数据与归档检查通过后，还需要在目标发行版测试安装、启动和卸载。

## 错误排查

| 现象 | 检查方法 |
| --- | --- |
| 提示缺少 `unsquashfs` | 安装 `squashfs-tools`；当前入口会先检查该命令 |
| 提示缺少 `ar` | 安装 `binutils`，或安装 `dpkg` 以使用 `dpkg-deb` |
| 提示缺少 `rpmbuild` | 安装目标发行版的 `rpm-build` 包 |
| 配置读取失败 | 检查 JSON 语法；配置根节点与 `deb`、`rpm` 必须是对象 |
| 提取失败 | 用 `--verbose` 查看错误，确认文件来源、完整性及输入程序架构 |
| 安装后无法启动 | 检查目标系统依赖、CPU 架构、启动脚本和桌面入口 |
| 菜单中没有图标 | 检查包内桌面文件与图标路径，以及安装时桌面缓存更新输出 |

调试命令：

```bash
python3 main.py ./application.AppImage --verbose --keep-temp
```

提交问题时附上可复现命令、系统/Python 版本、提交编号及去除敏感信息后的日志，参见[贡献指南](../CONTRIBUTING.md)。

## 当前行为与限制

- 当前元数据解析未设置应用版本，包版本使用默认值 `1.0.0`，没有命令行版本覆盖选项。
- `--format both` 分别尝试两种格式；其中一种成功即可返回成功退出码。自动化脚本应同时检查两种输出文件。
- `--keep-temp` 不保留打包器构建目录，也不关闭其清理逻辑。
- 转换过程会尝试执行输入 AppImage；本工具不是用于隔离不可信程序的沙箱。
