# AppImage 转 DEB/RPM 转换器

使用 Python 将 Linux AppImage 重新打包为 DEB 或 RPM 安装包，便于通过系统包管理器安装和卸载应用。

[使用指南](docs/usage.md) | [参与贡献](CONTRIBUTING.md) | [报告问题](https://github.com/Snake-Konginchrist/appimage2debrpm-converter/issues) | [安全说明](SECURITY.md) | [MIT 许可证](LICENSE)

## 功能

- 从 AppImage 提取应用文件，读取 `.desktop` 中的名称、描述、启动入口和图标。
- 生成 DEB、RPM，或一次生成两种格式。
- 为 DEB 与 RPM 分别配置分类和运行依赖，并兼容原有扁平配置与命令行参数。
- 创建启动脚本、桌面入口和应用图标，提供桌面数据库及图标缓存更新脚本。
- 使用 `dpkg-deb` 构建 DEB；缺少该工具时，使用 Python 标准库和 `ar` 打包。
- 使用 `rpmbuild` 构建 RPM，提供分步进度和详细错误输出。

## 环境要求

- Linux；生成的安装包需要在目标发行版上验证。
- Python 3.9 或更高版本。当前代码使用 Python 3.9 引入的类型注解写法。
- Git，用于获取源码；`unsquashfs`，用于 AppImage 提取流程。
- DEB：`dpkg-deb`，或用于替代打包路径的 `ar`。
- RPM：`rpmbuild`。

Python 部分仅使用标准库，无须安装第三方 Python 包。

## 快速开始

### 1. 安装系统依赖

Debian / Ubuntu，构建 DEB：

```bash
sudo apt-get update
sudo apt-get install git python3 squashfs-tools dpkg binutils
```

Fedora，构建 RPM：

```bash
sudo dnf install git python3 squashfs-tools rpm-build
```

构建两种格式时，需要同时准备相应工具。其他发行版请使用其包管理器安装上述命令。

### 2. 获取源码

```bash
git clone https://github.com/Snake-Konginchrist/appimage2debrpm-converter.git
cd appimage2debrpm-converter
python3 main.py --help
```

### 3. 转换应用

将 `./application.AppImage` 替换为实际文件路径：

```bash
# 生成 DEB，输出到 ./output/
python3 main.py ./application.AppImage

# 生成 RPM
python3 main.py ./application.AppImage --format rpm

# 同时生成 DEB 和 RPM，并指定输出目录
python3 main.py ./application.AppImage --format both --output ./packages/
```

使用普通用户执行转换。提取流程会尝试运行输入 AppImage 的 `--appimage-extract`，因此应仅处理可信来源的文件。

## 配置

复制示例文件，按原应用及目标发行版调整维护者、许可证、依赖和架构：

```bash
cp config.example.json config.json
python3 main.py ./application.AppImage --format both --config config.json
```

`deb` 与 `rpm` 使用各自的配置对象。`--section`、`--priority`、`--depends` 等旧参数仍可使用；显式命令行参数优先于配置文件。配置字段、默认行为与完整选项见[使用指南](docs/usage.md)。

## 使用范围

- 本工具重新打包现有程序，不执行交叉编译，也不转换程序的 CPU 架构。未指定架构时，使用构建机器的架构。
- 运行依赖需要按目标发行版填写；默认依赖不能替代完整的依赖检查。
- 当前未从 AppImage 中识别应用版本，生成包的版本默认使用 `1.0.0`。
- 生成安装包后，应在目标系统验证安装、启动和卸载。现有回归测试不等同于所有 AppImage 或发行版的兼容性认证。

## 开发与贡献

运行现有回归测试：

```bash
python3 -m unittest discover -s tests -v
```

测试使用 Python 标准库；实际 DEB 归档检查需要 `ar`，环境中存在 `dpkg-deb` 时还会检查包字段和文件列表。

欢迎提交错误报告、功能建议、文档改进和代码贡献。提交方式、代码约定及验证要求见 [CONTRIBUTING.md](CONTRIBUTING.md)；普通使用问题请通过 [GitHub Issues](https://github.com/Snake-Konginchrist/appimage2debrpm-converter/issues) 提出。

## 维护与许可证

由 [Snake-Konginchrist](https://github.com/Snake-Konginchrist) 维护，贡献者记录见 [Git 提交历史](https://github.com/Snake-Konginchrist/appimage2debrpm-converter/commits/main/)。

转换器源代码采用 [MIT 许可证](LICENSE)。被转换应用及其依赖仍遵循各自的许可证；配置中的 `license` 字段用于描述原应用，不会改变原应用的许可条件。
