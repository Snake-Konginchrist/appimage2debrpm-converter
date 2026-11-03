# 贡献指南

欢迎通过错误报告、功能建议、文档修正、测试和代码改进参与项目。交流时请围绕具体问题，尊重其他参与者。

## 报告问题

先搜索 [GitHub Issues](https://github.com/Snake-Konginchrist/appimage2debrpm-converter/issues)，确认是否已有相同报告。新问题请提供：

- 发行版及版本、CPU 架构、Python 和相关打包工具的版本。
- 项目提交编号：`git rev-parse --short HEAD`。
- 最小复现命令、输入 AppImage 的来源及版本、预期结果和实际结果。
- `--verbose` 输出中相关的错误信息，去除令牌、个人路径和其他敏感信息。

功能建议请说明使用场景、期望行为和现有方法的不足。漏洞报告请使用 [SECURITY.md](SECURITY.md) 中的私密联系方式。

## 开发环境

Fork 仓库并克隆自己的副本，在分支上开发：

```bash
git clone https://github.com/YOUR_USERNAME/appimage2debrpm-converter.git
cd appimage2debrpm-converter
git switch -c fix/describe-the-change
```

将 `YOUR_USERNAME` 替换为自己的 GitHub 用户名。Python 需要 3.9+，不依赖第三方 Python 包。系统打包工具按 [README](README.md#环境要求) 准备。

## 代码与文档约定

- 使用四空格缩进，遵循周边代码的命名、类型注解和异常处理风格。
- 共用逻辑放在 `core/` 或 `utils/`，格式相关逻辑放在 `local_deb/`、`local_rpm/`。
- 调用外部工具时使用参数列表；不要将文件路径或用户输入拼成 shell 命令。
- 保持已有参数与配置兼容；行为变化应解释原因和迁移方法。
- 功能、参数、安装依赖或限制变化时，同步修改 README、使用指南及配置示例中受影响的内容。
- README 用于项目介绍、快速开始和文档导航，变更细节写在提交信息与 Pull Request 中。
- 保留第三方代码与原应用的许可信息；项目代码贡献遵循现有 [MIT 许可证](LICENSE)。

## 验证改动

在项目根目录执行：

```bash
python3 main.py --help
python3 -m unittest discover -s tests -v
git diff --check
```

现有测试覆盖配置兼容、参数优先级、RPM 架构与 spec 内容，以及实际 DEB 归档结构。`ar` 不存在时归档测试会跳过；`dpkg-deb` 存在时还会检查 DEB 字段和文件列表。

修改打包逻辑时，应增加能复现问题的回归测试，并在相关 Linux 环境使用实际 AppImage 验证。PR 中应分别说明单元测试、实际转换、安装、启动和卸载中做过哪些验证，未执行的项目也请说明。

文档改动请检查相对链接、示例配置与 `python3 main.py --help` 是否一致。无需为纯文字修改新增代码测试。

## 提交 Pull Request

1. 尽量让一个 PR 解决一个明确的问题，避免混入无关格式化。
2. 使用说明改动目的的提交信息，保留相关贡献者署名。
3. 提交前检查差异，确认没有临时构建目录、应用安装包或私密配置。
4. 在 PR 中描述问题、最终行为、关联 Issue、验证结果及兼容性影响。

修改代码和合并 PR 不会自动创建 Release。版本发布由维护者单独决定。
