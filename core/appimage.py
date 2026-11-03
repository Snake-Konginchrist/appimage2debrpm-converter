"""
AppImage处理核心模块
负责AppImage文件的解析、提取和元数据获取
"""

import os
import configparser
from typing import Dict, Optional, List
from utils.command_executor import execute_command, check_command_exists
from utils.file_operations import create_temp_dir, find_file_in_path, is_executable


class AppImageInfo:
    """AppImage信息类，存储从AppImage中提取的元数据"""
    
    def __init__(self):
        self.name: str = ""
        self.version: str = "1.0.0"
        self.description: str = ""
        self.categories: List[str] = []
        self.executable: str = ""
        self.icon: str = ""
        self.desktop_file: str = ""
        self.maintainer: str = ""
        self.homepage: str = ""
        self.depends: List[str] = []
        self.size: int = 0


class AppImageExtractor:
    """AppImage提取器类，负责提取AppImage内容和解析元数据"""
    
    def __init__(self, appimage_path: str):
        """
        初始化AppImage提取器
        
        Args:
            appimage_path: AppImage文件路径
        """
        self.appimage_path = os.path.abspath(appimage_path)
        self.temp_dir: Optional[str] = None
        self.extracted_dir: Optional[str] = None
        self.info = AppImageInfo()
        
        # 检查必要的工具是否存在
        self._check_dependencies()
    
    def _check_dependencies(self) -> None:
        """检查系统依赖工具是否存在"""
        required_tools = ['unsquashfs']
        missing_tools = []
        
        for tool in required_tools:
            if not check_command_exists(tool):
                missing_tools.append(tool)
        
        if missing_tools:
            raise RuntimeError(f"缺少必要工具: {', '.join(missing_tools)}。请安装squashfs-tools包。")
    
    def extract(self) -> str:
        """
        提取AppImage内容到临时目录
        
        Returns:
            提取后的目录路径
        
        Raises:
            RuntimeError: 如果提取失败
        """
        if not os.path.isfile(self.appimage_path):
            raise FileNotFoundError(f"AppImage文件不存在: {self.appimage_path}")
        
        # 创建临时目录
        self.temp_dir = create_temp_dir("appimage_extract_")
        
        # 首先尝试使用AppImage的内置提取功能
        success = self._extract_using_appimage()
        
        if not success:
            # 如果内置提取失败，尝试使用unsquashfs
            print("AppImage内置提取失败，尝试使用unsquashfs...")
            success = self._extract_using_unsquashfs()
        
        if not success:
            raise RuntimeError("无法提取AppImage文件，请检查文件是否为有效的AppImage格式")
        
        print(f"AppImage已提取到: {self.extracted_dir}")
        return self.extracted_dir
    
    def _extract_using_appimage(self) -> bool:
        """
        使用AppImage的内置提取功能
        
        Returns:
            提取是否成功
        """
        try:
            # 确保AppImage文件有执行权限
            if not os.access(self.appimage_path, os.X_OK):
                os.chmod(self.appimage_path, 0o755)
            
            # 使用AppImage的--appimage-extract选项
            return_code, stdout, stderr = execute_command([
                self.appimage_path, '--appimage-extract'
            ], cwd=self.temp_dir)
            
            if return_code == 0:
                # 检查是否生成了squashfs-root目录
                potential_dir = os.path.join(self.temp_dir, "squashfs-root")
                if os.path.isdir(potential_dir):
                    self.extracted_dir = potential_dir
                    return True
            
            return False
            
        except Exception as e:
            print(f"AppImage内置提取失败: {e}")
            return False
    
    def _extract_using_unsquashfs(self) -> bool:
        """
        使用unsquashfs工具提取
        
        Returns:
            提取是否成功
        """
        try:
            self.extracted_dir = os.path.join(self.temp_dir, "squashfs-root")
            
            # 使用unsquashfs提取AppImage
            return_code, stdout, stderr = execute_command([
                'unsquashfs', '-d', self.extracted_dir, self.appimage_path
            ])
            
            if return_code == 0:
                return True
            else:
                print(f"unsquashfs提取失败: {stderr}")
                return False
                
        except Exception as e:
            print(f"unsquashfs提取异常: {e}")
            return False
    
    def parse_metadata(self) -> AppImageInfo:
        """
        解析AppImage的元数据
        
        Returns:
            包含元数据的AppImageInfo对象
        """
        if not self.extracted_dir:
            raise RuntimeError("请先调用extract()方法提取AppImage")
        
        # 获取基本信息
        self.info.size = os.path.getsize(self.appimage_path)
        
        # 查找.desktop文件
        desktop_file = self._find_desktop_file()
        if desktop_file:
            self._parse_desktop_file(desktop_file)
        
        # 查找主可执行文件
        self._find_main_executable()
        
        # 查找图标文件
        self._find_icon_file()
        
        return self.info
    
    def _find_desktop_file(self) -> Optional[str]:
        """查找.desktop文件"""
        desktop_files = []
        for root, _, files in os.walk(self.extracted_dir):
            for file in files:
                if file.endswith('.desktop'):
                    desktop_files.append(os.path.join(root, file))
        
        # 优先选择根目录下的.desktop文件
        for desktop_file in desktop_files:
            if os.path.dirname(desktop_file) == self.extracted_dir:
                return desktop_file
        
        # 如果根目录没有，返回第一个找到的
        return desktop_files[0] if desktop_files else None
    
    def _parse_desktop_file(self, desktop_file: str) -> None:
        """解析.desktop文件获取应用信息"""
        try:
            # 禁用插值功能以避免%F等参数导致的解析错误
            config = configparser.ConfigParser(interpolation=None)
            config.read(desktop_file, encoding='utf-8')
            
            if 'Desktop Entry' in config:
                entry = config['Desktop Entry']
                
                self.info.name = entry.get('Name', os.path.basename(self.appimage_path))
                self.info.description = entry.get('Comment', entry.get('GenericName', ''))
                self.info.executable = entry.get('Exec', '').split()[0]  # 只取命令部分
                self.info.icon = entry.get('Icon', '')
                
                # 解析分类
                categories = entry.get('Categories', '')
                if categories:
                    self.info.categories = [cat.strip() for cat in categories.split(';') if cat.strip()]
                
                self.info.desktop_file = desktop_file
                
        except Exception as e:
            print(f"警告：解析.desktop文件失败: {e}")
    
    def _find_main_executable(self) -> None:
        """查找主可执行文件"""
        if self.info.executable:
            # 如果从.desktop文件中获取了可执行文件名，尝试找到它
            exec_path = find_file_in_path(self.info.executable, self.extracted_dir)
            if exec_path and is_executable(exec_path):
                self.info.executable = exec_path
                return
        
        # 查找AppRun文件（AppImage标准）
        apprun_path = os.path.join(self.extracted_dir, 'AppRun')
        if is_executable(apprun_path):
            self.info.executable = apprun_path
            return
        
        # 查找其他可执行文件
        for root, _, files in os.walk(self.extracted_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if is_executable(file_path) and not file.startswith('.'):
                    self.info.executable = file_path
                    return
    
    def _find_icon_file(self) -> None:
        """查找图标文件"""
        if self.info.icon:
            # 如果从.desktop文件中获取了图标名，尝试找到它
            icon_extensions = ['.png', '.svg', '.xpm', '.ico']
            
            for ext in icon_extensions:
                icon_path = find_file_in_path(self.info.icon + ext, self.extracted_dir)
                if icon_path:
                    self.info.icon = icon_path
                    return
            
            # 尝试直接查找图标名（可能已包含扩展名）
            icon_path = find_file_in_path(self.info.icon, self.extracted_dir)
            if icon_path:
                self.info.icon = icon_path
                return
        
        # 查找常见的图标文件
        icon_patterns = ['*.png', '*.svg', '*.xpm', '*.ico']
        for root, _, files in os.walk(self.extracted_dir):
            for file in files:
                if any(file.lower().endswith(ext[1:]) for ext in ['.png', '.svg', '.xpm', '.ico']):
                    self.info.icon = os.path.join(root, file)
                    return
    
    def cleanup(self) -> None:
        """清理临时文件"""
        if self.temp_dir:
            from utils.file_operations import remove_dir
            remove_dir(self.temp_dir)
            self.temp_dir = None
            self.extracted_dir = None 
