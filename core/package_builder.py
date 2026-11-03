"""
包构建器抽象基类
定义DEB和RPM包构建器的通用接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from core.appimage import AppImageInfo


class PackageBuilder(ABC):
    """包构建器抽象基类"""
    
    def __init__(self, app_info: AppImageInfo, extracted_dir: str):
        """
        初始化包构建器
        
        Args:
            app_info: AppImage信息对象
            extracted_dir: AppImage提取后的目录路径
        """
        self.app_info = app_info
        self.extracted_dir = extracted_dir
        self.build_dir: str = ""
        self.package_config: Dict[str, Any] = {}
    
    @abstractmethod
    def prepare_build_directory(self) -> str:
        """
        准备构建目录
        
        Returns:
            构建目录路径
        """
        pass
    
    @abstractmethod
    def create_package_structure(self) -> None:
        """创建包的目录结构"""
        pass
    
    @abstractmethod
    def copy_application_files(self) -> None:
        """复制应用程序文件到包目录"""
        pass
    
    @abstractmethod
    def generate_metadata_files(self) -> None:
        """生成包的元数据文件"""
        pass
    
    @abstractmethod
    def build_package(self, output_path: str) -> str:
        """
        构建最终的包文件
        
        Args:
            output_path: 输出包文件的路径
        
        Returns:
            生成的包文件路径
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """清理临时文件"""
        pass
    
    def set_package_config(self, config: Dict[str, Any]) -> None:
        """
        设置包配置
        
        Args:
            config: 包配置字典
        """
        self.package_config.update(config)
    
    def _get_sub_config(self, package_type: str) -> Dict[str, Any]:
        """
        获取指定包类型的子配置（deb 或 rpm）
        
        配置支持嵌套结构，例如：
            {"deb": {"depends": [...], "requires": [...]}, "rpm": {...}}
        若不存在对应的子对象，返回空字典。
        
        Args:
            package_type: 包类型 ('deb' 或 'rpm')
        
        Returns:
            子配置字典
        """
        sub = self.package_config.get(package_type)
        if isinstance(sub, dict):
            return sub
        return {}
    
    def _get_dependencies(self, package_type: str) -> list:
        """
        获取指定包类型的依赖列表
        
        优先从嵌套子配置的 'depends' 字段读取，
        兼容旧的扁平 'depends' 字段。
        
        Args:
            package_type: 包类型 ('deb' 或 'rpm')
        
        Returns:
            依赖列表
        """
        deps = self._get_sub_config(package_type).get('depends')
        if deps is None:
            deps = self.package_config.get('depends', [])
        if deps is None:
            deps = []
        return list(deps) if isinstance(deps, (list, tuple)) else [deps]
    
    def _get_requires(self, package_type: str) -> list:
        """
        获取指定包类型的需求列表
        
        优先从嵌套子配置的 'requires' 字段读取，
        兼容旧的扁平 'requires' 字段。
        
        Args:
            package_type: 包类型 ('deb' 或 'rpm')
        
        Returns:
            需求列表
        """
        reqs = self._get_sub_config(package_type).get('requires')
        if reqs is None:
            reqs = self.package_config.get('requires', [])
        if reqs is None:
            reqs = []
        return list(reqs) if isinstance(reqs, (list, tuple)) else [reqs]
    
    def _get_section(self, package_type: str, default: str = '') -> str:
        """
        获取指定包类型的分类(section)
        
        优先从嵌套子配置的 'section' 字段读取，
        兼容旧的扁平 'section' 字段。
        
        Args:
            package_type: 包类型 ('deb' 或 'rpm')
            default: 默认值
        
        Returns:
            分类字符串
        """
        section = self._get_sub_config(package_type).get('section')
        if section is None:
            section = self.package_config.get('section')
        return section if section else default
    
    def _get_priority(self, package_type: str, default: str = '') -> str:
        """
        获取指定包类型的优先级(priority)
        
        优先从嵌套子配置的 'priority' 字段读取，
        兼容旧的扁平 'priority' 字段。
        
        Args:
            package_type: 包类型 ('deb' 或 'rpm')
            default: 默认值
        
        Returns:
            优先级字符串
        """
        priority = self._get_sub_config(package_type).get('priority')
        if priority is None:
            priority = self.package_config.get('priority')
        return priority if priority else default
    
    def get_package_name(self, preserve_case: bool = False) -> str:
        """
        获取包名称（转换为符合规范的格式）
        
        Args:
            preserve_case: 是否保持原始大小写，默认False（转为小写以符合包管理规范）
        
        Returns:
            规范化的包名称
        """
        name = self.app_info.name if preserve_case else self.app_info.name.lower()
        # 移除特殊字符，只保留字母、数字、连字符和下划线
        import re
        if preserve_case:
            name = re.sub(r'[^a-zA-Z0-9\-_]', '-', name)
        else:
            name = re.sub(r'[^a-z0-9\-_]', '-', name)
        # 移除连续的连字符
        name = re.sub(r'-+', '-', name)
        # 移除开头和结尾的连字符
        name = name.strip('-')
        return name or "unknown-app"
    
    def get_display_name(self) -> str:
        """
        获取应用程序的显示名称（保持原始大小写）
        
        Returns:
            原始显示名称
        """
        return self.app_info.name or "Unknown App"
    
    def _detect_system_architecture(self) -> str:
        """
        自动检测系统架构
        
        Returns:
            系统架构字符串
        """
        import platform
        
        # 获取机器架构
        machine = platform.machine().lower()
        
        # 映射到标准架构名称
        arch_mapping = {
            'x86_64': 'amd64',    # 64位 x86
            'amd64': 'amd64',     # 64位 x86 (Windows风格)
            'i386': 'i386',       # 32位 x86
            'i686': 'i386',       # 32位 x86
            'armv7l': 'armhf',    # ARM 32位
            'aarch64': 'arm64',   # ARM 64位
            'arm64': 'arm64',     # ARM 64位 (macOS风格)
        }
        
        return arch_mapping.get(machine, 'amd64')  # 默认返回amd64
    
    def get_architecture(self, package_type: str = 'deb') -> str:
        """
        获取目标架构
        
        Args:
            package_type: 包类型 ('deb' 或 'rpm')
        
        Returns:
            架构字符串
        """
        # 确定架构：优先使用配置，否则自动检测
        if 'architecture' in self.package_config and self.package_config['architecture']:
            detected_arch = self.package_config['architecture']
        else:
            detected_arch = self._detect_system_architecture()
        
        # 根据包类型调整架构名称
        if package_type == 'rpm':
            # RPM通常使用x86_64而不是amd64
            if detected_arch == 'amd64':
                return 'x86_64'
            elif detected_arch == 'arm64':
                return 'aarch64'
            elif detected_arch == 'armhf':
                return 'armv7hl'
            elif detected_arch == 'i386':
                return 'i686'
        
        return detected_arch
    
    def get_package_version(self, package_type: str = 'deb') -> str:
        """
        获取包版本号
        
        Args:
            package_type: 包类型 ('deb' 或 'rpm')，用于决定版本号规范化规则
        
        Returns:
            版本号字符串
        """
        version = self.app_info.version
        if not version or version == "":
            version = "1.0.0"
        
        import re
        # 只保留版本号中合法的字符：字母、数字、点、加号、波浪号、下划线、连字符
        version = re.sub(r'[^0-9A-Za-z.+\-_~]', '', version)
        # 移除开头/结尾的分隔符，确保以字母或数字开头结尾
        version = version.strip('.-+_~')
        if not version:
            version = "1.0.0"
        
        # RPM版本号不允许包含连字符(连字符用于分隔Version与Release)，
        # 也不允许包含下划线，改用波浪号(~)表示预发布版本，符合RPM惯例
        if package_type == 'rpm':
            version = version.replace('-', '~').replace('_', '~')
            # 移除连续的波浪号
            version = re.sub(r'~+', '~', version).strip('~')
            if not version:
                version = "1.0.0"
        
        return version 
