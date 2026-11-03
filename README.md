# AppImage转DEB/RPM包转换器

这是一个用Python编写的工具，可以将AppImage应用程序转换为DEB或RPM包格式，方便在Linux系统上进行包管理和分发。

## 功能特性

- 🔄 支持将AppImage转换为DEB包
- 🔄 支持将AppImage转换为RPM包
- 📦 自动提取AppImage内容和元数据
- 🎯 生成符合标准的包结构
- ⚙️ 支持自定义包配置
- 📋 命令行界面，易于使用
- 🧹 自动清理临时文件

## 系统要求

### 基本要求
- Python 3.7+
- Linux操作系统

### 依赖工具

#### 对于DEB包构建
```bash
# Ubuntu/Debian
sudo apt-get install squashfs-tools dpkg-dev

# 或者最小安装
sudo apt-get install squashfs-tools dpkg-deb
```

#### 对于RPM包构建
```bash
# CentOS/RHEL/Fedora
sudo yum install squashfs-tools rpm-build
# 或
sudo dnf install squashfs-tools rpm-build
```

## 安装

1. 克隆或下载项目文件
2. 确保安装了必要的系统工具（见上方依赖工具）
3. 可选：安装Python依赖（目前主要使用标准库）

```bash
# 如果需要额外功能，可以安装可选依赖
pip install -r requirements.txt
```

## 使用方法

### 基本用法

```bash
# 转换为DEB包
python main.py app.AppImage

# 转换为RPM包
python main.py app.AppImage --format rpm

# 同时生成DEB和RPM包
python main.py app.AppImage --format both

# 指定输出目录
python main.py app.AppImage --output ./packages/
```

### 高级用法

```bash
# 自定义包信息
python main.py app.AppImage \
    --format deb \
    --maintainer "Your Name <email@example.com>" \
    --section "graphics" \
    --homepage "https://example.com" \
    --depends "libgtk-3-0" "libqt5core5a"

# 使用配置文件
python main.py app.AppImage --config config.json

# 详细输出和保留临时文件（调试用）
python main.py app.AppImage --verbose --keep-temp
```

### 配置文件示例

创建一个`config.json`文件：

```json
{
    "maintainer": "Your Name <email@example.com>",
    "license": "GPL-3.0",
    "homepage": "https://example.com",
    "deb": {
        "section": "graphics",
        "priority": "optional",
        "depends": ["libgtk-3-0", "libqt5core5a"],
        "requires": []
    },
    "rpm": {
        "section": "Applications/Graphics",
        "depends": [],
        "requires": ["glibc", "qt5-qtbase"]
    },
    "architecture": "amd64"
}
```

> 说明：`deb` 与 `rpm` 为两个独立的子配置对象，各自包含
> `section`（分类，DEB 的 Section 字段 / RPM 的 Group 字段）、
> `depends`（依赖）与 `requires`（需求）等字段，分别作用于
> DEB 包与 RPM 包的构建，可配置不同的值。
> 同时兼容旧的扁平配置和 `--section`、`--priority`、`--depends` 参数。
> 显式命令行参数优先于配置文件；`--depends` 同时覆盖 DEB 的 `depends`
> 和 RPM 的 `requires`，两种格式依赖不同时请使用各自的子配置。

## 命令行选项

```
位置参数:
  appimage              要转换的AppImage文件路径

可选参数:
  -h, --help            显示帮助信息
  --version             显示版本信息
  -f, --format {deb,rpm,both}
                        输出包格式 (默认: deb)
  -o, --output OUTPUT   输出目录路径 (默认: ./output)
  -c, --config CONFIG   配置文件路径 (JSON格式)
  -v, --verbose         显示详细输出
  --keep-temp           保留临时文件 (用于调试)

包配置选项:
  -m, --maintainer MAINTAINER
                        维护者信息 (格式: "姓名 <邮箱>")
  --section SECTION     DEB包分类 (未配置时为 misc)
  --priority PRIORITY   DEB包优先级 (未配置时为 optional)
  --license LICENSE     软件许可证
  --homepage HOMEPAGE   项目主页URL
  --depends [DEPENDS ...]
                        依赖包列表 (用空格分隔)
  --architecture ARCH   目标架构 (如: amd64, x86_64)
```

## 项目结构

```
appimage2deb-converter/
├── core/                   # 核心模块
│   ├── appimage.py        # AppImage处理
│   └── package_builder.py # 包构建器基类
├── local_deb/              # DEB包构建（本地实现，避免调用系统库）
│   └── deb_builder.py
├── local_rpm/              # RPM包构建（本地实现，避免调用系统库）
│   └── rpm_builder.py
├── utils/                 # 工具模块
│   ├── command_executor.py
│   └── file_operations.py
├── cli.py                 # 命令行界面
├── main.py               # 主程序入口
├── requirements.txt      # Python依赖
└── README.md            # 说明文档
```

## 工作原理

1. **提取AppImage**: 使用`unsquashfs`工具提取AppImage内容到临时目录
2. **解析元数据**: 从`.desktop`文件和其他源获取应用程序信息
3. **构建包结构**: 创建符合DEB/RPM标准的目录结构
4. **复制文件**: 将应用程序文件复制到适当位置
5. **生成元数据**: 创建`control`文件（DEB）或`.spec`文件（RPM）
6. **构建包**: 使用`dpkg-deb`或`rpmbuild`生成最终包文件
7. **清理**: 删除临时文件

## 注意事项

- 确保AppImage文件具有可执行权限
- 某些AppImage可能需要特定的运行时依赖
- 生成的包可能需要根据目标系统调整依赖关系
- 建议在目标系统上测试生成的包

## 故障排除

### 常见错误

1. **"缺少必要工具: unsquashfs"**
   ```bash
   sudo apt-get install squashfs-tools
   ```

2. **"需要dpkg-deb工具来构建DEB包"**
   ```bash
   sudo apt-get install dpkg-dev
   ```

3. **"需要rpmbuild工具来构建RPM包"**
   ```bash
   sudo yum install rpm-build
   ```

### 调试技巧

- 使用`--verbose`选项查看详细输出
- 使用`--keep-temp`选项保留临时文件进行检查
- 检查生成的包内容：
  ```bash
  # DEB包
  dpkg -c package.deb
  
  # RPM包
  rpm -qlp package.rpm
  ```

## 许可证

本项目采用MIT许可证。详见LICENSE文件。

## 贡献

欢迎提交问题报告和功能请求！如果您想贡献代码，请：

1. Fork本项目
2. 创建功能分支
3. 提交更改
4. 发起Pull Request

## 更新日志

### v1.0.0
- 初始版本
- 支持AppImage转DEB包
- 支持AppImage转RPM包
- 命令行界面
- 配置文件支持 
