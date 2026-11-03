"""
RPM包构建器
负责将AppImage转换为RPM包
"""

import os
import stat
from typing import Dict, Any
from core.package_builder import PackageBuilder
from utils.file_operations import create_temp_dir, make_dirs, copy_tree, copy_file, remove_dir
from utils.command_executor import execute_command, check_command_exists


class RpmBuilder(PackageBuilder):
    """RPM包构建器"""
    
    def __init__(self, app_info, extracted_dir: str):
        """
        初始化RPM包构建器
        
        Args:
            app_info: AppImage信息对象
            extracted_dir: AppImage提取后的目录路径
        """
        super().__init__(app_info, extracted_dir)
        self.rpm_build_dir = ""
        self.spec_file = ""
        self._check_dependencies()
    
    def _check_dependencies(self) -> None:
        """检查构建RPM包所需的工具"""
        required_tools = ['rpmbuild']
        missing_tools = []
        
        for tool in required_tools:
            if not check_command_exists(tool):
                missing_tools.append(tool)
        
        if missing_tools:
            print(f"警告：缺少工具 {', '.join(missing_tools)}，将尝试使用替代方法构建RPM包")
    
    def prepare_build_directory(self) -> str:
        """
        准备RPM包构建目录
        
        Returns:
            构建目录路径
        """
        self.build_dir = create_temp_dir("rpm_build_")
        
        # 创建RPM构建目录结构
        rpm_dirs = ['BUILD', 'RPMS', 'SOURCES', 'SPECS', 'SRPMS']
        for rpm_dir in rpm_dirs:
            make_dirs(os.path.join(self.build_dir, rpm_dir))
        
        self.rpm_build_dir = os.path.join(self.build_dir, 'BUILD')
        self.spec_file = os.path.join(self.build_dir, 'SPECS', f"{self.get_package_name()}.spec")
        
        print(f"RPM构建目录已创建: {self.build_dir}")
        return self.build_dir
    
    def create_package_structure(self) -> None:
        """创建RPM包的目录结构"""
        package_name = self.get_package_name(preserve_case=True)
        
        # 在BUILD目录下创建包结构
        build_root = os.path.join(self.rpm_build_dir, f"{package_name}-{self.get_package_version('rpm')}")
        make_dirs(build_root)
        
        # 创建标准的Linux目录结构
        directories = [
            f"usr/bin",
            f"usr/share/applications", 
            f"usr/share/pixmaps",
            f"usr/share/{package_name}",
            f"usr/share/doc/{package_name}"
        ]
        
        for directory in directories:
            make_dirs(os.path.join(build_root, directory))
    
    def copy_application_files(self) -> None:
        """复制应用程序文件到RPM包目录"""
        package_name = self.get_package_name(preserve_case=True)
        version = self.get_package_version('rpm')
        build_root = os.path.join(self.rpm_build_dir, f"{package_name}-{version}")
        app_install_dir = os.path.join(build_root, f"usr/share/{package_name}")
        
        # 复制整个应用程序目录
        copy_tree(self.extracted_dir, app_install_dir)
        
        # 创建启动脚本
        self._create_launcher_script(build_root)
        
        # 复制.desktop文件
        self._copy_desktop_file(build_root)
        
        # 复制图标文件
        self._copy_icon_file(build_root)
    
    def _create_launcher_script(self, build_root: str) -> None:
        """创建应用程序启动脚本"""
        package_name = self.get_package_name(preserve_case=True)
        script_path = os.path.join(build_root, f"usr/bin/{package_name}")
        app_dir = f"/usr/share/{package_name}"
        
        # 查找主可执行文件的相对路径
        if self.app_info.executable:
            rel_exec_path = os.path.relpath(self.app_info.executable, self.extracted_dir)
        else:
            rel_exec_path = "AppRun"
        
        script_content = f"""#!/bin/bash
# {self.app_info.name} 启动脚本
# 由AppImage转换器自动生成

APP_DIR="{app_dir}"
EXEC_PATH="$APP_DIR/{rel_exec_path}"

# 切换到应用程序目录
cd "$APP_DIR"

# 确保可执行文件有执行权限
chmod +x "$EXEC_PATH"

# 启动应用程序
exec "$EXEC_PATH" "$@"
"""
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # 设置执行权限
        os.chmod(script_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    
    def _copy_desktop_file(self, build_root: str) -> None:
        """复制并修改.desktop文件"""
        if not self.app_info.desktop_file:
            return
        
        package_name = self.get_package_name(preserve_case=True)
        desktop_dest = os.path.join(build_root, f"usr/share/applications/{package_name}.desktop")
        
        # 读取原始.desktop文件
        with open(self.app_info.desktop_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修改Exec和Icon路径
        lines = content.split('\n')
        modified_lines = []
        
        for line in lines:
            if line.startswith('Exec='):
                modified_lines.append(f'Exec={package_name}')
            elif line.startswith('Icon='):
                modified_lines.append(f'Icon={package_name}')
            else:
                modified_lines.append(line)
        
        # 写入修改后的.desktop文件
        with open(desktop_dest, 'w', encoding='utf-8') as f:
            f.write('\n'.join(modified_lines))
    
    def _copy_icon_file(self, build_root: str) -> None:
        """复制图标文件到hicolor图标主题目录"""
        if not self.app_info.icon or not os.path.isfile(self.app_info.icon):
            return
        
        package_name = self.get_package_name(preserve_case=True)
        icon_ext = os.path.splitext(self.app_info.icon)[1]
        if not icon_ext:
            icon_ext = '.png'
        
        # 探测图标尺寸，用于决定hicolor主题目录的尺寸子目录
        icon_size = self._detect_icon_size(self.app_info.icon)
        
        if icon_size:
            # 复制到标准hicolor图标主题目录：usr/share/icons/hicolor/<size>/apps/
            icon_dest = os.path.join(
                build_root,
                f"usr/share/icons/hicolor/{icon_size}/apps/{package_name}{icon_ext}"
            )
            make_dirs(os.path.dirname(icon_dest))
        else:
            # 无法探测尺寸时，回退到pixmaps目录（旧式图标位置）
            icon_dest = os.path.join(build_root, f"usr/share/pixmaps/{package_name}{icon_ext}")
        
        copy_file(self.app_info.icon, icon_dest)
    
    def _detect_icon_size(self, icon_path: str) -> str:
        """
        探测图标尺寸，返回hicolor目录尺寸字符串（如 '512x512'）
        
        Args:
            icon_path: 图标文件路径
        
        Returns:
            尺寸字符串，无法探测时返回空字符串
        """
        ext = os.path.splitext(icon_path)[1].lower()
        
        # PNG/JPEG/GIF等光栅图像：读取头部尺寸
        if ext in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
            try:
                import struct
                with open(icon_path, 'rb') as f:
                    header = f.read(32)
                
                if ext == '.png' and header[:8] == b'\x89PNG\r\n\x1a\n':
                    width, height = struct.unpack('>II', header[16:24])
                    return f"{width}x{height}"
                elif ext == '.gif' and header[:6] in (b'GIF87a', b'GIF89a'):
                    width, height = struct.unpack('<HH', header[6:10])
                    return f"{width}x{height}"
            except Exception:
                return ""
        
        # SVG矢量图：解析width/height/viewBox属性
        if ext == '.svg':
            try:
                with open(icon_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(2048)
                import re
                w = re.search(r'width=["\']?(\d+)', content)
                h = re.search(r'height=["\']?(\d+)', content)
                if w and h:
                    return f"{w.group(1)}x{h.group(1)}"
                vb = re.search(r'viewBox=["\']\s*0\s+0\s+(\d+)\s+(\d+)', content)
                if vb:
                    return f"{vb.group(1)}x{vb.group(2)}"
                return "scalable"
            except Exception:
                return "scalable"
        
        return ""
    
    def generate_metadata_files(self) -> None:
        """生成RPM包的元数据文件"""
        self._generate_spec_file()
    
    def _generate_spec_file(self) -> None:
        """生成RPM spec文件"""
        package_name = self.get_package_name()  # spec文件中的Name字段保持小写（RPM规范）
        package_name_preserve_case = self.get_package_name(preserve_case=True)  # 用于目录名
        version = self.get_package_version('rpm')
        
        # 生成依赖列表（从嵌套的rpm子配置读取，兼容旧的扁平requires字段）
        requires = self._get_requires('rpm')
        if not requires:
            # 添加一些常见的依赖
            requires = ['glibc', 'libgcc']
        
        # 获取架构
        architecture = self.get_architecture('rpm')
        
        # 生成文件列表
        files_list = self._generate_files_list()
        
        # 主页URL可能为空，为空时省略该标签，避免空的spec标签导致rpmbuild报错
        homepage = self.app_info.homepage or self.package_config.get('homepage', '')
        url_line = f"URL:            {homepage}" if homepage else ""
        
        # RPM的Group字段对应DEB的Section概念，从rpm子配置读取，为空则省略
        group = self._get_section('rpm')
        group_line = f"Group:          {group}" if group else ""
        
        spec_content = f"""Name:           {package_name}
Version:        {version}
Release:        1%{{?dist}}
Summary:        {self.app_info.description or self.app_info.name}

License:        {self.package_config.get('license', 'Unknown')}
{group_line}
{url_line}
BuildArch:      {architecture}
Requires:       {', '.join(requires)}

%description
{self.app_info.description or f'AppImage应用程序 {self.app_info.name} 转换为RPM包'}

原始AppImage文件大小: {self.app_info.size // 1024}KB

%prep
# 准备阶段 - 文件已预先放置，无需解压源码

%build
# 构建阶段 - 文件已准备好，跳过

%install
# 安装阶段 - 复制文件到构建根目录
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT

# 复制所有文件（使用绝对路径，避免rpmbuild宏解析差异）
cp -r {self.rpm_build_dir}/{package_name_preserve_case}-{version}/* $RPM_BUILD_ROOT/

%clean
rm -rf $RPM_BUILD_ROOT

%post
# 安装后脚本
# 更新桌面数据库
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications
fi

# 更新hicolor图标主题缓存
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi

# 更新KDE桌面缓存（Plasma 6用kbuildsycoca6，Plasma 5用kbuildsycoca5）
if command -v kbuildsycoca6 >/dev/null 2>&1; then
    kbuildsycoca6 --noincremental 2>/dev/null || true
elif command -v kbuildsycoca5 >/dev/null 2>&1; then
    kbuildsycoca5 --noincremental 2>/dev/null || true
fi

%preun
# 卸载前脚本

%files
{files_list}

%changelog
* {self._get_current_date()} AppImage Converter <converter@example.com> - {version}-1
- 从AppImage自动转换生成的RPM包
"""
        
        with open(self.spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
    
    def _generate_files_list(self) -> str:
        """生成RPM包的文件列表"""
        package_name = self.get_package_name(preserve_case=True)
        version = self.get_package_version('rpm')
        build_root = os.path.join(self.rpm_build_dir, f"{package_name}-{version}")
        
        files = []
        for root, dirs, filenames in os.walk(build_root):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, build_root)
                
                # 为可执行文件添加属性
                if rel_path.startswith('usr/bin/'):
                    files.append(f'%attr(755,root,root) /{rel_path}')
                else:
                    files.append(f'/{rel_path}')
        
        return '\n'.join(files)
    
    def _get_current_date(self) -> str:
        """获取当前日期，格式为RPM changelog格式"""
        import datetime
        import locale
        
        try:
            # 设置英文locale以获得英文日期格式
            locale.setlocale(locale.LC_TIME, 'C')
        except:
            pass
        
        now = datetime.datetime.now()
        return now.strftime("%a %b %d %Y")
    
    def build_package(self, output_path: str) -> str:
        """
        构建RPM包
        
        Args:
            output_path: 输出目录路径
        
        Returns:
            生成的RPM包文件路径
        """
        if not check_command_exists('rpmbuild'):
            raise RuntimeError("需要rpmbuild工具来构建RPM包。请安装: sudo yum install rpm-build 或 sudo dnf install rpm-build")
        
        package_name = self.get_package_name()
        version = self.get_package_version('rpm')
        architecture = self.get_architecture('rpm')
        
        # 使用rpmbuild构建包
        # _tmppath 显式指向 /tmp，避免在只读的 /var/tmp 上创建临时文件失败
        # _buildroot 指向构建根目录下的临时安装目录，保证 %install 可写
        tmp_dir = os.path.join(self.build_dir, 'tmp')
        make_dirs(tmp_dir)
        buildroot = os.path.join(self.build_dir, 'buildroot')
        make_dirs(buildroot)
        
        return_code, stdout, stderr = execute_command([
            'rpmbuild', '--define', f'_topdir {self.build_dir}',
            '--define', f'_builddir {self.rpm_build_dir}',
            '--define', f'_tmppath {tmp_dir}',
            '--define', f'_buildroot {buildroot}',
            '-bb', self.spec_file
        ])
        
        if return_code != 0:
            raise RuntimeError(f"构建RPM包失败: {stderr}")
        
        # 查找生成的RPM文件
        rpms_dir = os.path.join(self.build_dir, 'RPMS', architecture)
        rpm_files = [f for f in os.listdir(rpms_dir) if f.endswith('.rpm')]
        
        if not rpm_files:
            raise RuntimeError("未找到生成的RPM文件")
        
        rpm_file = rpm_files[0]
        rpm_path = os.path.join(rpms_dir, rpm_file)
        
        # 复制到输出目录
        output_rpm_path = os.path.join(output_path, rpm_file)
        copy_file(rpm_path, output_rpm_path)
        
        print(f"RPM包已生成: {output_rpm_path}")
        return output_rpm_path
    
    def cleanup(self) -> None:
        """清理临时文件"""
        if self.build_dir:
            remove_dir(self.build_dir)
            self.build_dir = "" 
