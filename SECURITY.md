# 安全说明

## 漏洞报告

请通过维护者 [Snake-Konginchrist 的公开联系邮箱](mailto:snakekongin@outlook.com) 私密报告安全问题。联系方式也可从其 [GitHub 主页](https://github.com/Snake-Konginchrist) 核实。

报告中请提供受影响的提交、运行环境、复现步骤和可能的影响；分享复现材料时去除凭据与个人信息。在维护者核实问题前，请避免在公开 Issue 中披露可直接利用的细节。

普通转换失败、安装错误和功能建议请提交 [GitHub Issue](https://github.com/Snake-Konginchrist/appimage2debrpm-converter/issues)。

## 使用边界

提取流程会尝试执行 AppImage 的 `--appimage-extract`。转换器不隔离输入程序的执行，也不校验输入应用的来源或可信性。请使用普通用户处理可信文件；检查生成包及其维护脚本后，再在目标系统安装。

漏洞修复以主分支为基础处理。目前没有承诺维护的历史版本分支或固定响应时限。
