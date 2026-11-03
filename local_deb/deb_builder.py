"""
DEB包构建器
负责将AppImage转换为DEB包
"""

import os
import stat
import tarfile
from typing import Dict, Any
from core.package_builder import PackageBuilder
from utils.file_operations import create_temp_dir, make_dirs, copy_tree, copy_file, remove_dir
from utils.command_executor import execute_command, check_command_exists


class DebBuilder(PackageBuilder):
    """DEB包构建器"""
    
    def __init__(self, app_info, extracted_dir: str):
        """
        初始化DEB包构建器
        
        Args:
            app_info: AppImage信息对象
            extracted_dir: AppImage提取后的目录路径
        """
        super().__init__(app_info, extracted_dir)
        self.debian_dir = ""
        self._check_dependencies()
    
    def _check_dependencies(self) -> None:
        """检查构建DEB包所需的工具"""
        required_tools = ['dpkg-deb', 'fakeroot']
        missing_tools = []
        
        for tool in required_tools:
            if not check_command_exists(tool):
                missing_tools.append(tool)
        
        if missing_tools:
            print(f"警告：缺少工具 {', '.join(missing_tools)}，将尝试使用替代方法构建DEB包")
    
    def prepare_build_directory(self) -> str:
        """
        准备DEB包构建目录
        
        Returns:
            构建目录路径
        """
        self.build_dir = create_temp_dir("deb_build_")
        self.debian_dir = os.path.join(self.build_dir, "DEBIAN")
        make_dirs(self.debian_dir)
        
        print(f"DEB构建目录已创建: {self.build_dir}")
        return self.build_dir
    
    def create_package_structure(self) -> None:
        """创建DEB包的目录结构"""
        package_name = self.get_package_name(preserve_case=True)
        
        # 创建标准的Linux目录结构
        directories = [
            f"usr/bin",
            f"usr/share/applications",
            f"usr/share/pixmaps",
            f"usr/share/{package_name}",
            f"usr/share/doc/{package_name}"
        ]
        
        for directory in directories:
            make_dirs(os.path.join(self.build_dir, directory))
    
    def copy_application_files(self) -> None:
        """复制应用程序文件到DEB包目录"""
        package_name = self.get_package_name(preserve_case=True)
        app_install_dir = os.path.join(self.build_dir, f"usr/share/{package_name}")
        
        # 复制整个应用程序目录
        copy_tree(self.extracted_dir, app_install_dir)
        
        # 创建启动脚本
        self._create_launcher_script()
        
        # 复制.desktop文件
        self._copy_desktop_file()
        
        # 复制图标文件
        self._copy_icon_file()
    
    def _create_launcher_script(self) -> None:
        """创建应用程序启动脚本"""
        package_name = self.get_package_name(preserve_case=True)
        script_path = os.path.join(self.build_dir, f"usr/bin/{package_name}")
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
    
    def _copy_desktop_file(self) -> None:
        """复制并修改.desktop文件"""
        if not self.app_info.desktop_file:
            return
        
        package_name = self.get_package_name(preserve_case=True)
        desktop_dest = os.path.join(self.build_dir, f"usr/share/applications/{package_name}.desktop")
        
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
    
    def _copy_icon_file(self) -> None:
        """复制图标文件到hicolor图标主题目录"""
        if not self.app_info.icon or not os.path.isfile(self.app_info.icon):
            return
        
        package_name = self.get_package_name(preserve_case=True)
        icon_ext = os.path.splitext(self.app_info.icon)[1]
        if not icon_ext:
            icon_ext = '.png'
        
        # 探测图标尺寸（PNG/SVG等），用于决定hicolor主题目录的尺寸子目录
        icon_size = self._detect_icon_size(self.app_info.icon)
        
        if icon_size:
            # 复制到标准hicolor图标主题目录：usr/share/icons/hicolor/<size>/apps/
            icon_dest = os.path.join(
                self.build_dir,
                f"usr/share/icons/hicolor/{icon_size}/apps/{package_name}{icon_ext}"
            )
            make_dirs(os.path.dirname(icon_dest))
        else:
            # 无法探测尺寸时，回退到pixmaps目录（旧式图标位置）
            icon_dest = os.path.join(self.build_dir, f"usr/share/pixmaps/{package_name}{icon_ext}")
        
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
                    # PNG IHDR：宽度在字节16-19，高度在字节20-23（大端）
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
                # 优先取width/height，其次取viewBox
                w = re.search(r'width=["\']?(\d+)', content)
                h = re.search(r'height=["\']?(\d+)', content)
                if w and h:
                    return f"{w.group(1)}x{h.group(1)}"
                vb = re.search(r'viewBox=["\']\s*0\s+0\s+(\d+)\s+(\d+)', content)
                if vb:
                    return f"{vb.group(1)}x{vb.group(2)}"
                # SVG默认
                return "scalable"
            except Exception:
                return "scalable"
        
        return ""
    
    def generate_metadata_files(self) -> None:
        """生成DEB包的元数据文件"""
        self._generate_control_file()
        self._generate_postinst_script()
        self._generate_prerm_script()
    
    def _generate_control_file(self) -> None:
        """生成control文件"""
        package_name = self.get_package_name()
        version = self.get_package_version()
        
        # 计算安装后的大小（KB）
        installed_size = self._calculate_installed_size()
        
        # 确定架构
        architecture = self.get_architecture('deb')
        
        # 生成依赖列表（从嵌套的deb子配置读取，兼容旧的扁平depends字段）
        depends = self._get_dependencies('deb')
        if not depends:
            # 添加一些常见的依赖
            depends = ['libc6', 'libgcc-s1']
        
        control_content = f"""Package: {package_name}
Version: {version}
Section: {self._get_section('deb', 'misc')}
Priority: {self._get_priority('deb', 'optional')}
Architecture: {architecture}
Depends: {', '.join(depends)}
Maintainer: {self.package_config.get('maintainer', 'AppImage Converter <converter@example.com>')}
Description: {self.app_info.description or self.app_info.name}
 {self.app_info.description or f'AppImage应用程序 {self.app_info.name} 转换为DEB包'}
 .
 原始AppImage文件大小: {self.app_info.size // 1024}KB
Homepage: {self.app_info.homepage or self.package_config.get('homepage', '')}
Installed-Size: {installed_size}
"""
        
        control_path = os.path.join(self.debian_dir, "control")
        with open(control_path, 'w', encoding='utf-8') as f:
            f.write(control_content)
    
    def _calculate_installed_size(self) -> int:
        """计算安装后的大小（KB）"""
        total_size = 0
        for root, _, files in os.walk(self.build_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
        return total_size // 1024  # 转换为KB
    
    def _generate_postinst_script(self) -> None:
        """生成安装后脚本"""
        postinst_content = """#!/bin/bash
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

exit 0
"""
        
        postinst_path = os.path.join(self.debian_dir, "postinst")
        with open(postinst_path, 'w', encoding='utf-8') as f:
            f.write(postinst_content)
        
        # 设置执行权限
        os.chmod(postinst_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    
    def _generate_prerm_script(self) -> None:
        """生成卸载前脚本"""
        prerm_content = """#!/bin/bash
# 卸载前脚本

exit 0
"""
        
        prerm_path = os.path.join(self.debian_dir, "prerm")
        with open(prerm_path, 'w', encoding='utf-8') as f:
            f.write(prerm_content)
        
        # 设置执行权限
        os.chmod(prerm_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    
    def build_package(self, output_path: str) -> str:
        """
        构建DEB包
        
        Args:
            output_path: 输出目录路径
        
        Returns:
            生成的DEB包文件路径
        """
        package_name = self.get_package_name(preserve_case=True)
        version = self.get_package_version()
        architecture = self.get_architecture('deb')
        
        deb_filename = f"{package_name}_{version}_{architecture}.deb"
        deb_path = os.path.join(output_path, deb_filename)
        
        # 使用dpkg-deb构建包
        if check_command_exists('dpkg-deb'):
            return_code, stdout, stderr = execute_command([
                'dpkg-deb', '--build', self.build_dir, deb_path
            ])
            
            if return_code != 0:
                raise RuntimeError(f"构建DEB包失败: {stderr}")
        else:
            # 如果没有dpkg-deb，使用ar命令手动构建
            self._build_deb_manually(deb_path)
        
        print(f"DEB包已生成: {deb_path}")
        return deb_path
    
    def _build_deb_manually(self, deb_path: str) -> None:
        """
        手动构建DEB包（当dpkg-deb不可用时）
        
        使用Python标准库生成tar/gzip，再用ar构建.deb文件。
        .deb文件本质是一个ar归档，包含：
            1. debian-binary  (内容为 "2.0\n")
            2. control.tar.gz (DEBIAN目录下的控制文件)
            3. data.tar.gz    (实际安装的文件)
        """
        import shutil

        if not check_command_exists('ar'):
            raise RuntimeError("缺少构建DEB包所需的工具: ar。请安装: sudo apt-get install binutils")
        
        # 临时目录用于存放中间产物
        staging_dir = create_temp_dir("deb_manual_")
        
        try:
            debian_binary_path = os.path.join(staging_dir, "debian-binary")
            control_tar_path = os.path.join(staging_dir, "control.tar.gz")
            data_tar_path = os.path.join(staging_dir, "data.tar.gz")
            
            # 1. 生成 debian-binary 文件
            with open(debian_binary_path, 'w', encoding='utf-8') as f:
                f.write("2.0\n")
            
            def root_owner(member):
                member.uid = member.gid = 0
                member.uname = member.gname = 'root'
                return member

            # 控制文件必须位于归档根目录，而不是DEBIAN/control。
            # GNU格式支持长路径，并避免生成dpkg不支持的PAX扩展头。
            with tarfile.open(control_tar_path, 'w:gz', format=tarfile.GNU_FORMAT) as archive:
                archive.add(self.debian_dir, arcname='.', filter=root_owner)
            
            # 3. 生成 data.tar.gz（排除DEBIAN目录的其他所有文件）
            # 先列出顶层条目，排除DEBIAN
            entries = []
            for entry in sorted(os.listdir(self.build_dir)):
                if entry != 'DEBIAN':
                    entries.append(entry)
            
            if not entries:
                raise RuntimeError("DEB包没有可打包的数据文件")
            
            with tarfile.open(data_tar_path, 'w:gz', format=tarfile.GNU_FORMAT) as archive:
                for entry in entries:
                    archive.add(os.path.join(self.build_dir, entry), arcname=entry, filter=root_owner)
            
            # 4. 使用ar归档生成.deb文件
            # ar要求以指定顺序归档：debian-binary 在最前
            # 确保输出目录存在，并使用绝对路径（ar在cwd下执行）
            make_dirs(os.path.dirname(os.path.abspath(deb_path)))
            abs_deb_path = os.path.abspath(deb_path)

            # 每次创建新归档，避免覆盖旧包时残留成员或符号表。
            staged_deb_path = os.path.join(staging_dir, 'package.deb')
            return_code, _, stderr = execute_command(
                ['ar', 'rcS', staged_deb_path, 'debian-binary', 'control.tar.gz', 'data.tar.gz'],
                cwd=staging_dir
            )
            if return_code != 0:
                raise RuntimeError(f"使用ar构建DEB包失败: {stderr}")

            shutil.copy2(staged_deb_path, abs_deb_path)
            
        finally:
            remove_dir(staging_dir)
    
    def cleanup(self) -> None:
        """清理临时文件"""
        if self.build_dir:
            remove_dir(self.build_dir)
            self.build_dir = "" 
